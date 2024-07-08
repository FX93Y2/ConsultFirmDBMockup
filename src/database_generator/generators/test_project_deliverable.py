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
    simulation_start_date = date(start_year, 1, 1)
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

                # Clean up old assignments
                cleanup_old_assignments(session, current_date)

                # Get available consultants for the month
                available_consultants = get_available_consultants(session, current_date)
                active_units = session.query(BusinessUnit).all()

                # Create new projects if needed
                create_new_projects_if_needed(session, current_date, available_consultants, active_units, project_meta, simulation_start_date)

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

def cleanup_old_assignments(session, current_date):
    three_months_ago = current_date - timedelta(days=90)
    old_assignments = session.query(ProjectTeam).filter(
        ProjectTeam.EndDate.is_(None),
        ProjectTeam.StartDate < three_months_ago
    ).join(Project).filter(
        Project.Status.in_(['Completed', 'Cancelled'])
    ).all()

    for assignment in old_assignments:
        assignment.EndDate = min(current_date, assignment.Project.ActualEndDate or current_date)
        logging.info(f"Cleaned up old assignment: Consultant {assignment.ConsultantID} on Project {assignment.ProjectID}, ended on {assignment.EndDate}")

    session.commit()

def create_new_projects_if_needed(session, current_date, available_consultants, active_units, project_meta, simulation_start_date):
    logging.info(f"Starting project creation process on {current_date}")
    
    # Sort available consultants by title, highest first
    sorted_consultants = sorted(
        available_consultants, 
        key=lambda c: get_current_title(session, c.ConsultantID, current_date).TitleID,
        reverse=True
    )
    
    for consultant in sorted_consultants:
        current_title = get_current_title(session, consultant.ConsultantID, current_date)
        if current_title.TitleID >= 4:  # Only consider title 4 and above for project managers
            logging.info(f"Considering {consultant.ConsultantID} (Title {current_title.TitleID}) for project manager")
            if random.random() < 0.7:  # 70% chance to start a new project
                project = create_new_project(session, current_date, available_consultants, active_units, consultant, simulation_start_date)
                if project:
                    project_meta[project.ProjectID] = initialize_project_meta(project, session)
                    logging.info(f"Created new project with {consultant.ConsultantID} (Title {current_title.TitleID}) as project manager")
                    # Remove the assigned consultants from the available pool
                    available_consultants = [c for c in available_consultants if c.ConsultantID not in project_meta[project.ProjectID]['team']]
            else:
                logging.info(f"Didn't create project for {consultant.ConsultantID} (Title {current_title.TitleID}) due to random chance")
        else:
            logging.info(f"Stopped considering new projects at {consultant.ConsultantID} (Title {current_title.TitleID})")
            break
    
    logging.info(f"Finished project creation process on {current_date}")

def create_new_project(session, current_date, available_consultants, active_units, project_manager, simulation_start_date):
    assigned_consultants = assign_consultants_to_project(session, available_consultants, current_date, project_manager)
    if len(assigned_consultants) < 2:  # Ensure we have at least one manager and one team member
        logging.warning(f"Not enough consultants assigned to new project on {current_date}")
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

    team_size = set_project_dates(project, current_date, assigned_consultants, session, simulation_start_date)
    project.PlannedHours = calculate_planned_hours(project, team_size)
    project.ActualHours = float(adjust_hours(project.PlannedHours))
    
    deliverables = generate_deliverables(project)
    session.add_all(deliverables)
    session.flush()  # This will populate DeliverableID

    calculate_project_financials(session, project, assigned_consultants, current_date, deliverables)
    
    # Assign project team
    assign_project_team(session, project, assigned_consultants)

    # Log project creation and initial status
    logging.info(f"Created new project {project.ProjectID} starting on {project.PlannedStartDate}")
    logging.info(f"Initial team for project {project.ProjectID}: {[c.ConsultantID for c in assigned_consultants]}")
    logging.info(f"Project Managers for project {project.ProjectID}: {[c.ConsultantID for c in assigned_consultants if get_current_title(session, c.ConsultantID, current_date).TitleID in [4, 5, 6]]}")

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


def update_project_statuses(session, current_date, project_meta):
    for project_id, meta in project_meta.items():
        project = session.query(Project).get(project_id)
        if project.Status == 'Completed':
            continue

        if project.Status == 'Not Started' and project.ActualStartDate <= current_date:
            project.Status = 'In Progress'
            logging.info(f"Project {project.ProjectID} started on {current_date}")

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
            # Update ProjectTeam EndDates
            session.query(ProjectTeam).filter(
                ProjectTeam.ProjectID == project.ProjectID,
                ProjectTeam.EndDate.is_(None)
            ).update({ProjectTeam.EndDate: current_date})
            logging.info(f"Project {project.ProjectID} completed on {current_date}. All team assignments ended.")
        elif project.Progress > 0:
            project.Status = 'In Progress'

        # Log the project status
        logging.info(f"Project {project.ProjectID} status: {project.Status}, Progress: {project.Progress}%")

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


