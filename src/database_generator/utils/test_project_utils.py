from decimal import Decimal, ROUND_HALF_UP
import random
from datetime import timedelta, date
from dateutil.relativedelta import relativedelta
from sqlalchemy import func
from collections import Counter, defaultdict
from ...db_model import *
from config import project_settings
import math

def round_to_nearest_thousand(value):
    return Decimal(value).quantize(Decimal('1000'), rounding=ROUND_HALF_UP)

def adjust_hours(planned_hours):
    if random.random() < 0.1:  # 10% chance of finishing early
        actual_hours = Decimal(planned_hours) * Decimal(random.uniform(0.8, 0.95))
    else:  # 90% chance of overrunning
        actual_hours = Decimal(planned_hours) * Decimal(random.uniform(1.05, 1.3))
    return actual_hours.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)

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

def determine_project_count(available_consultants, growth_rate):
    base_count = len(available_consultants) // random.randint(3, 5)  # number of consultants per project
    adjusted_count = int(base_count * (1 + growth_rate))
    return max(5, adjusted_count)

def calculate_project_progress(project, deliverables):
    total_planned_hours = sum(d.PlannedHours for d in deliverables)
    
    if total_planned_hours == 0:
        project.Progress = 0
        return

    weighted_progress = sum((d.ActualHours / d.PlannedHours) * (d.PlannedHours / total_planned_hours) * 100 for d in deliverables)
    project.Progress = int(round(weighted_progress))

def get_working_days(year, month):
    start_date = date(year, month, 1)
    end_date = start_date + relativedelta(months=1) - timedelta(days=1)
    return [d for d in daterange(start_date, end_date) if d.weekday() < 5]  # Monday = 0, Friday = 4

def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(n)

def get_current_title(session, consultant_id, current_date):
    current_title = session.query(ConsultantTitleHistory).filter(
        ConsultantTitleHistory.ConsultantID == consultant_id,
        ConsultantTitleHistory.StartDate <= current_date,
        (ConsultantTitleHistory.EndDate.is_(None) | (ConsultantTitleHistory.EndDate >= current_date))
    ).order_by(ConsultantTitleHistory.StartDate.desc()).first()
    
    return current_title

def get_available_consultants(session, current_date):
    available_consultants = session.query(Consultant).join(ConsultantTitleHistory).filter(
        ConsultantTitleHistory.StartDate <= current_date,
        (ConsultantTitleHistory.EndDate.is_(None) | (ConsultantTitleHistory.EndDate >= current_date)),
        ConsultantTitleHistory.EventType.notin_(['Layoff', 'Attrition'])
    ).all()

    return [c for c in available_consultants if is_consultant_available(session, c.ConsultantID, current_date)]

def is_consultant_available(session, consultant_id, current_date):
    active_projects = session.query(func.count(ProjectTeam.ProjectID)).filter(
        ProjectTeam.ConsultantID == consultant_id,
        ProjectTeam.StartDate <= current_date,
        (ProjectTeam.EndDate.is_(None) | (ProjectTeam.EndDate >= current_date))
    ).scalar()
    
    return active_projects < 3

def assign_project_to_business_unit(session, assigned_consultants, active_units, current_year):
    from ...db_model import Project
    
    consultant_unit_counts = Counter(consultant.BusinessUnitID for consultant in assigned_consultants)
    
    project_counts = dict(session.query(
        Project.UnitID, func.count(Project.ProjectID)
    ).filter(
        func.extract('year', Project.PlannedStartDate) == current_year,
        Project.UnitID.in_([unit.BusinessUnitID for unit in active_units])
    ).group_by(Project.UnitID).all())
    
    for unit in active_units:
        if unit.BusinessUnitID not in project_counts:
            project_counts[unit.BusinessUnitID] = 0
    
    total_consultants = sum(consultant_unit_counts.values())
    target_distribution = {unit.BusinessUnitID: consultant_unit_counts.get(unit.BusinessUnitID, 0) / total_consultants 
                           for unit in active_units}
    
    total_projects = sum(project_counts.values())
    current_distribution = {unit_id: count / (total_projects + 1)
                            for unit_id, count in project_counts.items()}
    
    distribution_difference = {unit_id: target_distribution.get(unit_id, 0) - current_distribution.get(unit_id, 0)
                               for unit_id in project_counts.keys()}
    return max(distribution_difference, key=distribution_difference.get)

