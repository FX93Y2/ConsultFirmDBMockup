import random
import logging
import traceback
from scipy.stats import norm
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import sessionmaker
from sqlalchemy import func
from collections import defaultdict
from decimal import Decimal
from models.db_model import *
from ..utils.project_utils import *
from ..utils.project_financial_utils import *
from config import project_settings, consultant_settings
                
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_projects(start_year, end_year, initial_consultants):
    yearly_targets = calculate_yearly_project_targets(start_year, end_year, initial_consultants)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    simulation_start_date = date(start_year, 1, 1)
    simulation_end_date = date(end_year, 12, 31)
    print("Generating Project Data...")

    try:
        for current_year in range(start_year, end_year + 1):
            monthly_targets = distribute_monthly_targets(yearly_targets[current_year])
            
            # Update available consultants at the start of each year
            available_consultants = get_available_consultants(session, date(current_year, 1, 1))
            
            for current_month in range(1, 13):
                month_start = date(current_year, current_month, 1)
                if month_start > simulation_end_date:
                    break

                logging.info(f"Processing {month_start.strftime('%B %Y')}...")

                active_units = session.query(BusinessUnit).all()

                available_consultants = create_new_projects_if_needed(session, month_start, available_consultants, active_units, simulation_start_date, monthly_targets)
                
                # Daily simulation within the month
                current_date = month_start
                while current_date.month == current_month:
                    start_due_projects(session, current_date)
                    if current_date.weekday() < 5:  # Weekday
                        generate_daily_consultant_deliverables(session, current_date, session.query(Project).all())
                    update_project_statuses(session, current_date, available_consultants)
                    current_date += timedelta(days=1)

                # End of month operations
                month_end = current_date - timedelta(days=1)
                update_existing_projects(session, month_end, available_consultants)
                log_consultant_projects(session, month_end)

                session.commit()

            generate_project_expenses_for_year(session, simulation_end_date)
            session.commit()
            print(f"Project generation for year {current_year} completed successfully.")

    except Exception as e:
        print(f"An error occurred while processing projects: {str(e)}")
        import traceback
        print(traceback.format_exc())
        session.rollback()
    finally:
        session.close()


def update_consultant_metadata(consultant, title_id, last_project_date, active_project_count):
    consultant.custom_data['title_id'] = title_id
    consultant.custom_data['last_project_date'] = last_project_date
    consultant.custom_data['active_project_count'] = active_project_count

def update_project_metadata(project, team, deliverables, target_hours):
    project.custom_data['team'] = [c.ConsultantID for c in team]
    project.custom_data['deliverables'] = {
        d.DeliverableID: {
            'target_hours': target_hours / len(deliverables),
            'consultant_deliverables': []
        } for d in deliverables
    }
    project.custom_data['target_hours'] = target_hours

def calculate_yearly_project_targets(start_year, end_year, initial_consultants):
    yearly_targets = {}
    consultant_count = initial_consultants
    
    for year in range(start_year, end_year + 1):
        growth_rate = consultant_settings.CONSULTANT_YEARLY_GROWTHRATE.get(year, 0.05)  # Default growth rate of 5%
        consultant_count *= (1 + growth_rate)
        
        yearly_targets[year] = math.ceil(consultant_count / 2)
    
    return yearly_targets

def distribute_monthly_targets(yearly_target):
    base_monthly_target = yearly_target // 12
    extra_projects = yearly_target % 12
    
    monthly_targets = [base_monthly_target] * 12
    middle_months = project_settings.PROJECT_MONTH_DISTRIBUTION
    for i in range(extra_projects):
        month = random.choice(middle_months)
        monthly_targets[month] += 1
    
    return monthly_targets


def start_due_projects(session, current_date):
    due_projects = session.query(Project).filter(
        Project.Status == 'Not Started',
        Project.ActualStartDate <= current_date
    ).all()

    for project in due_projects:
        project.Status = 'In Progress'
        logging.info(f"Starting project {project.ProjectID} on {current_date}")

        team_member_ids = project.custom_data.get('team', [])
        for consultant_id in team_member_ids:
            existing_assignment = session.query(ProjectTeam).filter(
                ProjectTeam.ProjectID == project.ProjectID,
                ProjectTeam.ConsultantID == consultant_id
            ).first()

            if not existing_assignment:
                team_member = ProjectTeam(
                    ProjectID=project.ProjectID,
                    ConsultantID=consultant_id,
                    Role='Team Member',
                    StartDate=current_date
                )
                session.add(team_member)
                logging.info(f"Assigned consultant {consultant_id} to project {project.ProjectID}")

    session.commit()     


