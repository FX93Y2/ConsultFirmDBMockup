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
            
            for current_month in range(1, 12):
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

                # Generate monthly expenses for all active projects
                active_projects = session.query(Project).filter(Project.Status.in_(['Not Started', 'In Progress'])).all()
                for project in active_projects:
                    generate_expense_records(session, project, month_end)

                session.commit()

            print(f"Project generation for year {current_year} completed successfully.")

    except Exception as e:
        print(f"An error occurred while processing projects: {str(e)}")
        print(traceback.format_exc())
        session.rollback()
    finally:
        session.close()

def update_consultant_custom_data(session, consultant_id, project_id, action, current_date):
    consultant_custom_data = session.query(ConsultantCustomData).get(consultant_id)
    if not consultant_custom_data:
        consultant_custom_data = ConsultantCustomData(ConsultantID=consultant_id, CustomData={})
        session.add(consultant_custom_data)

    if action == 'add':
        consultant_custom_data.CustomData['active_project_count'] = consultant_custom_data.CustomData.get('active_project_count', 0) + 1
        consultant_custom_data.CustomData['last_project_date'] = current_date.isoformat()
    elif action == 'remove':
        consultant_custom_data.CustomData['active_project_count'] = max(0, consultant_custom_data.CustomData.get('active_project_count', 1) - 1)
        consultant_custom_data.CustomData['last_project_date'] = current_date.isoformat()

    session.flush()

def update_project_metadata(session, project, team, deliverables, target_hours):
    project_custom_data = session.query(ProjectCustomData).filter_by(ProjectID=project.ProjectID).first()
    if not project_custom_data:
        project_custom_data = ProjectCustomData(ProjectID=project.ProjectID, CustomData={})
        session.add(project_custom_data)
    
    project_custom_data.CustomData = {
        'team': [c.ConsultantID for c in team],
        'deliverables': {
            d.DeliverableID: {
                'target_hours': target_hours / len(deliverables),
                'consultant_deliverables': []
            } for d in deliverables
        },
        'target_hours': target_hours
    }
    session.flush()

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

        project_custom_data = session.query(ProjectCustomData).get(project.ProjectID)
        team_member_ids = project_custom_data.CustomData.get('team', [])
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
                update_consultant_custom_data(session, consultant_id, project.ProjectID, 'add', current_date)
                logging.info(f"Assigned consultant {consultant_id} to project {project.ProjectID}")

    session.commit()     


