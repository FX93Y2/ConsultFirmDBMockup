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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_projects(start_year, end_year):
    Session = sessionmaker(bind=engine)
    session = Session()
    simulation_start_date = date(start_year, 1, 1)
    simulation_end_date = date(end_year, 12, 31)
    print("Generating Project Data...")

    try:
        project_meta = defaultdict(lambda: {
            'team': [],
            'deliverables': defaultdict(lambda: {
                'remaining_hours': 0,
                'consultant_deliverables': []
            }),
            'target_hours': 0
        })

        for current_year in range(start_year, end_year + 1):
            for current_month in range(1, 13):
                current_date = date(current_year, current_month, 1)
                if current_date > simulation_end_date:
                    break

                logging.info(f"Processing {current_date.strftime('%B %Y')}...")

                available_consultants = get_available_consultants(session, current_date)
                active_units = session.query(BusinessUnit).all()

                project_meta = create_new_projects_if_needed(session, current_date, available_consultants, active_units, project_meta, simulation_start_date)
                update_existing_projects(session, current_date, available_consultants, project_meta)
                generate_monthly_consultant_deliverables(session, current_date, project_meta)
                update_project_statuses(session, current_date, project_meta)

                log_consultant_projects(session, current_date)  # Add this line

                session.commit()

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


def create_new_projects_if_needed(session, current_date, available_consultants, active_units, project_meta, simulation_start_date):

    higher_level_consultants = sorted(
        [c for c in available_consultants if c.title_id >= project_settings.HIGHER_LEVEL_TITLE_THRESHOLD],
        key=lambda c: (c.active_project_count, -c.title_id)
    )

    projects_created = 0
    for consultant in higher_level_consultants:
        if consultant.active_project_count >= project_settings.MAX_PROJECTS_PER_CONSULTANT:
            continue

        if random.random() < 0.5: # 70% chance of creating a new project
            project, new_project_meta, target_hours = create_new_project(session, current_date, available_consultants, active_units, simulation_start_date, project_manager=consultant)
            if project:
                project_meta[project.ProjectID] = new_project_meta
                project_meta[project.ProjectID]['target_hours'] = target_hours
                projects_created += 1

                logging.info(f"Created new project: ProjectID {project.ProjectID}, "
                             f"Start Date: {project.PlannedStartDate}, "
                             f"Team Size: {len(new_project_meta['team'])}, "
                             f"Project Manager: {consultant.consultant.ConsultantID}")

                # Update consultant project counts
                for consultant_id in new_project_meta['team']:
                    consultant_info = next(c for c in available_consultants if c.consultant.ConsultantID == consultant_id)
                    consultant_info.active_project_count += 1

                # Re-sort available_consultants
                available_consultants = sorted(available_consultants, key=lambda c: (c.active_project_count, -c.title_id))

    logging.info(f"Date: {current_date}, New Projects Created: {projects_created}")
    return project_meta