def create_new_projects_if_needed(session, current_date, available_consultants, active_units, simulation_start_date, monthly_targets):
    # Include all consultants, not just those with active projects
    all_consultants = session.query(Consultant).all()
    
    project_manager_consultants = [c for c in all_consultants if c.custom_data.get('title_id', 0) >= 4]
    
    project_manager_consultants.sort(key=lambda c: (c.custom_data.get('active_project_count', 0), -c.custom_data.get('title_id', 0)))
    
    logging.info(f"Available project managers: {len(project_manager_consultants)}")
    logging.info(f"Top 5 PM candidates: {[(c.ConsultantID, c.custom_data.get('title_id', 0), c.custom_data.get('active_project_count', 0)) for c in project_manager_consultants[:5]]}")

    target_for_month = monthly_targets[current_date.month - 1]
    
    # Calculate total capacity for new projects
    total_capacity = sum(max(0, project_settings.MAX_PROJECTS_PER_CONSULTANT.get(c.custom_data.get('title_id', 1), 2) - c.custom_data.get('active_project_count', 0)) for c in project_manager_consultants)
    
    # Adjust target based on capacity, but ensure it's not negative
    adjusted_target = max(0, min(target_for_month, total_capacity))
    
    logging.info(f"Target for month: {target_for_month}, Adjusted target: {adjusted_target}, Total capacity: {total_capacity}")

    if adjusted_target > 0:
        std_dev = max(0.1, adjusted_target * 0.2)
        projects_to_create = max(0, round(norm.rvs(loc=adjusted_target, scale=std_dev)))
    else:
        projects_to_create = 0

    projects_this_month = len([p for p in session.query(Project).all() if p.custom_data.get('start_date', date.min).month == current_date.month and p.custom_data.get('start_date', date.min).year == current_date.year])
    projects_to_create = max(0, projects_to_create - projects_this_month)

    logging.info(f"Target projects to create: {projects_to_create}")

    projects_created = 0
    for consultant in project_manager_consultants:
        if projects_created >= projects_to_create:
            break
        
        max_projects = project_settings.MAX_PROJECTS_PER_CONSULTANT.get(consultant.custom_data.get('title_id', 1), 2)
        if consultant.custom_data.get('active_project_count', 0) >= max_projects:
            continue

        logging.info(f"Attempting to create project with PM: {consultant.ConsultantID} (Title: {consultant.custom_data.get('title_id', 0)}, Active Projects: {consultant.custom_data.get('active_project_count', 0)})")
        project = create_new_project(session, current_date, all_consultants, active_units, simulation_start_date, project_manager=consultant)
        if project:
            projects_created += 1

            # Update consultant project counts
            for consultant_id in project.custom_data['team']:
                consultant = session.query(Consultant).get(consultant_id)
                consultant.custom_data['active_project_count'] = consultant.custom_data.get('active_project_count', 0) + 1
                consultant.custom_data['last_project_date'] = current_date

            # Update available_consultants list
            available_consultants = [c for c in all_consultants if c.custom_data.get('active_project_count', 0) < project_settings.MAX_PROJECTS_PER_CONSULTANT.get(c.custom_data.get('title_id', 1), 2)]
            available_consultants.sort(key=lambda c: (c.custom_data.get('active_project_count', 0), -c.custom_data.get('title_id', 0)))
            logging.info(f"Successfully created project: ProjectID {project.ProjectID}")
        else:
            logging.warning(f"Failed to create new project with Project Manager: {consultant.ConsultantID}")

    logging.info(f"Date: {current_date}, New Projects Created: {projects_created}, Target: {adjusted_target}, Available Project Managers: {len(project_manager_consultants)}")
    return available_consultants


