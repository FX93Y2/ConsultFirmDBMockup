import random
from faker import Faker
from datetime import date, timedelta
from sqlalchemy.orm import sessionmaker
from sqlalchemy import func, or_
from collections import defaultdict
from data_generator.create_db import (Project, Consultant, BusinessUnit, Client, ProjectBillingRate, 
                                      ProjectExpense,Deliverable, ConsultantDeliverable, ConsultantTitleHistory, engine)
from data_generator.gen_cons_title_hist import get_growth_rate
fake = Faker()

def get_project_type():
    return random.choices(['Time and Material', 'Fixed'], weights=[0.6, 0.4])[0]

def generate_basic_project(session, current_year):
    project = Project(
        ClientID=random.choice(session.query(Client.ClientID).all())[0],
        UnitID=random.choice(session.query(BusinessUnit.BusinessUnitID).all())[0],
        Name=f"Project_{current_year}_{random.randint(1000, 9999)}",
        Type=get_project_type(),
        Status='Not Started',
        Progress=0
    )
    return project

def find_available_consultants(session, year):
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)
    
    available_consultants = session.query(Consultant).join(ConsultantTitleHistory).\
        filter(ConsultantTitleHistory.StartDate <= end_date).\
        filter(or_(ConsultantTitleHistory.EndDate >= start_date, ConsultantTitleHistory.EndDate == None)).\
        all()
    
    # Reset project count for each consultant at the start of the year
    for consultant in available_consultants:
        consultant.project_count = 0
    
    return available_consultants

def determine_project_count(available_consultants, growth_rate):
    base_count = len(available_consultants) // random.randint(3, 5)
    adjusted_count = int(base_count * (1 + growth_rate))
    return max(5, adjusted_count)

def assign_consultants_to_project(project, available_consultants, session):
    consultants_by_title = defaultdict(list)
    for consultant in available_consultants:
        current_title = session.query(ConsultantTitleHistory).\
            filter(ConsultantTitleHistory.ConsultantID == consultant.ConsultantID).\
            order_by(ConsultantTitleHistory.StartDate.desc()).first()
        
        if current_title:
            consultants_by_title[current_title.TitleID].append(consultant)

    assigned_consultants = []

    # Ensure at least one high-level consultant (Project Manager or above)
    higher_level_titles = [5, 6]  # 5: Project Manager, 6: Vice President
    for title_id in higher_level_titles:
        if consultants_by_title[title_id]:
            higher_level_consultant = random.choice(consultants_by_title[title_id])
            assigned_consultants.append(higher_level_consultant)
            consultants_by_title[title_id].remove(higher_level_consultant)
            break

    # Assign a mix of other consultants
    num_additional_consultants = random.randint(4, 8)  # Increase team size for larger projects
    all_consultants = [c for consultants in consultants_by_title.values() for c in consultants]
    
    for _ in range(num_additional_consultants):
        if all_consultants:
            consultant = random.choice(all_consultants)
            assigned_consultants.append(consultant)
            all_consultants.remove(consultant)

    project.AssignedConsultants = assigned_consultants
    return assigned_consultants

def calculate_project_costs(project, assigned_consultants, session):
    # Get the project duration in days
    project_duration = (project.PlannedEndDate - project.PlannedStartDate).days
    
    total_cost = 0
    for consultant in assigned_consultants:
        # Get the consultant's current salary
        current_title = session.query(ConsultantTitleHistory).\
            filter(ConsultantTitleHistory.ConsultantID == consultant.ConsultantID).\
            order_by(ConsultantTitleHistory.StartDate.desc()).first()
        
        if current_title:
            yearly_salary = current_title.Salary
            daily_rate = yearly_salary / 260  # Assuming 260 working days per year
            
            # Assume consultants spend 50-80% of their time on there project
            time_allocation = random.uniform(0.5, 0.8)
            consultant_cost = daily_rate * project_duration * time_allocation
            
            total_cost += consultant_cost

    # Add some overhead cost
    overhead_rate = 0.3
    total_cost += total_cost * overhead_rate
    
    return total_cost

