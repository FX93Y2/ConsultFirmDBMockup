import random
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.orm import sessionmaker
from sqlalchemy import func, or_
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP
from src.create_db import (Project, Consultant, BusinessUnit, Client, ProjectBillingRate, 
                         ProjectExpense, Deliverable, ConsultantDeliverable, ConsultantTitleHistory, 
                         Payroll, engine)
from ..utils.project_utils import (round_to_nearest_thousand, adjust_hours, calculate_hourly_cost, 
                                 determine_project_count, calculate_project_progress)
from config import project_settings

def get_active_business_units(session, year):
    return session.query(BusinessUnit).join(Consultant).filter(
        Consultant.HireYear <= year
    ).distinct().all()

def get_available_consultants(session, year):
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)
    
    return session.query(Consultant).join(ConsultantTitleHistory).filter(
        ConsultantTitleHistory.StartDate <= end_date,
        or_(ConsultantTitleHistory.EndDate >= start_date, ConsultantTitleHistory.EndDate == None),
        ConsultantTitleHistory.EventType.notin_(['Layoff', 'Attrition'])
    ).all()

def get_consultant_daily_hours(session, consultant_id, date):
    total_hours = session.query(func.sum(ConsultantDeliverable.Hours)).filter(
        ConsultantDeliverable.ConsultantID == consultant_id,
        ConsultantDeliverable.Date == date
    ).scalar() or 0
    return total_hours

def get_latest_consultant_start_date(assigned_consultants, session, current_year):
    latest_start_date = date(current_year, 1, 1)
    for consultant in assigned_consultants:
        title_history = session.query(ConsultantTitleHistory).filter(
            ConsultantTitleHistory.ConsultantID == consultant.ConsultantID,
            ConsultantTitleHistory.StartDate.between(date(current_year, 1, 1), date(current_year, 12, 31))
        ).order_by(ConsultantTitleHistory.StartDate.desc()).first()
        
        if title_history and title_history.StartDate > latest_start_date:
            latest_start_date = title_history.StartDate
    
    return latest_start_date

def assign_project_to_business_unit(session, assigned_consultants, active_units, current_year):
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

def assign_consultants_to_project(available_consultants, session):
    consultants_by_title = {}
    for consultant in available_consultants:
        current_title = session.query(ConsultantTitleHistory).filter(
            ConsultantTitleHistory.ConsultantID == consultant.ConsultantID
        ).order_by(ConsultantTitleHistory.StartDate.desc()).first()
        
        if current_title:
            title_id = current_title.TitleID
            if title_id not in consultants_by_title:
                consultants_by_title[title_id] = []
            consultants_by_title[title_id].append(consultant)

    assigned_consultants = []

    higher_level_titles = [5, 6]
    for title_id in higher_level_titles:
        if title_id in consultants_by_title and consultants_by_title[title_id]:
            higher_level_consultant = random.choice(consultants_by_title[title_id])
            assigned_consultants.append(higher_level_consultant)
            consultants_by_title[title_id].remove(higher_level_consultant)
            break

    all_consultants = [c for consultants in consultants_by_title.values() for c in consultants]
    num_additional_consultants = min(len(all_consultants), random.randint(2, 5))
    assigned_consultants.extend(random.sample(all_consultants, num_additional_consultants))

    return assigned_consultants

def set_project_dates(project, current_year, assigned_consultants, session):
    if project.Type == 'Fixed':
        duration_months = random.randint(*project_settings.FIXED_PROJECT_DURATION_RANGE)
    else:  # Time and Material
        duration_months = random.randint(*project_settings.TIME_MATERIAL_PROJECT_DURATION_RANGE)
    
    latest_consultant_start = get_latest_consultant_start_date(assigned_consultants, session, current_year)
    
    earliest_possible_start = date(current_year, 1, 1)
    latest_possible_start = date(current_year, 12, 31)
    
    planned_start_options = [
        earliest_possible_start,
        latest_consultant_start - timedelta(days=random.randint(0, 90)),
        date(current_year, random.randint(1, 12), random.randint(1, 28))
    ]
    planned_start = max(earliest_possible_start, min(random.choice(planned_start_options), latest_possible_start))
    
    project.PlannedStartDate = planned_start
    project.PlannedEndDate = project.PlannedStartDate + timedelta(days=duration_months * 30)
    
    return duration_months