def create_new_project(session, current_date, available_consultants, active_units, simulation_start_date, project_manager):
    logging.info(f"Attempting to create new project with PM: {project_manager.ConsultantID} (Title: {project_manager.custom_data.get('title_id', 'Unknown')})")

    try:
        eligible_consultants = [c for c in available_consultants if c.custom_data.get('title_id', 0) <= project_manager.custom_data.get('title_id', 0)]
        days_before = random.randint(0, 15)
        created_at = current_date - timedelta(days=days_before)
        created_at = max(created_at, simulation_start_date)# Ensure created_at is not before the simulation start date
        project = Project(
            ClientID=random.choice(session.query(Client.ClientID).all())[0],
            UnitID=assign_project_to_business_unit(session, eligible_consultants, active_units, current_date.year),
            Name=f"Project{current_date.year}{random.randint(1000, 9999)}",
            Type=random.choices(project_settings.PROJECT_TYPES, weights=project_settings.PROJECT_TYPE_WEIGHTS)[0],
            Status='Not Started',
            Progress=0,
            EstimatedBudget=None,
            Price=None,
            CreatedAt=created_at
        )

        session.add(project)
        session.flush()
        logging.info(f"Created project: ProjectID {project.ProjectID}")

        target_team_size = set_project_dates(project, current_date, project_manager, session, simulation_start_date)
        project.PlannedHours = calculate_planned_hours(project, target_team_size)
        target_hours = calculate_target_hours(project.PlannedHours)
        project.ActualHours = 0

        # Assign initial team members
        assigned_consultants, remaining_slots = assign_consultants_to_project(eligible_consultants, project_manager, target_team_size)

        deliverables = generate_deliverables(project, target_hours)
        session.add_all(deliverables)
        session.flush()

        # Initialize project custom_data
        project.custom_data = {
            'team': [c.ConsultantID for c in assigned_consultants],
            'deliverables': {},
            'target_hours': target_hours,
            'target_team_size': target_team_size,
            'remaining_slots': remaining_slots
        }

        # Set up billing rates for all title levels
        if project.Type == 'Time and Material':
            for title_id in range(1, 7):  # Assuming title IDs range from 1 to 6
                avg_experience = calculate_average_experience(session, title_id, current_date)
                rate = calculate_billing_rate(title_id, project.Type, avg_experience)
                billing_rate = ProjectBillingRate(
                    ProjectID=project.ProjectID,
                    TitleID=title_id,
                    Rate=float(rate)
                )
                session.add(billing_rate)
            session.flush()

        calculate_project_financials(session, project, assigned_consultants, current_date, deliverables)

        assign_project_team(session, project, assigned_consultants)
        session.flush()

        update_project_metadata(project, assigned_consultants, deliverables, target_hours)

        logging.info(f"Project {project.ProjectID} created with {len(assigned_consultants)} consultants. Remaining slots: {remaining_slots}")

        return project
    except Exception as e:
        logging.error(f"Error creating new project: {str(e)}")
        import traceback
        print(traceback.format_exc())
        session.rollback()
        return None


def update_existing_projects(session, current_date, available_consultants):
    active_projects = session.query(Project).filter(
        Project.Status.in_(['Not Started', 'In Progress']),
        Project.PlannedStartDate <= current_date,
        Project.PlannedEndDate >= current_date
    ).all()

    for project in active_projects:
        try:
            if project.Status == 'Not Started' and project.PlannedStartDate <= current_date:
                project.Status = 'In Progress'
                project.ActualStartDate = current_date

            # Update project team if needed
            current_team = project.custom_data.get('team', [])
            update_project_team(session, project, available_consultants, current_team, current_date)

        except Exception as e:
            logging.error(f"Error updating project {project.ProjectID}: {str(e)}")
            session.rollback()
        else:
            session.commit()

def generate_daily_consultant_deliverables(session, current_date, projects):
    consultant_daily_hours = defaultdict(float)
    
    active_projects = [p for p in projects if p.Status == 'In Progress']
    random.shuffle(active_projects)
    
    for project in active_projects:
        project_actual_hours = Decimal('0.0')

        for deliverable_id, deliverable_meta in project.custom_data.get('deliverables', {}).items():
            deliverable = session.query(Deliverable).get(deliverable_id)
            if deliverable.Status == 'Completed' or deliverable.PlannedStartDate > current_date:
                continue

            if deliverable.Status == 'Not Started':
                deliverable.ActualStartDate = current_date
                deliverable.Status = 'In Progress'

            remaining_hours = Decimal(str(deliverable_meta['target_hours'])) - Decimal(str(deliverable.ActualHours))

            if remaining_hours <= Decimal('0.0'):
                continue

            for consultant_id in project.custom_data.get('team', []):
                consultant = session.query(Consultant).get(consultant_id)
                consultant_title = consultant.custom_data.get('title_id', 1)  # Default to 1 if not present
                max_daily_hours = Decimal(str(project_settings.MAX_DAILY_HOURS_PER_TITLE.get(consultant_title, 8.0)))
                min_daily_hours = Decimal(str(project_settings.MIN_DAILY_HOURS_PER_PROJECT.get(consultant_title, 2.0)))

                if consultant_daily_hours[consultant_id] >= max_daily_hours:
                    continue

                consultant_hours_today = Decimal(str(consultant_daily_hours[consultant_id]))
                available_hours = min(max_daily_hours - consultant_hours_today, remaining_hours)

                if available_hours <= Decimal('0.0'):
                    continue

                hours = round_decimal(Decimal(str(random.uniform(float(min_daily_hours), float(available_hours)))), 1)
                consultant_deliverable = ConsultantDeliverable(
                    ConsultantID=consultant_id,
                    DeliverableID=deliverable_id,
                    Date=current_date,
                    Hours=float(hours)
                )
                session.add(consultant_deliverable)
                deliverable_meta['consultant_deliverables'].append(consultant_deliverable)
                remaining_hours -= hours
                deliverable.ActualHours = float(round_decimal(Decimal(str(deliverable.ActualHours)) + hours, 1))
                project_actual_hours += hours
                consultant_daily_hours[consultant_id] += float(hours)

            deliverable.Progress = min(100, int((Decimal(str(deliverable.ActualHours)) / Decimal(str(deliverable_meta['target_hours']))) * 100))

        project.ActualHours = float(round_decimal(Decimal(str(project.ActualHours)) + project_actual_hours, 1))
        project.Progress = min(100, int((Decimal(str(project.ActualHours)) / Decimal(str(project.custom_data['target_hours']))) * 100))

    session.commit()