def set_project_dates(project, assigned_consultants, session, current_year):
    # Base duration factors
    BASE_DURATION = 90  # 3 month base duration
    CONSULTANT_FACTOR = 1.1
    SENIORITY_FACTOR = 1.2

    # Calculate project duration based on the number and seniority of consultants
    duration = BASE_DURATION
    for consultant in assigned_consultants:
        duration *= CONSULTANT_FACTOR
        
        current_title = session.query(ConsultantTitleHistory).\
            filter(ConsultantTitleHistory.ConsultantID == consultant.ConsultantID).\
            order_by(ConsultantTitleHistory.StartDate.desc()).first()
        
        if current_title and current_title.TitleID >= 4:
            duration *= SENIORITY_FACTOR

    # Add some randomness to the duration
    duration = int(duration * random.uniform(0.8, 1.2))
    duration = max(90, min(540, duration))  # Ensure duration is between 3 months and 1.5 years

    # Set the project dates
    project.PlannedStartDate = date(current_year, random.randint(1, 12), random.randint(1, 28))
    project.PlannedEndDate = project.PlannedStartDate + timedelta(days=duration)
    project.ActualStartDate = project.PlannedStartDate

    return duration

def determine_project_completion(project, current_date):
    # Projects have a higher chance of completion if they're past their planned end date
    days_overdue = (current_date - project.PlannedEndDate).days
    base_completion_chance = 0.5  # 50% chance for projects on or before the planned end date
    
    if days_overdue > 0:
        # Increase chance of completion for overdue projects
        completion_chance = min(base_completion_chance + (days_overdue / 365), 0.95)
    else:
        total_planned_duration = (project.PlannedEndDate - project.PlannedStartDate).days
        if total_planned_duration > 0:
            elapsed_duration = (current_date - project.PlannedStartDate).days
            completion_chance = base_completion_chance * (elapsed_duration / total_planned_duration)
        else:
            completion_chance = 0  # Project hasn't started yet

    # Adjust based on progress
    if project.Progress > 0:
        completion_chance *= (project.Progress / 100)
    else:
        completion_chance = 0  # No progress made yet

    return random.random() < completion_chance

def set_project_financials(project, total_cost):

    BASE_PROFIT_MARGIN = 0.2  # 20% profit margin
    if project.Type == 'Fixed':
        project.Price = total_cost * (1 + BASE_PROFIT_MARGIN)
        project_duration_days = (project.PlannedEndDate - project.PlannedStartDate).days
        average_team_size = 4  # Assuming an average team size of 4
        project.PlannedHours = project_duration_days * 8 * average_team_size  # 8 hours per day

    elif project.Type == 'Time and Material':
        # For Time and Material projects, set PlannedHours based on the total cost
        AVERAGE_BILLING_RATE = 150  # $150 per hour
        project.PlannedHours = int(total_cost / AVERAGE_BILLING_RATE)
        
        project.Price = total_cost * (1 + BASE_PROFIT_MARGIN)

    if project.Price:
        project.Price = round(project.Price, -3)
    project.PlannedHours = round(project.PlannedHours, -1)

    return project

def adjust_for_profit_loss(project, growth_rate):
    # Base adjustment range
    BASE_ADJUSTMENT = 0.2

    adjustment_range = BASE_ADJUSTMENT + (growth_rate * 0.5)
    adjustment_factor = random.uniform(1 - adjustment_range, 1 + adjustment_range)

    if project.Type == 'Fixed':
        project.Price = project.Price * adjustment_factor
    elif project.Type == 'Time and Material':
        project.PlannedHours = int(project.PlannedHours * adjustment_factor)

    # Simulate some budget overrun
    if random.random() < 0.1:
        overrun_factor = random.uniform(1.1, 1.5)
        if project.Type == 'Fixed':
            project.ActualCost = project.Price * overrun_factor
        else:
            project.PlannedHours = int(project.PlannedHours * overrun_factor)

    # Round values for realism
    if project.Price:
        project.Price = round(project.Price, -3)
    project.PlannedHours = round(project.PlannedHours, -1)

    return project

