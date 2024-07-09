from decimal import Decimal, ROUND_HALF_UP
import random
from datetime import timedelta, date
from dateutil.relativedelta import relativedelta
from sqlalchemy import func, case
from collections import Counter
from ...db_model import *
from config import project_settings
import math
import logging

def initialize_project_meta(project, target_hours):
    meta = {
        'team': [pt.ConsultantID for pt in project.Team],
        'deliverables': {},
        'target_hours': target_hours
    }
    
    for deliverable in project.Deliverables:
        meta['deliverables'][deliverable.DeliverableID] = {
            'target_hours': deliverable.PlannedHours * (target_hours / project.PlannedHours),
            'consultant_deliverables': []
        }
    
    return meta

def round_to_nearest_thousand(value):
    return Decimal(value).quantize(Decimal('1000'), rounding=ROUND_HALF_UP)

def calculate_planned_hours(project, team_size):
    duration_days = (project.PlannedEndDate - project.PlannedStartDate).days
    working_days = math.ceil(duration_days * 5 / 7)  # Assuming 5 working days per week
    
    daily_team_hours = team_size * project_settings.AVERAGE_WORKING_HOURS_PER_DAY
    total_planned_hours = working_days * daily_team_hours
    
    return round(total_planned_hours)

def calculate_target_hours(planned_hours):
    if random.random() < 0.1:  # 10% chance of finishing early
        factor = random.uniform(0.8, 0.95)
    else:  # 90% chance of overrunning
        factor = random.uniform(1.05, 1.3)
    return round(planned_hours * factor)

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

def assign_project_team(session, project, assigned_consultants):
    logging.info(f"Assigning team for ProjectID: {project.ProjectID}")
    for consultant, title_id, _ in assigned_consultants:
        role = 'Project Manager' if title_id >= 4 else 'Team Member'
        
        team_member = ProjectTeam(
            ProjectID=project.ProjectID,
            ConsultantID=consultant.ConsultantID,
            Role=role,
            StartDate=project.ActualStartDate,
            EndDate=None
        )
        session.add(team_member)
        logging.info(f"Assigned ConsultantID: {consultant.ConsultantID}, Role: {role} to ProjectID: {project.ProjectID}")

def calculate_project_progress(project, deliverables):
    total_planned_hours = sum(d.PlannedHours for d in deliverables)
    
    if total_planned_hours == 0:
        project.Progress = 0
        return

    weighted_progress = sum((d.ActualHours / d.PlannedHours) * (d.PlannedHours / total_planned_hours) * 100 for d in deliverables)
    project.Progress = min(100, int(round(weighted_progress)))

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
    
    if current_title is None:
        logging.warning(f"No current title found for consultant {consultant_id} on {current_date}")
        return None
    
    return current_title

def get_available_consultants(session, current_date):
    available_consultants = session.query(
        Consultant,
        ConsultantTitleHistory.TitleID,
        case(
            (func.max(ProjectTeam.EndDate).isnot(None), func.max(ProjectTeam.EndDate)),
            else_=func.min(ConsultantTitleHistory.StartDate)
        ).label('last_project_date')
    ).join(
        ConsultantTitleHistory,
        (Consultant.ConsultantID == ConsultantTitleHistory.ConsultantID) &
        (ConsultantTitleHistory.StartDate <= current_date) &
        ((ConsultantTitleHistory.EndDate.is_(None)) | (ConsultantTitleHistory.EndDate > current_date))
    ).outerjoin(
        ProjectTeam,
        Consultant.ConsultantID == ProjectTeam.ConsultantID
    ).group_by(
        Consultant.ConsultantID,
        ConsultantTitleHistory.TitleID
    ).having(
        func.count(ProjectTeam.ID) < 3
    ).order_by(
        'last_project_date'
    ).all()

    logging.info(f"Date: {current_date}, Available Consultants: {len(available_consultants)}")
    for consultant, title_id, last_project_date in available_consultants:
        logging.debug(f"Available Consultant: {consultant.ConsultantID}, Title: {title_id}, Last Project: {last_project_date}")

    return available_consultants

