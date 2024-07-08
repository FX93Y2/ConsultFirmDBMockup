import random
import logging
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import sessionmaker
from sqlalchemy import func
from collections import defaultdict
from decimal import Decimal
from ...db_model import *
from ..utils.test_project_utils import *
from config import project_settings

logging.basicConfig(level=logging.INFO)

def generate_projects(start_year, end_year):
    Session = sessionmaker(bind=engine)
    session = Session()
    simulation_end_date = date(end_year, 12, 31)
    print("Generating Project Data...")

    try:
        # Initialize project meta data
        project_meta = defaultdict(lambda: {
            'team': [],
            'deliverables': defaultdict(lambda: {
                'remaining_hours': 0,
                'consultant_deliverables': []
            })
        })

        for current_year in range(start_year, end_year + 1):
            for current_month in range(1, 13):
                current_date = date(current_year, current_month, 1)
                if current_date > simulation_end_date:
                    break

                print(f"Processing {current_date.strftime('%B %Y')}...")

                # Get available consultants for the month
                available_consultants = get_available_consultants(session, current_date)
                active_units = session.query(BusinessUnit).all()

                # Create new projects if needed
                if current_date.month in [1, 7]:  # Assuming new projects start twice a year
                    growth_rate = 0.1
                    num_new_projects = determine_project_count(available_consultants, growth_rate)
                    
                    for _ in range(num_new_projects):
                        project = create_new_project(session, current_date, available_consultants, active_units)
                        if project:
                            project_meta[project.ProjectID] = initialize_project_meta(project, session)

                # Update existing projects
                update_existing_projects(session, current_date, available_consultants, project_meta)

                # Generate consultant deliverables for the month
                generate_monthly_consultant_deliverables(session, current_date, project_meta)

                # Update project and deliverable statuses
                update_project_statuses(session, current_date, project_meta)

                session.commit()

        # Generate final project expenses
        generate_project_expenses(session, project_meta, simulation_end_date)

        session.commit()
        print("Project generation completed successfully.")

    except Exception as e:
        print(f"An error occurred while processing projects: {str(e)}")
        import traceback
        print(traceback.format_exc())
        session.rollback()
    finally:
        session.close()

def create_new_project(session, current_date, available_consultants, active_units):
    assigned_consultants = assign_consultants_to_project(session, available_consultants, current_date)
    if not assigned_consultants:
        return None

    assigned_unit_id = assign_project_to_business_unit(session, assigned_consultants, active_units, current_date.year)
    
    project = Project(
        ClientID=random.choice(session.query(Client.ClientID).all())[0],
        UnitID=assigned_unit_id,
        Name=f"Project_{current_date.year}_{random.randint(1000, 9999)}",
        Type=random.choices(project_settings.PROJECT_TYPES, weights=project_settings.PROJECT_TYPE_WEIGHTS)[0],
        Status='Not Started',
        Progress=0,
        EstimatedBudget=None,
        Price=None
    )
    
    session.add(project)
    session.flush()  # This will populate the ProjectID

    set_project_dates(project, current_date, assigned_consultants, session)
    project.PlannedHours = math.floor((project.PlannedEndDate - project.PlannedStartDate).days / 30 * project_settings.WORKING_HOURS_PER_MONTH)
    project.ActualHours = 0
    
    deliverables = generate_deliverables(project)
    session.add_all(deliverables)
    session.flush()  # This will populate DeliverableID

    calculate_project_financials(session, project, assigned_consultants, current_date, deliverables)
    
    # Assign project team
    assign_project_team(session, project, assigned_consultants)

    return project

def initialize_project_meta(project, session):
    meta = {
        'team': [],
        'deliverables': defaultdict(lambda: {
            'remaining_hours': 0,
            'consultant_deliverables': []
        })
    }

    # Initialize team
    team_members = session.query(ProjectTeam).filter(ProjectTeam.ProjectID == project.ProjectID).all()
    meta['team'] = [member.ConsultantID for member in team_members]

    # Initialize deliverables
    deliverables = session.query(Deliverable).filter(Deliverable.ProjectID == project.ProjectID).all()
    for deliverable in deliverables:
        meta['deliverables'][deliverable.DeliverableID]['remaining_hours'] = deliverable.PlannedHours

    return meta

def update_existing_projects(session, current_date, available_consultants, project_meta):
    active_projects = session.query(Project).filter(
        Project.Status.in_(['Not Started', 'In Progress']),
        Project.PlannedStartDate <= current_date,
        Project.PlannedEndDate >= current_date
    ).all()

    for project in active_projects:
        if project.Status == 'Not Started' and project.PlannedStartDate <= current_date:
            project.Status = 'In Progress'
            project.ActualStartDate = current_date

        # Update project team if needed
        update_project_team(session, project, available_consultants, project_meta[project.ProjectID]['team'], current_date)