def generate_project_billing_rates(session, project, assigned_consultants):
    billing_rates = []

    if project.Type == 'Time and Material':
        # Base billing rates for each title
        base_rates = {
            1: 100, 2: 150, 3: 200, 
            4: 250, 5: 300, 6: 400
        }

        assigned_titles = set()

        for consultant in assigned_consultants:
            current_title = session.query(ConsultantTitleHistory).\
                filter(ConsultantTitleHistory.ConsultantID == consultant.ConsultantID).\
                order_by(ConsultantTitleHistory.StartDate.desc()).first()
            
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
    total_project_hours = max(project.PlannedHours, num_deliverables * 10)
    remaining_hours = total_project_hours
    project_duration = max(1, (project.PlannedEndDate - project.PlannedStartDate).days)

    for i in range(num_deliverables):
        is_last_deliverable = (i == num_deliverables - 1)
        
        if is_last_deliverable:
            planned_hours = remaining_hours
        else:
            min_hours = 10
            max_hours = max(min_hours, remaining_hours - (num_deliverables - i - 1) * min_hours)
            planned_hours = random.randint(min_hours, max_hours) if max_hours > min_hours else min_hours
            remaining_hours -= planned_hours

        start_date = project.PlannedStartDate if i == 0 else deliverables[-1].DueDate + timedelta(days=1)
        due_date = start_date + timedelta(days=max(1, int((planned_hours / total_project_hours) * project_duration)))
        
        if is_last_deliverable:
            due_date = project.PlannedEndDate

        deliverable = Deliverable(
            ProjectID=project.ProjectID,
            Name=f"Deliverable {i+1}",
            PlannedStartDate=start_date,
            ActualStartDate=start_date,
            Status='Not Started',
            DueDate=due_date,
            PlannedHours=planned_hours,
            ActualHours=0,
            Progress=0
        )
        deliverables.append(deliverable)

    return deliverables