def create_new_project(session, current_date, available_consultants, active_units, simulation_start_date, project_manager):
    assigned_consultants = assign_consultants_to_project(available_consultants, project_manager)

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
    session.flush()

    team_size = set_project_dates(project, current_date, assigned_consultants, session, simulation_start_date)
    project.PlannedHours = calculate_planned_hours(project, team_size)
    target_hours = calculate_target_hours(project.PlannedHours)
    project.ActualHours = 0
    
    deliverables = generate_deliverables(project, target_hours)
    session.add_all(deliverables)
    session.flush()

    calculate_project_financials(session, project, assigned_consultants, current_date, deliverables)
    
    assign_project_team(session, project, assigned_consultants)
    session.flush()

    project_meta = initialize_project_meta(project, target_hours)

    return project, project_meta, target_hours

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
        if project.ProjectID in project_meta:
            update_project_team(session, project, available_consultants, project_meta[project.ProjectID]['team'], current_date)
        else:
            logging.warning(f"Project {project.ProjectID} not found in project_meta")


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
    consultant_daily_hours = defaultdict(lambda: defaultdict(float))
    
    for project_id, meta in project_meta.items():
        project = session.query(Project).get(project_id)
        if project.Status not in ['Not Started', 'In Progress']:
            continue

        if project.Status == 'Not Started' and project.PlannedStartDate <= current_date:
            project.Status = 'In Progress'
            project.ActualStartDate = current_date

        project_actual_hours = 0

        for deliverable_id, deliverable_meta in meta['deliverables'].items():
            deliverable = session.query(Deliverable).get(deliverable_id)
            if deliverable.Status == 'Completed':
                continue

            remaining_hours = deliverable_meta['target_hours'] - deliverable.ActualHours

            for day in working_days:
                if remaining_hours <= 0:
                    break

                if day < project.ActualStartDate or day > project.PlannedEndDate:
                    continue

                for consultant_id in meta['team']:
                    consultant_hours_today = consultant_daily_hours[consultant_id][day]
                    available_hours = min(project_settings.MAX_DAILY_HOURS - consultant_hours_today, remaining_hours)

                    if available_hours <= 0:
                        continue

                    hours = round(random.uniform(project_settings.MIN_DAILY_HOURS, available_hours), 1)
                    consultant_deliverable = ConsultantDeliverable(
                        ConsultantID=consultant_id,
                        DeliverableID=deliverable_id,
                        Date=day,
                        Hours=hours
                    )
                    session.add(consultant_deliverable)
                    deliverable_meta['consultant_deliverables'].append(consultant_deliverable)
                    remaining_hours -= hours
                    deliverable.ActualHours += hours
                    project_actual_hours += hours
                    consultant_daily_hours[consultant_id][day] += hours

            deliverable.Progress = min(100, int((deliverable.ActualHours / deliverable_meta['target_hours']) * 100))

        project.ActualHours += project_actual_hours
        project.Progress = min(100, int((project.ActualHours / meta['target_hours']) * 100))


def update_project_statuses(session, current_date, project_meta):
    for project_id, meta in project_meta.items():
        project = session.query(Project).get(project_id)
        if project.Status == 'Completed':
            continue

        if project.Status == 'Not Started' and project.PlannedStartDate <= current_date:
            project.Status = 'In Progress'
            project.ActualStartDate = current_date

        if project.Status == 'In Progress':
            all_deliverables_completed = True
            total_target_hours = meta['target_hours']
            weighted_progress = 0

            for deliverable_id, deliverable_meta in meta['deliverables'].items():
                deliverable = session.query(Deliverable).get(deliverable_id)

                if deliverable.ActualHours >= deliverable_meta['target_hours']:
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

                deliverable_progress = (deliverable.ActualHours / deliverable_meta['target_hours']) * 100
                deliverable_weight = deliverable_meta['target_hours'] / total_target_hours
                weighted_progress += deliverable_progress * deliverable_weight
                deliverable.Progress = min(100, int(deliverable_progress))

            project.Progress = min(100, int(weighted_progress))

            if project.ActualHours == 0 and current_date > project.ActualStartDate + timedelta(days=60):
                # If no work has been done for a month after the start date, mark as Cancelled
                project.Status = 'Cancelled'
                logging.warning(f"Project {project.ProjectID} cancelled due to inactivity")
            elif all_deliverables_completed or current_date > project.PlannedEndDate:
                project.Status = 'Completed'
                project.ActualEndDate = current_date
                session.query(ProjectTeam).filter(
                    ProjectTeam.ProjectID == project.ProjectID,
                    ProjectTeam.EndDate.is_(None)
                ).update({ProjectTeam.EndDate: current_date})

        logging.info(f"Updated status for ProjectID {project.ProjectID}: Status {project.Status}, Progress {project.Progress}%, ActualHours {project.ActualHours}")

    session.commit()


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


