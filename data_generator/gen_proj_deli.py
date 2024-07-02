import random
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.orm import sessionmaker
from sqlalchemy import func, or_, and_
from .create_db import (Project, Consultant, BusinessUnit, Client, ProjectBillingRate, 
                       ProjectExpense, Deliverable, ConsultantDeliverable, ConsultantTitleHistory, 
                       Payroll, engine)

MIN_DAILY_HOURS = Decimal('1.0')
MAX_DAILY_HOURS = Decimal('8.0')
WORK_PROBABILITY = 0.9  # 90% chance of working on any given day

def round_to_nearest_thousand(value):
    return int(Decimal(value).quantize(Decimal('1000'), rounding=ROUND_HALF_UP))

def get_available_consultants(session, year):
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)
    
    available_consultants = session.query(Consultant).join(ConsultantTitleHistory).filter(
        ConsultantTitleHistory.StartDate <= end_date,
        or_(ConsultantTitleHistory.EndDate >= start_date, ConsultantTitleHistory.EndDate == None),
        ConsultantTitleHistory.EventType.notin_(['Layoff', 'Attrition'])
    ).all()
    
    return available_consultants

def adjust_hours(planned_hours):
    if random.random() < 0.1:  # 10% chance of finishing early
        actual_hours = Decimal(planned_hours) * Decimal(random.uniform(0.8, 0.95))
    else:  # 90% chance of overrunning
        actual_hours = Decimal(planned_hours) * Decimal(random.uniform(1.05, 1.3))
    return actual_hours.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)

def adjust_end_date(start_date, planned_end_date, planned_hours, actual_hours):
    planned_duration = (planned_end_date - start_date).days + 1
    if planned_hours == 0:
        actual_duration = planned_duration
    else:
        actual_duration = int((actual_hours / Decimal(planned_hours)) * planned_duration)
    actual_end_date = start_date + timedelta(days=max(0, actual_duration - 1))
    actual_end_date += timedelta(days=random.randint(-2, 2))
    return max(start_date, actual_end_date)

def calculate_hourly_cost(session, consultant, year):
    payroll_data = session.query(Payroll).filter(
        Payroll.ConsultantID == consultant.ConsultantID,
        func.extract('year', Payroll.EffectiveDate) == year
    ).all()
    
    if not payroll_data:
        return 0
    
    total_salary = sum(p.Amount for p in payroll_data)
    avg_monthly_salary = total_salary / len(payroll_data)
    hourly_cost = (avg_monthly_salary * 12) / (52 * 40)  # Assuming 52 weeks and 40 hours per week
    return hourly_cost * 1.3  # Adding 30% for overhead

def determine_project_count(available_consultants, growth_rate):
    base_count = len(available_consultants) // random.randint(3, 5)
    adjusted_count = int(base_count * (1 + growth_rate))
    return max(5, adjusted_count)

def assign_consultants_to_project(project, available_consultants, session):
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

    # Ensure at least one high-level consultant (Project Manager or above)
    higher_level_titles = [5, 6]
    for title_id in higher_level_titles:
        if title_id in consultants_by_title and consultants_by_title[title_id]:
            higher_level_consultant = random.choice(consultants_by_title[title_id])
            assigned_consultants.append(higher_level_consultant)
            consultants_by_title[title_id].remove(higher_level_consultant)
            break

    # Assign a mix of other consultants
    all_consultants = [c for consultants in consultants_by_title.values() for c in consultants]
    num_additional_consultants = min(len(all_consultants), random.randint(2, 5))
    assigned_consultants.extend(random.sample(all_consultants, num_additional_consultants))

    return assigned_consultants

def set_project_dates(project, current_year):
    if project.Type == 'Fixed':
        duration_months = random.randint(3, 24) 
    else:  # Time and Material
        duration_months = random.randint(1, 36)
    
    start_month = random.randint(1, 12)
    start_day = random.randint(1, 28)  # Avoid issues with February
    
    project.PlannedStartDate = date(current_year, start_month, start_day)
    project.PlannedEndDate = project.PlannedStartDate + timedelta(days=duration_months * 30)
    project.ActualStartDate = project.PlannedStartDate
    
    return duration_months