def create_new_projects_if_needed(session, current_date, available_consultants, active_units, simulation_start_date, monthly_targets):
    all_consultants = session.query(Consultant).all()
    
    project_manager_consultants = [c for c in all_consultants if session.query(ConsultantCustomData).get(c.ConsultantID).CustomData.get('title_id', 0) >= 4]
    
    project_manager_consultants.sort(key=lambda c: (
        session.query(ConsultantCustomData).get(c.ConsultantID).CustomData.get('active_project_count', 0),
        -session.query(ConsultantCustomData).get(c.ConsultantID).CustomData.get('title_id', 0)
    ))
    
    logging.info(f"Available project managers: {len(project_manager_consultants)}")
    logging.info(f"Top 5 PM candidates: {[(c.ConsultantID, session.query(ConsultantCustomData).get(c.ConsultantID).CustomData.get('title_id', 0), session.query(ConsultantCustomData).get(c.ConsultantID).CustomData.get('active_project_count', 0)) for c in project_manager_consultants[:5]]}")

    target_for_month = monthly_targets[current_date.month - 1]
    
    total_capacity = sum(max(0, project_settings.MAX_PROJECTS_PER_CONSULTANT.get(
        session.query(ConsultantCustomData).get(c.ConsultantID).CustomData.get('title_id', 1), 2) - 
        session.query(ConsultantCustomData).get(c.ConsultantID).CustomData.get('active_project_count', 0)
    ) for c in project_manager_consultants)
    
    adjusted_target = max(0, min(target_for_month, total_capacity))
    
    logging.info(f"Target for month: {target_for_month}, Adjusted target: {adjusted_target}, Total capacity: {total_capacity}")

    if adjusted_target > 0:
        std_dev = max(0.1, adjusted_target * 0.2)
        projects_to_create = max(0, round(norm.rvs(loc=adjusted_target, scale=std_dev)))
    else:
        projects_to_create = 0

    projects_this_month = len([p for p in session.query(Project).all() if 
        session.query(ProjectCustomData).get(p.ProjectID).CustomData.get('start_date', date.min).month == current_date.month and 
        session.query(ProjectCustomData).get(p.ProjectID).CustomData.get('start_date', date.min).year == current_date.year
    ])
    projects_to_create = max(0, projects_to_create - projects_this_month)

    logging.info(f"Target projects to create: {projects_to_create}")

    projects_created = 0
    for consultant in project_manager_consultants:
        if projects_created >= projects_to_create:
            break
        
        consultant_custom_data = session.query(ConsultantCustomData).get(consultant.ConsultantID)
        max_projects = project_settings.MAX_PROJECTS_PER_CONSULTANT.get(consultant_custom_data.CustomData.get('title_id', 1), 2)
        if consultant_custom_data.CustomData.get('active_project_count', 0) >= max_projects:
            continue

        logging.info(f"Attempting to create project with PM: {consultant.ConsultantID} (Title: {consultant_custom_data.CustomData.get('title_id', 0)}, Active Projects: {consultant_custom_data.CustomData.get('active_project_count', 0)})")
        project = create_new_project(session, current_date, all_consultants, active_units, simulation_start_date, project_manager=consultant)
        if project:
            projects_created += 1

            project_custom_data = session.query(ProjectCustomData).get(project.ProjectID)
            for consultant_id in project_custom_data.CustomData['team']:
                update_consultant_custom_data(session, consultant_id, project.ProjectID, 'add', current_date)

            available_consultants = [c for c in all_consultants if 
                session.query(ConsultantCustomData).get(c.ConsultantID).CustomData.get('active_project_count', 0) < 
                project_settings.MAX_PROJECTS_PER_CONSULTANT.get(session.query(ConsultantCustomData).get(c.ConsultantID).CustomData.get('title_id', 1), 2)
            ]
            available_consultants.sort(key=lambda c: (
                session.query(ConsultantCustomData).get(c.ConsultantID).CustomData.get('active_project_count', 0),
                -session.query(ConsultantCustomData).get(c.ConsultantID).CustomData.get('title_id', 0)
            ))
            logging.info(f"Successfully created project: ProjectID {project.ProjectID}")
        else:
            logging.warning(f"Failed to create new project with Project Manager: {consultant.ConsultantID}")

    logging.info(f"Date: {current_date}, New Projects Created: {projects_created}, Target: {adjusted_target}, Available Project Managers: {len(project_manager_consultants)}")
    return available_consultants