def generate_consultant_deliverables(deliverables, assigned_consultants):
    consultant_deliverables = []

    for deliverable in deliverables:
        # Determine how many consultants will work on this deliverable
        num_consultants = min(len(assigned_consultants), random.randint(1, 3))
        selected_consultants = random.sample(assigned_consultants, num_consultants)
        
        # Distribute hours among consultants
        total_hours = deliverable.PlannedHours
        consultant_hours = [random.randint(1, max(1, total_hours // num_consultants)) for _ in range(num_consultants)]
        
        # Adjust to ensure total hours match
        total_generated = sum(consultant_hours)
        if total_generated < total_hours:
            consultant_hours[-1] += total_hours - total_generated
        elif total_generated > total_hours:
            consultant_hours[-1] = max(1, consultant_hours[-1] - (total_generated - total_hours))
        
        for consultant, hours in zip(selected_consultants, consultant_hours):
            # Ensure the date range is always positive
            date_range = max(0, (deliverable.DueDate - deliverable.PlannedStartDate).days)
            
            # Generate random work dates
            work_dates = [
                deliverable.PlannedStartDate + timedelta(days=random.randint(0, date_range))
                for _ in range(min(hours, 10))
            ]
            work_dates.sort()
            
            # Distribute hours across work dates
            for work_date in work_dates:
                hours_for_date = min(8, hours)  # Max 8 hours per day
                consultant_deliverable = ConsultantDeliverable(
                    ConsultantID=consultant.ConsultantID,
                    DeliverableID=deliverable.DeliverableID,
                    Date=work_date,
                    Hours=hours_for_date
                )
                consultant_deliverables.append(consultant_deliverable)
                hours -= hours_for_date
                
                if hours <= 0:
                    break

    return consultant_deliverables

def generate_project_expenses(project, deliverables):
    expenses = []
    
    expense_categories = {
        'Travel': 0.8, 'Equipment': 0.6, 'Software Licenses': 0.7,
        'Training': 0.5, 'Miscellaneous': 0.3
    }

    num_expenses = random.randint(5, 15)
    
    for _ in range(num_expenses):
        category = random.choice(list(expense_categories.keys()))
        is_billable = random.random() < expense_categories[category]
        
        deliverable = random.choice(deliverables)
        
        if category in ['Travel', 'Equipment']:
            amount = random.uniform(500, 5000)
        elif category in ['Software Licenses', 'Training']:
            amount = random.uniform(100, 2000)
        else:  # Miscellaneous
            amount = random.uniform(50, 1000)
        amount = round(amount, 2)
        
        expense_date = project.PlannedStartDate + timedelta(days=random.randint(0, (project.PlannedEndDate - project.PlannedStartDate).days))
        
        expense = ProjectExpense(
            ProjectID=project.ProjectID,
            DeliverableID=deliverable.DeliverableID,
            Date=expense_date,
            Amount=amount,
            Description=f"{category} expense for {deliverable.Name}",
            Category=category,
            IsBillable=is_billable
        )
        
        expenses.append(expense)
    
    return expenses

def generate_projects(start_year, end_year):
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        for current_year in range(start_year, end_year + 1):
            growth_rate = get_growth_rate(current_year)
            available_consultants = find_available_consultants(session, current_year)
            num_projects = determine_project_count(available_consultants, growth_rate)

            projects = []
            all_deliverables = []
            all_consultant_deliverables = []
            all_project_expenses = []
            all_billing_rates = []

            for _ in range(num_projects):
                project = generate_basic_project(session, current_year)
                session.add(project)
                session.flush()  # This will populate the ProjectID

                assigned_consultants = assign_consultants_to_project(project, available_consultants, session)
                
                set_project_dates(project, assigned_consultants, session, current_year)
                
                total_cost = calculate_project_costs(project, assigned_consultants, session)
                project = set_project_financials(project, total_cost)
                project = adjust_for_profit_loss(project, growth_rate)

                deliverables = generate_deliverables(project)
                session.add_all(deliverables)
                session.flush()  # This will populate the DeliverableID for each deliverable

                consultant_deliverables = generate_consultant_deliverables(deliverables, assigned_consultants)
                all_consultant_deliverables.extend(consultant_deliverables)

                project_expenses = generate_project_expenses(project, deliverables)
                all_project_expenses.extend(project_expenses)

                project.TotalExpenses = sum(expense.Amount for expense in project_expenses)

                if project.Type == 'Time and Material':
                    billing_rates = generate_project_billing_rates(session, project, assigned_consultants)
                    all_billing_rates.extend(billing_rates)

                # Calculate initial progress
                current_date = date(current_year, 12, 31)
                if current_date >= project.PlannedStartDate:
                    project_duration = (project.PlannedEndDate - project.PlannedStartDate).days
                    elapsed_duration = (current_date - project.PlannedStartDate).days
                    project.Progress = min(int((elapsed_duration / project_duration) * 100), 99)
                else:
                    project.Progress = 0

                # Determine if the project should be completed
                if determine_project_completion(project, current_date):
                    project.Status = 'Completed'
                    project.ActualEndDate = min(current_date, project.PlannedEndDate)
                    project.Progress = 100
                else:
                    project.Status = 'In Progress' if current_date >= project.PlannedStartDate else 'Not Started'
                    project.ActualEndDate = None
                    if project.Status == 'In Progress':
                        # Add some randomness to progress for ongoing projects
                        project.Progress = min(99, max(0, int(project.Progress * random.uniform(0.8, 1.2))))

                projects.append(project)

                # Update consultant availability
                for consultant in assigned_consultants:
                    consultant.project_count = getattr(consultant, 'project_count', 0) + 1
                
                # Filter out consultants who are already on 2 projects
                available_consultants = [c for c in available_consultants if getattr(c, 'project_count', 0) < 2]

            # Bulk insert all generated data
            session.add_all(projects)
            session.add_all(all_deliverables)
            session.add_all(all_consultant_deliverables)
            session.add_all(all_project_expenses)
            session.add_all(all_billing_rates)

            print(f"Year {current_year}: Generated {num_projects} projects")

        session.commit()
    except Exception as e:
        print(f"An error occurred: {e}")
        session.rollback()
    finally:
        session.close()


def main(start_year, end_year):
    print("Generating Project Data...")
    generate_projects(start_year, end_year)
    print("Complete")
