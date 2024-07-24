from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import func
import random
from models.db_model import *
from config import project_settings

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
    consultants = session.query(Consultant).all()
    relevant_consultants = [c for c in consultants if c.custom_data.get('title_id') == title_id]
    
    if not relevant_consultants:
        return 5  # Default to 5 years if no consultants found for this title
    
    total_experience = sum((current_date.year - c.HireYear) for c in relevant_consultants)
    return total_experience / len(relevant_consultants)

def calculate_project_financials(session, project, assigned_consultants, current_date, deliverables):
    # Calculate billing rates for each title
    title_billing_rates = {}
    for consultant in assigned_consultants:
        title_id = consultant.custom_data.get('title_id', 1)  # Default to 1 if title_id is not found
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
        billing_rate = title_billing_rates[consultant.custom_data.get('title_id', 1)]
        
        estimated_total_cost += cost_rate * consultant_hours
        estimated_total_revenue += billing_rate * consultant_hours

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

    project.custom_data['pre_generated_expenses'] = generate_project_expenses(project, float(estimated_total_cost), deliverables)

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
         
def generate_project_expenses(project, estimated_total_cost, deliverables):
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

def update_project_financials(session, project):
    # Calculate actual cost
    actual_cost = Decimal('0')
    for deliverable in project.Deliverables:
        consultant_deliverables = session.query(ConsultantDeliverable).filter_by(DeliverableID=deliverable.DeliverableID).all()
        for cd in consultant_deliverables:
            hourly_cost = calculate_hourly_cost(session, cd.ConsultantID, cd.Date.year)
            actual_cost += Decimal(cd.Hours) * Decimal(hourly_cost)

    # Calculate actual revenue
    actual_revenue = Decimal('0')
    if project.Type == 'Fixed':
        actual_revenue = Decimal(project.Price)
    else:  # Time and Material
        for deliverable in project.Deliverables:
            consultant_deliverables = session.query(ConsultantDeliverable).filter_by(DeliverableID=deliverable.DeliverableID).all()
            for cd in consultant_deliverables:
                consultant = session.query(Consultant).get(cd.ConsultantID)        
                title_id = consultant.custom_data.get('title_id')
                billing_rate_entry = session.query(ProjectBillingRate).filter_by(
                    ProjectID=project.ProjectID,
                    TitleID=title_id
                ).first()
                
                actual_revenue += Decimal(cd.Hours) * Decimal(billing_rate_entry.Rate)

    # Update project metadata with financial information
    project.custom_data['actual_cost'] = float(actual_cost)
    project.custom_data['actual_revenue'] = float(actual_revenue)
    project.custom_data['profit'] = float(actual_revenue - actual_cost)
    project.custom_data['profit_margin'] = float((actual_revenue - actual_cost) / actual_revenue) if actual_revenue > 0 else 0

    session.commit()