def generate_project_expenses(project, total_consultant_cost):
    expenses = []
    expense_categories = {
        'Travel': 0.1,
        'Equipment': 0.05,
        'Software Licenses': 0.03,
        'Training': 0.02,
        'Miscellaneous': 0.05
    }
    
    for category, percentage in expense_categories.items():
        amount = total_consultant_cost * percentage * random.uniform(0.8, 1.2)
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
    total_consultant_cost = 0
    for consultant in assigned_consultants:
        hourly_cost = calculate_hourly_cost(session, consultant, current_year)
        total_consultant_cost += hourly_cost * project.PlannedHours

    expenses = generate_project_expenses(project, total_consultant_cost)
    total_expenses = sum(expense.Amount for expense in expenses)
    
    total_cost = total_consultant_cost + total_expenses
    
    if project.Type == 'Fixed':
        profit_margin = random.uniform(0.15, 0.30)
        project.Price = total_cost * (1 + profit_margin)
    else:  # Time and Material
        project.Price = None
        
    return expenses

def calculate_project_progress(project, deliverables):
    total_planned_hours = sum(d.PlannedHours for d in deliverables)
    weighted_progress = sum((d.Progress * d.PlannedHours) for d in deliverables)
    project.Progress = int(weighted_progress / total_planned_hours) if total_planned_hours > 0 else 0

def generate_project_billing_rates(session, project, assigned_consultants):
    billing_rates = []
    
    if project.Type == 'Time and Material':
        base_rates = {1: 100, 2: 150, 3: 200, 4: 250, 5: 300, 6: 400}
        assigned_titles = set()
        
        for consultant in assigned_consultants:
            current_title = session.query(ConsultantTitleHistory).filter(
                ConsultantTitleHistory.ConsultantID == consultant.ConsultantID
            ).order_by(ConsultantTitleHistory.StartDate.desc()).first()
            
            if current_title and current_title.TitleID not in assigned_titles:
                base_rate = base_rates[current_title.TitleID]
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
    num_deliverables = random.randint(3, 7)
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
            ActualStartDate=start_date,
            Status='Not Started',
            DueDate=due_date,
            PlannedHours=planned_hours,
            ActualHours=0,
            Progress=0,
            Price=price
        )
        deliverables.append(deliverable)

    return deliverables

def generate_consultant_deliverables(deliverables, assigned_consultants, project, end_year):
    consultant_deliverables = []
    simulation_end_date = date(end_year, 12, 31)

    project.ActualHours = adjust_hours(project.PlannedHours)
    project_extends_beyond_simulation = project.PlannedEndDate > simulation_end_date

    hour_adjustment_factor = project.ActualHours / Decimal(project.PlannedHours) if project.PlannedHours > 0 else Decimal('1')

    total_actual_hours = Decimal('0')
    for deliverable in deliverables:
        deliverable.ActualHours = (Decimal(deliverable.PlannedHours) * hour_adjustment_factor).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
        remaining_hours = deliverable.ActualHours
        
        start_date = max(deliverable.PlannedStartDate, project.ActualStartDate)
        end_date = simulation_end_date
        
        current_date = start_date
        
        while remaining_hours > Decimal('0') and current_date <= end_date:
            consultants_working_today = [c for c in assigned_consultants if random.random() < WORK_PROBABILITY]
            
            if not consultants_working_today:
                current_date += timedelta(days=1)
                continue
            
            daily_hours_left = Decimal(len(consultants_working_today)) * MAX_DAILY_HOURS
            
            for consultant in consultants_working_today:
                if remaining_hours <= Decimal('0') or daily_hours_left <= Decimal('0'):
                    break
                
                max_consultant_hours = min(MAX_DAILY_HOURS, daily_hours_left, remaining_hours)
                consultant_hours = Decimal(random.uniform(float(MIN_DAILY_HOURS), float(max_consultant_hours))).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
                
                if consultant_hours > Decimal('0'):
                    consultant_deliverable = ConsultantDeliverable(
                        ConsultantID=consultant.ConsultantID,
                        DeliverableID=deliverable.DeliverableID,
                        Date=current_date,
                        Hours=float(consultant_hours)
                    )
                    consultant_deliverables.append(consultant_deliverable)
                    remaining_hours -= consultant_hours
                    daily_hours_left -= consultant_hours
                    total_actual_hours += consultant_hours
            
            current_date += timedelta(days=1)
        
        deliverable.ActualHours = float(deliverable.ActualHours - remaining_hours)
        
        if deliverable.PlannedHours > 0:
            deliverable.Progress = min(100, int((deliverable.ActualHours / deliverable.PlannedHours) * 100))
        else:
            deliverable.Progress = 100 if deliverable.ActualHours > 0 else 0
        
        if deliverable.Progress < 100:
            deliverable.Status = 'In Progress'
        else:
            deliverable.Status = 'Completed'
            deliverable.SubmissionDate = current_date
            if project.Type == 'Fixed':
                deliverable.InvoicedDate = deliverable.SubmissionDate + timedelta(days=random.randint(0, 7))
        
        if remaining_hours > Decimal('0.1'):
            print(f"Warning: Deliverable {deliverable.DeliverableID} has {float(remaining_hours):.1f} unallocated hours")

    project.ActualHours = float(total_actual_hours)
    calculate_project_progress(project, deliverables)

    if project.Progress < 100:
        project.Status = 'In Progress'
        project.ActualEndDate = None
    else:
        project.Status = 'Completed'
        project.ActualEndDate = max(d.SubmissionDate for d in deliverables if d.SubmissionDate)

    return consultant_deliverables