def assign_consultants_to_project(session, available_consultants, current_date):
    consultants_by_title = defaultdict(list)
    for consultant in available_consultants:
        # Ensure we're working with Consultant objects
        if isinstance(consultant, BusinessUnit):
            for c in consultant.Consultants:
                current_title = get_current_title(session, c.ConsultantID, current_date)
                if current_title:
                    consultants_by_title[current_title.TitleID].append(c)
        else:
            current_title = get_current_title(session, consultant.ConsultantID, current_date)
            if current_title:
                consultants_by_title[current_title.TitleID].append(consultant)

    assigned_consultants = []

    # Assign a project manager (title 4 or higher)
    higher_level_titles = [6, 5, 4]
    for title_id in higher_level_titles:
        if consultants_by_title[title_id]:
            project_manager = random.choice(consultants_by_title[title_id])
            assigned_consultants.append(project_manager)
            consultants_by_title[title_id].remove(project_manager)
            break

    if not assigned_consultants:
        return []  # No suitable project manager found

    # Assign team members (titles 3 or lower)
    target_team_size = random.randint(5, 10)
    lower_level_consultants = [c for title_id in [1, 2, 3] for c in consultants_by_title[title_id]]
    
    num_additional_consultants = min(len(lower_level_consultants), target_team_size - 1)
    assigned_consultants.extend(random.sample(lower_level_consultants, num_additional_consultants))

    return assigned_consultants

def set_project_dates(project, current_date, assigned_consultants, session):
    if project.Type == 'Fixed':
        duration_months = random.randint(*project_settings.FIXED_PROJECT_DURATION_RANGE)
    else:  # Time and Material
        duration_months = random.randint(*project_settings.TIME_MATERIAL_PROJECT_DURATION_RANGE)
    
    project_manager = next(c for c in assigned_consultants if get_current_title(session, c.ConsultantID, current_date).TitleID >= 4)
    pm_availability = get_consultant_availability(session, project_manager.ConsultantID, current_date)
    
    planned_start = pm_availability + timedelta(days=random.randint(0, 15))
    actual_start_variance = timedelta(days=random.randint(-7, 14))
    
    project.PlannedStartDate = planned_start
    project.ActualStartDate = planned_start + actual_start_variance
    project.PlannedEndDate = project.PlannedStartDate + timedelta(days=duration_months * 30)
    
    return duration_months

def get_consultant_availability(session, consultant_id, current_date):
    latest_project = session.query(func.max(ProjectTeam.EndDate)).filter(
        ProjectTeam.ConsultantID == consultant_id,
        ProjectTeam.EndDate.isnot(None)
    ).scalar()
    
    return max(current_date, latest_project + timedelta(days=1)) if latest_project else current_date

import math

def generate_deliverables(project):
    from ...db_model import Deliverable
    
    num_deliverables = random.randint(*project_settings.DELIVERABLE_COUNT_RANGE)
    deliverables = []
    remaining_hours = project.PlannedHours
    project_duration = (project.PlannedEndDate - project.PlannedStartDate).days

    for i in range(num_deliverables):
        is_last_deliverable = (i == num_deliverables - 1)
        
        if is_last_deliverable:
            planned_hours = remaining_hours
        else:
            min_hours = 10
            max_hours = max(min_hours, math.floor(remaining_hours - (num_deliverables - i - 1) * min_hours))
            planned_hours = random.randint(math.floor(min_hours), math.floor(max_hours))
            remaining_hours -= planned_hours

        start_date = project.PlannedStartDate if i == 0 else deliverables[-1].DueDate + timedelta(days=1)
        deliverable_duration = max(1, int((planned_hours / project.PlannedHours) * project_duration))
        due_date = min(start_date + timedelta(days=deliverable_duration), project.PlannedEndDate)

        actual_start_variance = timedelta(days=random.randint(-3, 7))
        actual_start_date = start_date + actual_start_variance

        price = None
        if project.Type == 'Fixed' and project.Price is not None:
            price = round_to_nearest_thousand((Decimal(planned_hours) / Decimal(project.PlannedHours) * Decimal(project.Price)))

        deliverable = Deliverable(
            ProjectID=project.ProjectID,
            Name=f"Deliverable {i+1}",
            PlannedStartDate=start_date,
            ActualStartDate=actual_start_date,
            Status='Not Started',
            DueDate=due_date,
            PlannedHours=planned_hours,
            ActualHours=0,
            Progress=0,
            Price=price
        )
        deliverables.append(deliverable)

    return deliverables