def is_consultant_available(session, consultant_id, current_date):
    # Consider only projects that have been active in the last 2 months
    two_months_ago = current_date - timedelta(days=60)
    
    active_projects = session.query(func.count(ProjectTeam.ProjectID)).filter(
        ProjectTeam.ConsultantID == consultant_id,
        ProjectTeam.StartDate <= current_date,
        (ProjectTeam.EndDate.is_(None) | (ProjectTeam.EndDate >= two_months_ago)),
        Project.Status.in_(['In Progress', 'Not Started'])  # Only consider active projects
    ).join(Project).scalar()
    
    return active_projects < 5

def assign_project_to_business_unit(session, assigned_consultants, active_units, current_year):
    from ...db_model import Project
    
    consultant_unit_counts = Counter(consultant.BusinessUnitID for consultant, _, _ in assigned_consultants)
    
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

def assign_consultants_to_project(available_consultants, project_manager):
    assigned_consultants = [project_manager]
    other_consultants = [c for c in available_consultants if c != project_manager]
    
    # Possibly assign a second manager
    high_level_consultants = [c for c in other_consultants if c[1] >= 4]
    if high_level_consultants and random.random() < 0.5:
        second_manager = random.choice(high_level_consultants)
        assigned_consultants.append(second_manager)
        other_consultants.remove(second_manager)
    
    # Assign team members
    low_level_consultants = [c for c in other_consultants if c[1] < 4]
    team_size = random.randint(3, 8)  # Adjust as needed
    team_members = random.sample(low_level_consultants, min(len(low_level_consultants), team_size))
    assigned_consultants.extend(team_members)

    return assigned_consultants

def set_project_dates(project, current_date, assigned_consultants, session, simulation_start_date):
    if project.Type == 'Fixed':
        duration_months = random.randint(*project_settings.FIXED_PROJECT_DURATION_RANGE)
    else:  # Time and Material
        duration_months = random.randint(*project_settings.TIME_MATERIAL_PROJECT_DURATION_RANGE)
    
    project_manager = next(c for c, title_id, _ in assigned_consultants if title_id >= 4)
    pm_availability = max(get_consultant_availability(session, project_manager.ConsultantID, current_date), simulation_start_date)
    
    # Add more variance to the start date
    planned_start = pm_availability + timedelta(days=random.randint(0, 30))
    actual_start_variance = timedelta(days=random.randint(-14, 14))
    
    project.PlannedStartDate = planned_start
    project.ActualStartDate = max(planned_start + actual_start_variance, simulation_start_date)
    
    # Set initial status based on start date
    if project.ActualStartDate <= current_date:
        project.Status = 'In Progress'
    
    # Calculate end date based on working days
    working_days = duration_months * 21  # 21 working days per month
    project.PlannedEndDate = project.PlannedStartDate
    days_added = 0
    while days_added < working_days:
        project.PlannedEndDate += timedelta(days=1)
        if project.PlannedEndDate.weekday() < 5: 
            days_added += 1
    
    return len(assigned_consultants)

def get_consultant_availability(session, consultant_id, current_date):
    latest_project = session.query(func.max(ProjectTeam.EndDate)).filter(
        ProjectTeam.ConsultantID == consultant_id,
        ProjectTeam.EndDate.isnot(None)
    ).scalar()
    
    return max(current_date, latest_project + timedelta(days=1)) if latest_project else current_date

def generate_deliverables(project, target_hours):
    num_deliverables = random.randint(*project_settings.DELIVERABLE_COUNT_RANGE)
    deliverables = []
    remaining_target_hours = target_hours
    project_duration = (project.PlannedEndDate - project.PlannedStartDate).days

    for i in range(num_deliverables):
        is_last_deliverable = (i == num_deliverables - 1)
        
        if is_last_deliverable:
            deliverable_target_hours = remaining_target_hours
        else:
            min_hours = 10
            max_hours = max(min_hours, math.floor(remaining_target_hours - (num_deliverables - i - 1) * min_hours))
            deliverable_target_hours = random.randint(math.floor(min_hours), math.floor(max_hours))
            remaining_target_hours -= deliverable_target_hours

        start_date = project.PlannedStartDate if i == 0 else deliverables[-1].DueDate + timedelta(days=1)
        deliverable_duration = max(1, int((deliverable_target_hours / target_hours) * project_duration))
        due_date = min(start_date + timedelta(days=deliverable_duration), project.PlannedEndDate)

        deliverable = Deliverable(
            ProjectID=project.ProjectID,
            Name=f"Deliverable {i+1}",
            PlannedStartDate=start_date,
            DueDate=due_date,
            PlannedHours=round(deliverable_target_hours * (project.PlannedHours / target_hours)),
            ActualHours=0,
            Progress=0
        )
        deliverables.append(deliverable)

    return deliverables