def generate_project_expenses(project, total_consultant_cost):
    expenses = []
    
    for category, percentage in project_settings.EXPENSE_CATEGORIES.items():
        amount = round(total_consultant_cost * percentage * random.uniform(0.8, 1.2), -3)
        expense = ProjectExpense(
            ProjectID=project.ProjectID,
            Date=project.PlannedStartDate + timedelta(days=random.randint(0, (project.PlannedEndDate - project.PlannedStartDate).days)),
            Amount=amount,
            Description=f"{category} expense for {project.Name}",
            Category=category,
            IsBillable=False
        )
        expenses.append(expense)
    
    return expenses

def calculate_project_financials(project, assigned_consultants, session, current_year):
    total_consultant_cost = sum(calculate_hourly_cost(session, consultant, current_year) * project.PlannedHours 
                                for consultant in assigned_consultants)

    expenses = generate_project_expenses(project, total_consultant_cost)
    total_expenses = sum(expense.Amount for expense in expenses)
    
    total_cost = total_consultant_cost + total_expenses
    
    if project.Type == 'Fixed':
        profit_margin = random.uniform(*project_settings.PROFIT_MARGIN_RANGE)
        project.Price = total_cost * (1 + profit_margin)
    else:  # Time and Material
        project.Price = None
        
    return expenses

def generate_project_billing_rates(session, project, assigned_consultants):
    billing_rates = []
    
    if project.Type == 'Time and Material':
        assigned_titles = set()
        
        for consultant in assigned_consultants:
            current_title = session.query(ConsultantTitleHistory).filter(
                ConsultantTitleHistory.ConsultantID == consultant.ConsultantID
            ).order_by(ConsultantTitleHistory.StartDate.desc()).first()
            
            if current_title and current_title.TitleID not in assigned_titles:
                base_rate = project_settings.BASE_BILLING_RATES[current_title.TitleID]
                adjusted_rate = base_rate * random.uniform(1.0, 1.2)
                adjusted_rate = round(adjusted_rate / 5) * 5
                
                billing_rate = ProjectBillingRate(
                    ProjectID=project.ProjectID,
                    TitleID=current_title.TitleID,
                    Rate=adjusted_rate
                )
                billing_rates.append(billing_rate)
                assigned_titles.add(current_title.TitleID)
    
    return billing_rates

def generate_deliverables(project):
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
            max_hours = max(min_hours, remaining_hours - (num_deliverables - i - 1) * min_hours)
            planned_hours = random.randint(min_hours, max_hours)
            remaining_hours -= planned_hours

        start_date = project.PlannedStartDate if i == 0 else deliverables[-1].DueDate + timedelta(days=1)
        deliverable_duration = max(1, int((planned_hours / project.PlannedHours) * project_duration))
        due_date = min(start_date + timedelta(days=deliverable_duration), project.PlannedEndDate)

        price = None
        if project.Type == 'Fixed':
            price = round_to_nearest_thousand((Decimal(planned_hours) / Decimal(project.PlannedHours) * Decimal(project.Price)))

        deliverable = Deliverable(
            ProjectID=project.ProjectID,
            Name=f"Deliverable {i+1}",
            PlannedStartDate=start_date,
            Status='Not Started',
            DueDate=due_date,
            PlannedHours=planned_hours,
            ActualHours=0,
            Progress=0,
            Price=price
        )
        deliverables.append(deliverable)

    return deliverables


def generate_consultant_deliverables(deliverables, assigned_consultants, project, end_year, session):
    consultant_deliverables = []
    simulation_end_date = date(end_year, 12, 31)

    project.ActualHours = adjust_hours(project.PlannedHours)
    hour_adjustment_factor = project.ActualHours / Decimal(project.PlannedHours) if project.PlannedHours > 0 else Decimal('1')

    total_actual_hours = Decimal('0')
    for deliverable in deliverables:
        deliverable.ActualHours = Decimal('0')
        target_hours = (Decimal(deliverable.PlannedHours) * hour_adjustment_factor).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
        remaining_hours = target_hours
        
        start_date = max(deliverable.PlannedStartDate, project.PlannedStartDate)
        end_date = min(simulation_end_date, deliverable.DueDate)
        
        current_date = start_date
        
        while remaining_hours > Decimal('0') and current_date <= end_date:
            consultants_working_today = [c for c in assigned_consultants if random.random() < project_settings.WORK_PROBABILITY]
            
            if not consultants_working_today:
                current_date += timedelta(days=1)
                continue
            
            for consultant in consultants_working_today:
                if remaining_hours <= Decimal('0'):
                    break
                
                consultant_daily_hours = get_consultant_daily_hours(session, consultant.ConsultantID, current_date)
                available_hours = max(0, project_settings.MAX_DAILY_HOURS - consultant_daily_hours)
                
                if available_hours <= 0:
                    continue
                
                max_consultant_hours = min(Decimal(available_hours), remaining_hours)
                consultant_hours = Decimal(random.uniform(float(project_settings.MIN_DAILY_HOURS), float(max_consultant_hours))).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
                
                if consultant_hours > Decimal('0'):
                    consultant_deliverable = ConsultantDeliverable(
                        ConsultantID=consultant.ConsultantID,
                        DeliverableID=deliverable.DeliverableID,
                        Date=current_date,
                        Hours=float(consultant_hours)
                    )
                    consultant_deliverables.append(consultant_deliverable)
                    remaining_hours -= consultant_hours
                    total_actual_hours += consultant_hours
                    deliverable.ActualHours += consultant_hours
                    
                    if deliverable.ActualStartDate is None:
                        deliverable.ActualStartDate = current_date
            
            current_date += timedelta(days=1)
        
        if deliverable.ActualHours > 0:
            deliverable.SubmissionDate = current_date - timedelta(days=1)

    project.ActualHours = float(total_actual_hours)

    return consultant_deliverables