def update_project_status(project, current_date):
    if current_date < project.PlannedStartDate:
        project.Status = 'Not Started'
        project.Progress = 0
    elif current_date >= project.PlannedStartDate and current_date <= project.PlannedEndDate:
        project.Status = 'In Progress'
        total_duration = (project.PlannedEndDate - project.PlannedStartDate).days
        elapsed_duration = (current_date - project.PlannedStartDate).days
        project.Progress = min(int((elapsed_duration / total_duration) * 100), 99)
    else:
        project.Status = 'Completed'
        project.Progress = 100
        if not project.ActualEndDate:
            project.ActualEndDate = project.PlannedEndDate

def update_deliverable_status(deliverable, current_date):
    if current_date < deliverable.PlannedStartDate:
        deliverable.Status = 'Not Started'
        deliverable.Progress = 0
    elif current_date >= deliverable.PlannedStartDate and current_date <= deliverable.DueDate:
        deliverable.Status = 'In Progress'
        total_duration = (deliverable.DueDate - deliverable.PlannedStartDate).days
        elapsed_duration = (current_date - deliverable.PlannedStartDate).days
        deliverable.Progress = min(int((elapsed_duration / total_duration) * 100), 99)
    else:
        deliverable.Status = 'Completed'
        deliverable.Progress = 100
        if not deliverable.SubmissionDate:
            deliverable.SubmissionDate = deliverable.DueDate

def generate_projects(start_year, end_year):
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        for current_year in range(start_year, end_year + 1):
            
            available_consultants = get_available_consultants(session, current_year)
            growth_rate = 0.1
            num_projects = determine_project_count(available_consultants, growth_rate)
            
            for _ in range(num_projects):
                project = Project(
                    ClientID=random.choice(session.query(Client.ClientID).all())[0],
                    UnitID=random.choice(session.query(BusinessUnit.BusinessUnitID).all())[0],
                    Name=f"Project_{current_year}_{random.randint(1000, 9999)}",
                    Type=random.choice(['Fixed', 'Time and Material']),
                    Status='Not Started',
                    Progress=0
                )
                
                session.add(project)
                session.flush()  # This will populate the ProjectID
                
                assigned_consultants = assign_consultants_to_project(project, available_consultants, session)
                duration_months = set_project_dates(project, current_year)
                
                project.PlannedHours = duration_months * 160  # Say 160 working hours per month
                project.ActualHours = adjust_hours(project.PlannedHours)
                
                expenses = calculate_project_financials(project, assigned_consultants, session, current_year)
                session.add_all(expenses)
                
                billing_rates = generate_project_billing_rates(session, project, assigned_consultants)
                session.add_all(billing_rates)
                
                deliverables = generate_deliverables(project)
                session.add_all(deliverables)
                session.flush()  # This will populate the DeliverableID

                consultant_deliverables = generate_consultant_deliverables(deliverables, assigned_consultants, project, end_year)                
                session.add_all(consultant_deliverables)
                
                # Rounding the project price to the nearest thousand
                if project.Price:
                    project.Price = round_to_nearest_thousand(project.Price)
            
            session.commit()
            print(f"Generated {num_projects} projects for year {current_year}")
            
    except Exception as e:
        print(f"An error occurred while processing project {project.ProjectID}: {str(e)}")
        session.rollback()
    finally:
        session.close()

def main(start_year, end_year):
    print("Generating Project Data...")
    generate_projects(start_year, end_year)
    print("Complete")
