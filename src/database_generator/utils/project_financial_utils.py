from decimal import Decimal, ROUND_HALF_UP
import random
from ...db_model import *
from config import project_settings


def round_to_nearest_thousand(value):
    return Decimal(value).quantize(Decimal('1000'), rounding=ROUND_HALF_UP)

def calculate_hourly_cost(session, consultant_id, year):
    from ...db_model import ConsultantTitleHistory
    from sqlalchemy import func
    
    avg_salary = session.query(func.avg(ConsultantTitleHistory.Salary)).filter(
        ConsultantTitleHistory.ConsultantID == consultant_id,
        func.extract('year', ConsultantTitleHistory.StartDate) == year
    ).scalar()
    
    if not avg_salary:
        return 0
    
    hourly_cost = (avg_salary / 12) / (52 * 40)  # Assuming 52 weeks and 40 hours per week
    return hourly_cost * (1 + project_settings.OVERHEAD_PERCENTAGE)

def calculate_project_financials(session, project, assigned_consultants, current_date, deliverables):
    # Calculate billing rates for each title
    title_billing_rates = {}
    for consultant_info in assigned_consultants:
        if consultant_info.title_id not in title_billing_rates:
            title_billing_rates[consultant_info.title_id] = calculate_billing_rate(
                consultant_info.title_id, 
                project.Type, 
                current_date.year - consultant_info.consultant.HireYear
            )

    # Calculate estimated total cost and revenue
    estimated_total_cost = Decimal('0')
    estimated_total_revenue = Decimal('0')
    for consultant_info in assigned_consultants:
        consultant_hours = Decimal(project.PlannedHours) / len(assigned_consultants)
        cost_rate = Decimal(calculate_hourly_cost(session, consultant_info.consultant.ConsultantID, current_date.year))
        billing_rate = Decimal(title_billing_rates[consultant_info.title_id])
        
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

    project.pre_generated_expenses = generate_project_expenses(project, float(estimated_total_cost), deliverables)

    # Distribute price to deliverables for fixed contracts
    if project.Type == 'Fixed':
        total_planned_hours = sum(d.PlannedHours for d in deliverables)
        for deliverable in deliverables:
            deliverable.Price = round(project.Price * (deliverable.PlannedHours / total_planned_hours))

def calculate_billing_rate(title_id, project_type, years_experience):
    base_min, base_max = project_settings.HOURLY_RATE_RANGES[title_id]
    
    # Adjust for experience
    experience_factor = min(years_experience / 10, 1)  # Cap at 10 years for this calculation
    rate_range = base_max - base_min
    rate = base_min + (rate_range * experience_factor)
    
    # Adjust for project type
    if project_type == 'Fixed':
        rate *= Decimal('0.9')  # Slight discount for fixed-price projects
    
    # Add some randomness
    rate *= Decimal(random.uniform(0.95, 1.05))
    
    return round(rate, -1)  # Round to nearest 10
         
def generate_project_expenses(project, estimated_total_cost, deliverables):
    expenses = []
    total_planned_hours = sum(d.PlannedHours for d in deliverables)

    for deliverable in deliverables:
        deliverable_cost_ratio = deliverable.PlannedHours / total_planned_hours
        deliverable_estimated_cost = estimated_total_cost * deliverable_cost_ratio

        for category, percentage in project_settings.EXPENSE_CATEGORIES.items():
            is_billable = random.choice([True, False])
            amount = Decimal(deliverable_estimated_cost) * Decimal(percentage) * Decimal(random.uniform(0.8, 1.2))
            amount = round(amount, -2)  # Round to nearest hundred

            if amount > 0:
                expense = {
                    'DeliverableID': deliverable.DeliverableID,
                    'Amount': float(amount),
                    'Description': f"{category} expense for {deliverable.Name}",
                    'Category': category,
                    'IsBillable': is_billable
                }
                expenses.append(expense)

    return expenses