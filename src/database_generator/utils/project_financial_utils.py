from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import func, cast, Integer
from sqlalchemy.orm import aliased
import random
from models.db_model import *
from config import project_settings
import logging

def round_to_nearest_thousand(value):
    return Decimal(value).quantize(Decimal('1000'), rounding=ROUND_HALF_UP)

def calculate_hourly_cost(session, consultant_id, year):
    avg_salary = session.query(func.avg(ConsultantTitleHistory.Salary)).filter(
        ConsultantTitleHistory.ConsultantID == consultant_id,
        func.extract('year', ConsultantTitleHistory.StartDate) == year
    ).scalar()
    
    if not avg_salary:
        return 0
    
    hourly_cost = (avg_salary / 12) / (52 * 40)  # Assuming 52 weeks and 40 hours per week
    return hourly_cost * (1 + project_settings.OVERHEAD_PERCENTAGE)

def calculate_average_experience(session, title_id, current_date):
    ConsultantCustomDataAlias = aliased(ConsultantCustomData)
    
    consultants = session.query(Consultant).join(
        ConsultantCustomDataAlias,
        Consultant.ConsultantID == ConsultantCustomDataAlias.ConsultantID
    ).filter(
        cast(func.json_extract(ConsultantCustomDataAlias.CustomData, '$.title_id'), Integer) == title_id
    ).all()
    
    if not consultants:
        return 5  # Default to 5 years if no consultants found for this title
    
    total_experience = sum((current_date.year - c.HireYear) for c in consultants)
    return total_experience / len(consultants)

def calculate_project_financials(session, project, assigned_consultants, current_date, deliverables):
    # Calculate billing rates for each title
    title_billing_rates = {}
    for consultant in assigned_consultants:
        consultant_custom_data = session.query(ConsultantCustomData).get(consultant.ConsultantID)
        title_id = consultant_custom_data.CustomData.get('title_id', 1)  # Default to 1 if title_id is not found
        if title_id not in title_billing_rates:
            title_billing_rates[title_id] = calculate_billing_rate(
                title_id, 
                project.Type, 
                current_date.year - consultant.HireYear
            )

    # Calculate estimated total cost and revenue
    estimated_total_cost = Decimal('0')
    estimated_total_revenue = Decimal('0')
    for consultant in assigned_consultants:
        consultant_hours = Decimal(project.PlannedHours) / Decimal(len(assigned_consultants))
        cost_rate = Decimal(str(calculate_hourly_cost(session, consultant.ConsultantID, current_date.year)))
        consultant_custom_data = session.query(ConsultantCustomData).get(consultant.ConsultantID)
        billing_rate = title_billing_rates[consultant_custom_data.CustomData.get('title_id', 1)]
        
        estimated_total_cost += cost_rate * consultant_hours
        estimated_total_revenue += billing_rate * consultant_hours

    # Generate predefined expenses
    predefined_expenses = generate_predefined_expenses(project, float(estimated_total_cost), deliverables)

    # Update estimated total cost and revenue with predefined expenses
    for expense in predefined_expenses:
        estimated_total_cost += Decimal(str(expense['Amount']))
        if expense['IsBillable']:
            estimated_total_revenue += Decimal(str(expense['Amount']))

    if project.Type == 'Fixed':
        project.Price = float(round_to_nearest_thousand(estimated_total_revenue))
    else:  # Time and Material
        project.EstimatedBudget = float(round_to_nearest_thousand(estimated_total_revenue))
        
        # Generate Project Billing Rates
        billing_rates = []
        for title_id, rate in title_billing_rates.items():
            billing_rates.append(ProjectBillingRate(
                ProjectID=project.ProjectID,
                TitleID=title_id,
                Rate=float(rate)
            ))
        
        session.add_all(billing_rates)
        session.flush()

    project_custom_data = session.query(ProjectCustomData).get(project.ProjectID)
    if not project_custom_data:
        project_custom_data = ProjectCustomData(ProjectID=project.ProjectID, CustomData={})
        session.add(project_custom_data)
    project_custom_data.CustomData['predefined_expenses'] = predefined_expenses

    # Distribute price to deliverables for fixed contracts
    if project.Type == 'Fixed':
        total_planned_hours = Decimal(sum(d.PlannedHours for d in deliverables))
        for deliverable in deliverables:
            deliverable.Price = float((Decimal(project.Price) * (Decimal(deliverable.PlannedHours) / total_planned_hours)).quantize(Decimal('0.01')))