def calculate_project_financials(session, project, assigned_consultants, current_date, deliverables):
    # Calculate average hourly cost for each title
    title_hourly_costs = {}
    for consultant in assigned_consultants:
        # Ensure we're working with Consultant objects
        if isinstance(consultant, BusinessUnit):
            # If we have a BusinessUnit, we need to get its consultants
            consultants = consultant.Consultants
        else:
            consultants = [consultant]
        
        for c in consultants:
            current_title = get_current_title(session, c.ConsultantID, current_date)
            if current_title and current_title.TitleID not in title_hourly_costs:
                title_hourly_costs[current_title.TitleID] = calculate_hourly_cost(session, c.ConsultantID, current_date.year)

    # Calculate estimated total cost
    estimated_total_cost = sum(Decimal(title_hourly_costs[get_current_title(session, c.ConsultantID, current_date).TitleID]) * Decimal(project.PlannedHours) 
                               for c in assigned_consultants if isinstance(c, Consultant))

    if project.Type == 'Fixed':
        profit_margin = Decimal(random.uniform(*project_settings.PROFIT_MARGIN_RANGE))
        project.Price = float(round_to_nearest_thousand(estimated_total_cost * (Decimal('1') + profit_margin)))
    else:  # Time and Material
        project.EstimatedBudget = float(round_to_nearest_thousand(estimated_total_cost * project_settings.ESTIMATED_BUDGET_FACTORS))
        
        # Generate Project Billing Rates
        billing_rates = []
        for title_id, hourly_cost in title_hourly_costs.items():
            billing_rate = Decimal(hourly_cost) * (Decimal('1') + Decimal(random.uniform(*project_settings.PROFIT_MARGIN_RANGE)))
            billing_rate = round(billing_rate / Decimal('5')) * Decimal('5')  # Round to nearest $5
            billing_rates.append(ProjectBillingRate(
                ProjectID=project.ProjectID,
                TitleID=title_id,
                Rate=float(billing_rate)
            ))
        session.add_all(billing_rates)

    project.pre_generated_expenses = generate_project_expenses(project, float(estimated_total_cost), deliverables)

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

def update_project_and_deliverable_status(project, deliverables, simulation_end_date):
    all_deliverables_completed = True
    for deliverable in deliverables:
        if deliverable.ActualHours > 0:
            deliverable.Status = 'Completed' if deliverable.ActualHours >= deliverable.PlannedHours else 'In Progress'
            deliverable.Progress = min(100, int((deliverable.ActualHours / deliverable.PlannedHours) * 100))
            
            if project.ActualStartDate is None or deliverable.ActualStartDate < project.ActualStartDate:
                project.ActualStartDate = deliverable.ActualStartDate
            
            if deliverable.Status == 'Completed':
                if project.ActualEndDate is None or deliverable.SubmissionDate > project.ActualEndDate:
                    project.ActualEndDate = deliverable.SubmissionDate
            else:
                all_deliverables_completed = False
        else:
            all_deliverables_completed = False

    calculate_project_progress(project, deliverables)

    if project.Progress > 0:
        project.Status = 'In Progress'
        if all_deliverables_completed and project.PlannedEndDate <= simulation_end_date:
            project.Status = 'Completed'
        else:
            project.ActualEndDate = None

    return project, deliverables