def update_project_and_deliverable_status(project, deliverables):
    project.ActualStartDate = None
    project.ActualEndDate = None
    project.Status = 'Not Started'

    for deliverable in deliverables:
        if deliverable.ActualHours > 0:
            deliverable.Status = 'Completed' if deliverable.ActualHours >= deliverable.PlannedHours else 'In Progress'
            deliverable.Progress = min(100, int((deliverable.ActualHours / deliverable.PlannedHours) * 100))
            
            if project.ActualStartDate is None or deliverable.ActualStartDate < project.ActualStartDate:
                project.ActualStartDate = deliverable.ActualStartDate
            
            if deliverable.Status == 'Completed' and (project.ActualEndDate is None or deliverable.SubmissionDate > project.ActualEndDate):
                project.ActualEndDate = deliverable.SubmissionDate

    calculate_project_progress(project, deliverables)

    if project.Progress > 0:
        project.Status = 'Completed' if project.Progress == 100 else 'In Progress'

    if project.Status == 'Completed' and project.ActualEndDate is None:
        project.ActualEndDate = max(d.SubmissionDate for d in deliverables if d.SubmissionDate)

    return project, deliverables

def generate_projects(start_year, end_year):
    Session = sessionmaker(bind=engine)
    session = Session()
    print("Generating Project Data...")

    try:
        for current_year in range(start_year, end_year + 1):
            available_consultants = get_available_consultants(session, current_year)
            active_units = get_active_business_units(session, current_year)
            growth_rate = 0.1
            num_projects = determine_project_count(available_consultants, growth_rate)
            
            for _ in range(num_projects):
                assigned_consultants = assign_consultants_to_project(available_consultants, session)
                assigned_unit_id = assign_project_to_business_unit(session, assigned_consultants, active_units, current_year)
                
                project = Project(
                    ClientID=random.choice(session.query(Client.ClientID).all())[0],
                    UnitID=assigned_unit_id,
                    Name=f"Project_{current_year}_{random.randint(1000, 9999)}",
                    Type=random.choices(project_settings.PROJECT_TYPES, weights=project_settings.PROJECT_TYPE_WEIGHTS)[0],
                    Status='Not Started',
                    Progress=0
                )
                
                session.add(project)
                session.flush()  # This will populate the ProjectID

                duration_months = set_project_dates(project, current_year, assigned_consultants, session)
                project.PlannedHours = duration_months * project_settings.WORKING_HOURS_PER_MONTH
                project.ActualHours = 0
                
                expenses = calculate_project_financials(project, assigned_consultants, session, current_year)
                session.add_all(expenses)
                
                billing_rates = generate_project_billing_rates(session, project, assigned_consultants)
                session.add_all(billing_rates)
                
                deliverables = generate_deliverables(project)
                session.add_all(deliverables)
                session.flush()  # This will populate DeliverableID

                consultant_deliverables = generate_consultant_deliverables(deliverables, assigned_consultants, project, end_year, session)                
                session.add_all(consultant_deliverables)
                
                project, deliverables = update_project_and_deliverable_status(project, deliverables)
                
                session.add(project)
                session.add_all(deliverables)

                if project.Price:
                    project.Price = round_to_nearest_thousand(project.Price)
            
            session.commit()
            print(f"Generated {num_projects} projects for year {current_year}")
            
    except Exception as e:
        print(f"An error occurred while processing projects: {str(e)}")
        session.rollback()
    finally:
        session.close()
    print("Complete")
    