def calculate_billing_rate(title_id, project_type, years_experience):
    base_min, base_max = project_settings.HOURLY_RATE_RANGES[title_id]
    
    # Adjust for experience
    experience_factor = Decimal(min(years_experience / 10, 1))  # Cap at 10 years for this calculation
    rate_range = Decimal(base_max - base_min)
    rate = Decimal(base_min) + (rate_range * experience_factor)
    
    # Adjust for project type
    if project_type == 'Fixed':
        rate *= Decimal('0.9')  # Slight discount for fixed-price projects
    
    # Add some randomness
    rate *= Decimal(random.uniform(0.95, 1.05))
    
    return rate.quantize(Decimal('0.01'))
         
def generate_predefined_expenses(project, estimated_total_cost, deliverables):
    expenses = []
    total_planned_hours = Decimal(sum(d.PlannedHours for d in deliverables))

    for deliverable in deliverables:
        deliverable_cost_ratio = Decimal(deliverable.PlannedHours) / total_planned_hours
        deliverable_estimated_cost = Decimal(str(estimated_total_cost)) * deliverable_cost_ratio

        for category, percentage in project_settings.EXPENSE_CATEGORIES.items():
            is_billable = random.choice([True, False])
            amount = deliverable_estimated_cost * Decimal(str(percentage)) * Decimal(random.uniform(0.8, 1.2))
            amount = amount.quantize(Decimal('100'), rounding=ROUND_HALF_UP)  # Round to nearest hundred

            if amount > Decimal('0'):
                expense = {
                    'DeliverableID': deliverable.DeliverableID,
                    'Amount': float(amount),
                    'Description': f"{category} expense for {deliverable.Name}",
                    'Category': category,
                    'IsBillable': is_billable
                }
                expenses.append(expense)

    return expenses

def generate_expense_records(session, project, deliverable, predefined_expenses, current_date, work_ratio):
    deliverable_expenses = [e for e in predefined_expenses if e['DeliverableID'] == deliverable.DeliverableID]
    
    if not deliverable_expenses:
        logging.warning(f"No predefined expenses found for deliverable {deliverable.DeliverableID} in project {project.ProjectID}")
        return

    logging.info(f"Generating expenses for project {project.ProjectID}, deliverable {deliverable.DeliverableID}, work ratio: {work_ratio}")
    
    for expense in deliverable_expenses:
        expense_amount = Decimal(str(expense['Amount'])) * Decimal(str(work_ratio))
        if expense_amount > Decimal('0'):
            expense_record = ProjectExpense(
                ProjectID=project.ProjectID,
                DeliverableID=deliverable.DeliverableID,
                Date=current_date,
                Amount=float(expense_amount.quantize(Decimal('0.01'))),
                Description=expense['Description'],
                Category=expense['Category'],
                IsBillable=expense['IsBillable']
            )
            session.add(expense_record)
            logging.info(f"Generated expense record for project {project.ProjectID}, deliverable {deliverable.DeliverableID}: Amount={expense_record.Amount}, Category={expense_record.Category}")
        else:
            logging.debug(f"Skipped generating expense for project {project.ProjectID}, deliverable {deliverable.DeliverableID} due to zero amount")

    session.flush()
    logging.info(f"Completed expense generation for project {project.ProjectID}, deliverable {deliverable.DeliverableID}")