def create_new_project(session, current_date, available_consultants, active_units, simulation_start_date, project_manager):
    logging.info(f"Attempting to create new project with PM: {project_manager.ConsultantID} (Title: {project_manager.CustomData.CustomData.get('title_id', 'Unknown')})")

    try:
        eligible_consultants = [c for c in available_consultants if c.CustomData.CustomData.get('title_id', 0) <= project_manager.CustomData.CustomData.get('title_id', 0)]
        days_before = random.randint(0, 15)
        created_at = current_date - timedelta(days=days_before)
        created_at = max(created_at, simulation_start_date)
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
        assigned_consultants, remaining_slots = assign_consultants_to_project(session, eligible_consultants, project_manager, target_team_size)

        deliverables = generate_deliverables(project, target_hours)
        session.add_all(deliverables)
        session.flush()

        # Calculate project financials and generate predefined expenses
        estimated_total_cost, estimated_total_revenue, predefined_expenses = calculate_project_financials(session, project, assigned_consultants, current_date, deliverables)

        # Initialize project custom_data
        custom_data = {
            'team': [c.ConsultantID for c in assigned_consultants],
            'deliverables': {
                d.DeliverableID: {
                    'target_hours': float(d.PlannedHours),
                    'consultant_deliverables': []
                } for d in deliverables
            },
            'target_hours': float(target_hours),
            'target_team_size': target_team_size,
            'remaining_slots': remaining_slots,
            'predefined_expenses': predefined_expenses,
            'estimated_total_cost': float(estimated_total_cost),
            'estimated_total_revenue': float(estimated_total_revenue)
        }

        # Serialize dates in custom_data
        serialized_custom_data = serialize_dates(custom_data)

        project_custom_data = ProjectCustomData(
            ProjectID=project.ProjectID,
            CustomData=serialized_custom_data
        )
        session.add(project_custom_data)
        
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

        assign_project_team(session, project, assigned_consultants)
        session.flush()

        logging.info(f"Project {project.ProjectID} created with {len(assigned_consultants)} consultants. "
                     f"Target team size: {target_team_size}, Remaining slots: {remaining_slots}, "
                     f"Predefined expenses: {len(predefined_expenses)}")

        return project
    except Exception as e:
        logging.error(f"Error creating new project: {str(e)}")
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

            # Get project custom data
            project_custom_data = session.query(ProjectCustomData).get(project.ProjectID)
            if not project_custom_data:
                project_custom_data = ProjectCustomData(ProjectID=project.ProjectID, CustomData={})
                session.add(project_custom_data)

            # Update project team if needed
            current_team = project_custom_data.CustomData.get('team', [])
            update_project_team(session, project, available_consultants, current_team, current_date)

            # Update the project custom data
            project_custom_data.CustomData['team'] = current_team
            session.flush()

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
        project_custom_data = session.query(ProjectCustomData).filter_by(ProjectID=project.ProjectID).first()
        if not project_custom_data:
            continue

        predefined_expenses = project_custom_data.CustomData.get('predefined_expenses', [])

        for deliverable_id, deliverable_meta in project_custom_data.CustomData.get('deliverables', {}).items():
            deliverable = session.query(Deliverable).get(deliverable_id)
            if deliverable.Status == 'Completed' or deliverable.PlannedStartDate > current_date:
                continue

            if deliverable.Status == 'Not Started':
                deliverable.ActualStartDate = current_date
                deliverable.Status = 'In Progress'

            remaining_hours = Decimal(str(deliverable_meta['target_hours'])) - Decimal(str(deliverable.ActualHours))

            if remaining_hours <= Decimal('0.0'):
                continue

            for consultant_id in project_custom_data.CustomData.get('team', []):
                consultant_custom_data = session.query(ConsultantCustomData).filter_by(ConsultantID=consultant_id).first()
                if not consultant_custom_data:
                    continue
                consultant_title = consultant_custom_data.CustomData.get('title_id', 1)
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
                remaining_hours -= hours
                deliverable.ActualHours = float(round_decimal(Decimal(str(deliverable.ActualHours)) + hours, 1))
                project_actual_hours += hours
                consultant_daily_hours[consultant_id] += float(hours)


            deliverable.Progress = min(100, int((Decimal(str(deliverable.ActualHours)) / Decimal(str(deliverable_meta['target_hours']))) * 100))

        project.ActualHours = float(round_decimal(Decimal(str(project.ActualHours)) + project_actual_hours, 1))
        project.Progress = min(100, int((Decimal(str(project.ActualHours)) / Decimal(str(project_custom_data.CustomData['target_hours']))) * 100))

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
            project_custom_data = session.query(ProjectCustomData).get(project.ProjectID)
            total_target_hours = Decimal(project_custom_data.CustomData.get('target_hours', 0))
            weighted_progress = Decimal('0.0')

            for deliverable_id, deliverable_meta in project_custom_data.CustomData.get('deliverables', {}).items():
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
                handle_project_completion(session, project, current_date, available_consultants, current_date)
    session.commit()

def handle_project_completion(session, project, completion_date, available_consultants, current_date):
    # Update project status and end date
    project.Status = 'Completed'
    project.ActualEndDate = completion_date

    # Update ProjectTeam records
    team_members = session.query(ProjectTeam).filter(
        ProjectTeam.ProjectID == project.ProjectID,
        ProjectTeam.EndDate.is_(None)
    ).all()

    for team_member in team_members:
        team_member.EndDate = completion_date
        update_consultant_custom_data(session, team_member.ConsultantID, project.ProjectID, 'remove', completion_date)

        # Add consultant back to available pool if not at max projects
        consultant_custom_data = session.query(ConsultantCustomData).get(team_member.ConsultantID)
        max_projects = project_settings.MAX_PROJECTS_PER_CONSULTANT.get(consultant_custom_data.CustomData.get('title_id', 1), 2)
        if consultant_custom_data.CustomData.get('active_project_count', 0) < max_projects:
            consultant = session.query(Consultant).get(team_member.ConsultantID)
            if consultant not in available_consultants:
                available_consultants.append(consultant)

    logging.info(f"Project {project.ProjectID} completed on {completion_date}")