def update_project_statuses(session, current_date, available_consultants):
    projects = session.query(Project).all()
    for project in projects:
        if project.Status in ['Completed', 'Cancelled']:
            continue

        if project.Status == 'Not Started' and current_date >= project.ActualStartDate:
            project.Status = 'In Progress'
            logging.info(f"Starting project {project.ProjectID} on {current_date}")

        if project.Status == 'In Progress':
            all_deliverables_completed = True
            total_target_hours = Decimal(project.custom_data.get('target_hours', 0))
            weighted_progress = Decimal('0.0')

            for deliverable_id, deliverable_meta in project.custom_data.get('deliverables', {}).items():
                deliverable = session.query(Deliverable).get(deliverable_id)

                if Decimal(deliverable.ActualHours) >= Decimal(deliverable_meta['target_hours']):
                    deliverable.Status = 'Completed'
                    deliverable.SubmissionDate = current_date
                    if project.Type == 'Fixed':
                        deliverable.InvoicedDate = current_date + timedelta(days=random.randint(1, 7))
                elif Decimal(deliverable.ActualHours) > Decimal('0.0'):
                    deliverable.Status = 'In Progress'
                    all_deliverables_completed = False
                else:
                    deliverable.Status = 'Not Started'
                    all_deliverables_completed = False

                deliverable_progress = (Decimal(deliverable.ActualHours) / Decimal(deliverable_meta['target_hours'])) * 100
                deliverable_weight = Decimal(deliverable_meta['target_hours']) / total_target_hours
                weighted_progress += deliverable_progress * deliverable_weight
                deliverable.Progress = min(100, int(deliverable_progress))

            project.Progress = min(100, int(weighted_progress))

            if Decimal(project.ActualHours) == Decimal('0.0') and current_date > project.ActualStartDate + timedelta(days=120):
                project.Status = 'Cancelled'
                logging.warning(f"Project {project.ProjectID} cancelled due to inactivity")
            elif all_deliverables_completed:
                project.Status = 'Completed'
                project.ActualEndDate = current_date
                handle_project_completion(session, project, current_date, available_consultants)
    session.commit()


def generate_project_expenses_for_year(session, simulation_end_date):
    projects = session.query(Project).filter(Project.Status.in_(['In Progress', 'Completed'])).all()
    
    for project in projects:
        total_consultant_cost = sum(cd.Hours * calculate_hourly_cost(session, cd.ConsultantID, cd.Date.year)
                                    for deliverable_meta in project.custom_data.get('deliverables', {}).values()
                                    for cd in deliverable_meta.get('consultant_deliverables', []))

        expenses = []
        for deliverable_id, deliverable_meta in project.custom_data.get('deliverables', {}).items():
            deliverable = session.query(Deliverable).get(deliverable_id)
            
            expense_start_date = deliverable.ActualStartDate or deliverable.PlannedStartDate
            expense_end_date = min(deliverable.SubmissionDate or simulation_end_date,
                                   project.ActualEndDate or simulation_end_date,
                                   simulation_end_date)

            if expense_start_date >= expense_end_date:
                continue

            deliverable_expenses = generate_project_expenses(project, total_consultant_cost, [deliverable])
            
            for expense_data in deliverable_expenses:
                consultant_deliverable_dates = [cd.Date for cd in deliverable_meta.get('consultant_deliverables', [])
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
                    Amount=expense_data['Amount'],
                    Description=expense_data['Description'],
                    Category=expense_data['Category'],
                    IsBillable=expense_data['IsBillable']
                )
                expenses.append(expense)

        session.add_all(expenses)

    session.commit()