def generate_monthly_consultant_deliverables(session, current_date, project_meta):
    working_days = get_working_days(current_date.year, current_date.month)
    
    # Keep track of daily hours for each consultant
    consultant_daily_hours = defaultdict(lambda: defaultdict(float))
    
    for project_id, meta in project_meta.items():
        project = session.query(Project).get(project_id)
        if project.Status != 'In Progress':
            continue

        for deliverable_id, deliverable_meta in meta['deliverables'].items():
            if deliverable_meta['remaining_hours'] <= 0:
                continue

            deliverable = session.query(Deliverable).get(deliverable_id)
            if deliverable.Status == 'Completed':
                continue

            for day in working_days:
                if deliverable_meta['remaining_hours'] <= 0:
                    break

                for consultant_id in meta['team']:
                    if deliverable_meta['remaining_hours'] <= 0:
                        break

                    # Check how many hours the consultant has already worked today
                    consultant_hours_today = consultant_daily_hours[consultant_id][day]
                    
                    # Calculate how many more hours the consultant can work today
                    available_hours = min(project_settings.MAX_DAILY_HOURS - consultant_hours_today, 
                                          deliverable_meta['remaining_hours'])
                    
                    if available_hours <= 0:
                        continue  # Consultant has reached their daily limit

                    # Assign random hours within the available range
                    hours = round(random.uniform(project_settings.MIN_DAILY_HOURS, available_hours), 1)
                    
                    consultant_deliverable = ConsultantDeliverable(
                        ConsultantID=consultant_id,
                        DeliverableID=deliverable_id,
                        Date=day,
                        Hours=hours
                    )
                    session.add(consultant_deliverable)
                    deliverable_meta['consultant_deliverables'].append(consultant_deliverable)
                    deliverable_meta['remaining_hours'] -= hours
                    deliverable.ActualHours += hours
                    project.ActualHours += hours
                    
                    # Update the consultant's daily hours
                    consultant_daily_hours[consultant_id][day] += hours

            logging.info(f"Generated {len(deliverable_meta['consultant_deliverables'])} consultant deliverables for Project {project_id}, Deliverable {deliverable_id}")

    session.commit()

def update_project_statuses(session, current_date, project_meta):
    for project_id, meta in project_meta.items():
        project = session.query(Project).get(project_id)
        if project.Status == 'Completed':
            continue

        all_deliverables_completed = True
        for deliverable_id, deliverable_meta in meta['deliverables'].items():
            deliverable = session.query(Deliverable).get(deliverable_id)
            
            if deliverable_meta['remaining_hours'] <= 0:
                deliverable.Status = 'Completed'
                deliverable.SubmissionDate = current_date
                if project.Type == 'Fixed':
                    deliverable.InvoicedDate = current_date + timedelta(days=random.randint(1, 7))
            elif deliverable.ActualHours > 0:
                deliverable.Status = 'In Progress'
                all_deliverables_completed = False
            else:
                deliverable.Status = 'Not Started'
                all_deliverables_completed = False

            deliverable.Progress = min(100, int((deliverable.ActualHours / deliverable.PlannedHours) * 100))

        calculate_project_progress(project, session.query(Deliverable).filter(Deliverable.ProjectID == project.ProjectID).all())

        if all_deliverables_completed:
            project.Status = 'Completed'
            project.ActualEndDate = current_date
        elif project.Progress > 0:
            project.Status = 'In Progress'

def generate_project_expenses(session, project_meta, simulation_end_date):
    for project_id, meta in project_meta.items():
        project = session.query(Project).get(project_id)
        if project.Status not in ['In Progress', 'Completed']:
            continue

        total_consultant_cost = sum(cd.Hours * calculate_hourly_cost(session, cd.ConsultantID, cd.Date.year)
                                    for deliverable_meta in meta['deliverables'].values()
                                    for cd in deliverable_meta['consultant_deliverables'])

        expenses = []
        for deliverable_id, deliverable_meta in meta['deliverables'].items():
            deliverable = session.query(Deliverable).get(deliverable_id)
            
            expense_start_date = deliverable.ActualStartDate or deliverable.PlannedStartDate
            expense_end_date = min(deliverable.SubmissionDate or simulation_end_date,
                                   project.ActualEndDate or simulation_end_date,
                                   simulation_end_date)

            if expense_start_date >= expense_end_date:
                continue

            for category, percentage in project_settings.EXPENSE_CATEGORIES.items():
                is_billable = random.choice([True, False])
                amount = Decimal(total_consultant_cost) * Decimal(percentage) * Decimal(random.uniform(0.8, 1.2))
                amount = round(amount, -2)  # Round to nearest hundred

                if amount > 0:
                    consultant_deliverable_dates = [cd.Date for cd in deliverable_meta['consultant_deliverables']
                                                    if expense_start_date <= cd.Date <= expense_end_date]
                    
                    if consultant_deliverable_dates:
                        expense_date = random.choice(consultant_deliverable_dates)
                    else:
                        # Fallback: use the middle date between start and end
                        expense_date = expense_start_date + (expense_end_date - expense_start_date) / 2
                    
                    expense = ProjectExpense(
                        ProjectID=project.ProjectID,
                        DeliverableID=deliverable.DeliverableID,
                        Date=expense_date,
                        Amount=float(amount),
                        Description=f"{category} expense for {deliverable.Name}",
                        Category=category,
                        IsBillable=is_billable
                    )
                    expenses.append(expense)

        session.add_all(expenses)

    session.commit()

def assign_project_team(session, project, assigned_consultants):
    for consultant in assigned_consultants:
        current_title = get_current_title(session, consultant.ConsultantID, project.PlannedStartDate)
        role = 'Project Manager' if current_title.TitleID >= 4 else 'Team Member'
        team_member = ProjectTeam(
            ProjectID=project.ProjectID,
            ConsultantID=consultant.ConsultantID,
            Role=role,
            StartDate=project.PlannedStartDate
        )
        session.add(team_member)

def update_project_team(session, project, available_consultants, current_team, current_date):
    target_team_size = random.randint(5, 10)
    
    if len(current_team) < target_team_size:
        potential_new_members = [c for c in available_consultants if c.ConsultantID not in current_team and get_current_title(session, c.ConsultantID, current_date).TitleID <= 3]
        new_members_count = min(target_team_size - len(current_team), len(potential_new_members))
        
        for new_member in random.sample(potential_new_members, new_members_count):
            team_member = ProjectTeam(
                ProjectID=project.ProjectID,
                ConsultantID=new_member.ConsultantID,
                Role='Team Member',
                StartDate=current_date
            )
            session.add(team_member)
            current_team.append(new_member.ConsultantID)