def calculate_project_financials(session, project, assigned_consultants, current_date, deliverables):
    # Calculate average hourly cost for each title
    title_hourly_costs = {}
    for consultant, title_id, _ in assigned_consultants:
        if title_id not in title_hourly_costs:
            title_hourly_costs[title_id] = calculate_hourly_cost(session, consultant.ConsultantID, current_date.year)

    # Calculate estimated total cost
    estimated_total_cost = sum(Decimal(title_hourly_costs[title_id]) * Decimal(project.PlannedHours) 
                               for _, title_id, _ in assigned_consultants)

    if project.Type == 'Fixed':
        profit_margin = Decimal(random.uniform(*project_settings.PROFIT_MARGIN_RANGE))
        project.Price = float(round_to_nearest_thousand(estimated_total_cost * (Decimal('1') + profit_margin)))
    else:  # Time and Material
        project.EstimatedBudget = float(round_to_nearest_thousand(estimated_total_cost * project_settings.ESTIMATED_BUDGET_FACTORS))
        
        # Generate Project Billing Rates with variance
        billing_rates = []
        for title_id, hourly_cost in title_hourly_costs.items():
            base_billing_rate = Decimal(hourly_cost) * (Decimal('1') + Decimal(random.uniform(*project_settings.PROFIT_MARGIN_RANGE)))
            variance = Decimal(random.uniform(-0.1, 0.1))  # Add up to 10% variance
            billing_rate = base_billing_rate * (Decimal('1') + variance)
            billing_rate = round(billing_rate / Decimal('5')) * Decimal('5')  # Round to nearest $5
            billing_rates.append(ProjectBillingRate(
                ProjectID=project.ProjectID,
                TitleID=title_id,
                Rate=float(billing_rate)
            ))
        session.add_all(billing_rates)

    project.pre_generated_expenses = generate_project_expenses(project, float(estimated_total_cost), deliverables)

    # Distribute price to deliverables for fixed contracts
    if project.Type == 'Fixed':
        total_planned_hours = sum(d.PlannedHours for d in deliverables)
        for deliverable in deliverables:
            deliverable.Price = round(project.Price * (deliverable.PlannedHours / total_planned_hours))
            
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

def update_project_team(session, project, available_consultants, current_team, current_date):
    target_team_size = project_settings.TARGET_TEAM_SIZE
    
    if len(current_team) < target_team_size:
        potential_new_members = [
            (c, title_id) for c, title_id, _ in available_consultants 
            if c.ConsultantID not in current_team and title_id <= 3
        ]
        new_members_count = min(target_team_size - len(current_team), len(potential_new_members))
        
        for consultant, title_id in random.sample(potential_new_members, new_members_count):
            team_member = ProjectTeam(
                ProjectID=project.ProjectID,
                ConsultantID=consultant.ConsultantID,
                Role='Team Member',
                StartDate=current_date
            )
            session.add(team_member)
            current_team.append(consultant.ConsultantID)
            logging.info(f"Added consultant {consultant.ConsultantID} to project {project.ProjectID} team")

    logging.info(f"Updated team size for project {project.ProjectID}: {len(current_team)} members")

def log_consultant_projects(session, current_date):
    consultants = session.query(Consultant).all()
    for consultant in consultants:
        active_projects = session.query(Project).join(ProjectTeam).filter(
            ProjectTeam.ConsultantID == consultant.ConsultantID,
            ProjectTeam.StartDate <= current_date,
            (ProjectTeam.EndDate.is_(None) | (ProjectTeam.EndDate >= current_date)),
            Project.Status.in_(['Not Started', 'In Progress'])
        ).all()
        
        logging.info(f"Date: {current_date}, ConsultantID: {consultant.ConsultantID}, Active Projects: {len(active_projects)}")
        for project in active_projects:
            logging.debug(f"  ProjectID: {project.ProjectID}, Status: {project.Status}, Start Date: {project.ActualStartDate}")
