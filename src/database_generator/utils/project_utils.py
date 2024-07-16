from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass
import random
from datetime import timedelta, date
from sqlalchemy import func, case
from collections import Counter
from ...db_model import *
from .project_financial_utils import update_project_financials
from config import project_settings
import math
import logging

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


def assign_project_team(session, project, assigned_consultants):
    project_manager = assigned_consultants[0]
    team_leads = assigned_consultants[1:4]  # Next 3 consultants are team leads
    team_members = assigned_consultants[4:]  # Remaining consultants are team members

    # Assign Project Manager
    team_member = ProjectTeam(
        ProjectID=project.ProjectID,
        ConsultantID=project_manager.ConsultantID,
        Role='Project Manager',
        StartDate=project.ActualStartDate,
        EndDate=None
    )
    session.add(team_member)
    logging.info(f"Assigned Project Manager: {project_manager.ConsultantID} (Title: {project_manager.custom_data.get('title_id', 'Unknown')}) to ProjectID: {project.ProjectID}")

    # Assign Team Leads
    for consultant in team_leads:
        team_member = ProjectTeam(
            ProjectID=project.ProjectID,
            ConsultantID=consultant.ConsultantID,
            Role='Team Lead',
            StartDate=project.ActualStartDate,
            EndDate=None
        )
        session.add(team_member)
        logging.info(f"Assigned Team Lead: {consultant.ConsultantID} (Title: {consultant.custom_data.get('title_id', 'Unknown')}) to ProjectID: {project.ProjectID}")

    # Assign Team Members
    for consultant in team_members:
        team_member = ProjectTeam(
            ProjectID=project.ProjectID,
            ConsultantID=consultant.ConsultantID,
            Role='Team Member',
            StartDate=project.ActualStartDate,
            EndDate=None
        )
        session.add(team_member)
        logging.info(f"Assigned Team Member: {consultant.ConsultantID} (Title: {consultant.custom_data.get('title_id', 'Unknown')}) to ProjectID: {project.ProjectID}")

    session.flush()

def calculate_project_progress(project, deliverables):
    total_planned_hours = sum(d.PlannedHours for d in deliverables)
    
    if total_planned_hours == 0:
        project.Progress = 0
        return

    weighted_progress = sum((d.ActualHours / d.PlannedHours) * (d.PlannedHours / total_planned_hours) * 100 for d in deliverables)
    project.Progress = min(100, int(round(weighted_progress)))

def handle_project_completion(session, project, completion_date, available_consultants):
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

        # Update consultant metadata
        consultant = session.query(Consultant).get(team_member.ConsultantID)
        if consultant:
            consultant.custom_data['active_project_count'] = max(0, consultant.custom_data.get('active_project_count', 1) - 1)

            # Add consultant back to available pool if not at max projects
            max_projects = project_settings.MAX_PROJECTS_PER_CONSULTANT.get(consultant.custom_data.get('title_id', 1), 2)
            if consultant.custom_data.get('active_project_count', 0) < max_projects:
                if consultant not in available_consultants:
                    available_consultants.append(consultant)

    # Calculate and update final project metrics
    update_project_financials(session, project)

    logging.info(f"Project {project.ProjectID} completed on {completion_date}")

def get_available_consultants(session, current_date):
    two_months_ago = current_date - timedelta(days=60)
    
    # Subquery to get the most recent title for each consultant
    latest_title = session.query(
        ConsultantTitleHistory.ConsultantID,
        func.max(ConsultantTitleHistory.StartDate).label('latest_start_date')
    ).filter(
        ConsultantTitleHistory.StartDate <= current_date
    ).group_by(ConsultantTitleHistory.ConsultantID).subquery()

    results = session.query(
        Consultant,
        ConsultantTitleHistory.TitleID,
        func.coalesce(func.max(ProjectTeam.EndDate), func.min(ConsultantTitleHistory.StartDate)).label('last_project_date'),
        func.count(case((ProjectTeam.EndDate.is_(None) | (ProjectTeam.EndDate >= current_date), 1))).label('active_project_count')
    ).join(
        latest_title,
        Consultant.ConsultantID == latest_title.c.ConsultantID
    ).join(
        ConsultantTitleHistory,
        (Consultant.ConsultantID == ConsultantTitleHistory.ConsultantID) &
        (ConsultantTitleHistory.StartDate == latest_title.c.latest_start_date)
    ).outerjoin(
        ProjectTeam,
        (Consultant.ConsultantID == ProjectTeam.ConsultantID) &
        (ProjectTeam.StartDate <= current_date) &
        ((ProjectTeam.EndDate.is_(None)) | (ProjectTeam.EndDate >= two_months_ago))
    ).group_by(
        Consultant.ConsultantID,
        ConsultantTitleHistory.TitleID
    ).order_by(
        'active_project_count',
        'last_project_date'
    ).all()

    available_consultants = []
    for consultant, title_id, last_project_date, active_project_count in results:
        # Initialize custom_data if it doesn't exist
        if not hasattr(consultant, 'custom_data'):
            consultant.custom_data = {}
        
        # Update consultant metadata
        consultant.custom_data.update({
            'title_id': title_id,
            'last_project_date': last_project_date,
            'active_project_count': int(active_project_count) if active_project_count is not None else 0
        })
        available_consultants.append(consultant)

    return available_consultants


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

def assign_consultants_to_project(available_consultants, project_manager):
    assigned_consultants = [project_manager]
    
    # Separate consultants by title
    high_level_consultants = [c for c in available_consultants if c != project_manager and c.custom_data.get('title_id', 0) in [4, 5, 6]]
    senior_consultants = [c for c in available_consultants if c != project_manager and c.custom_data.get('title_id', 0) == 3]
    junior_consultants = [c for c in available_consultants if c != project_manager and c.custom_data.get('title_id', 0) in [1, 2]]

    # Sort consultants by active project count (ascending) and then by title_id (descending)
    for consultant_list in [high_level_consultants, senior_consultants, junior_consultants]:
        consultant_list.sort(key=lambda c: (c.custom_data.get('active_project_count', 0), -c.custom_data.get('title_id', 0)))

    # Assign team leads
    team_leads = []
    # First, assign high-level consultants as team leads (maximum 2)
    for c in high_level_consultants:
        max_projects = project_settings.MAX_PROJECTS_PER_CONSULTANT.get(c.custom_data.get('title_id', 1), 2)
        if c.custom_data.get('active_project_count', 0) < max_projects:
            team_leads.append(c)
            if len(team_leads) == 2:
                break

    # Then, add senior consultants as team leads (maximum 1)
    if len(team_leads) < 3 and senior_consultants:
        for c in senior_consultants:
            max_projects = project_settings.MAX_PROJECTS_PER_CONSULTANT.get(c.custom_data.get('title_id', 1), 2)
            if c.custom_data.get('active_project_count', 0) < max_projects:
                team_leads.append(c)
                senior_consultants.remove(c)
                break

    assigned_consultants.extend(team_leads)

    # Calculate remaining slots
    remaining_slots = random.randint(
        max(project_settings.MIN_TEAM_SIZE - len(assigned_consultants), 0),
        max(project_settings.MAX_TEAM_SIZE - len(assigned_consultants), 0)
    )

    # Fill remaining slots with a mix of senior and junior consultants
    available_team_members = senior_consultants + junior_consultants
    available_team_members = [c for c in available_team_members 
                              if c.custom_data.get('active_project_count', 0) < project_settings.MAX_PROJECTS_PER_CONSULTANT.get(c.custom_data.get('title_id', 1), 2)]
    available_team_members.sort(key=lambda c: (c.custom_data.get('active_project_count', 0), -c.custom_data.get('title_id', 0)))

    assigned_consultants.extend(available_team_members[:remaining_slots])

    logging.info(f"Assigned team: PM={project_manager.ConsultantID}, "
                 f"Team Leads={[c.ConsultantID for c in team_leads]}, "
                 f"Team Members={[c.ConsultantID for c in assigned_consultants if c not in [project_manager] + team_leads]}")

    return assigned_consultants

def set_project_dates(project, current_date, assigned_consultants, session, simulation_start_date):
    if project.Type == 'Fixed':
        duration_months = random.randint(*project_settings.FIXED_PROJECT_DURATION_RANGE)
    else:  # Time and Material
        duration_months = random.randint(*project_settings.TIME_MATERIAL_PROJECT_DURATION_RANGE)
    
    project_manager = next((c for c in assigned_consultants if c.custom_data.get('title_id', 0) >= project_settings.HIGHER_LEVEL_TITLE_THRESHOLD), None)
    if not project_manager:
        logging.warning(f"No suitable project manager found for project {project.ProjectID}")
        project_manager = assigned_consultants[0]  # Fallback to the first consultant if no suitable PM is found
    
    pm_availability = max(get_consultant_availability(session, project_manager.ConsultantID, current_date), simulation_start_date)
    
    # Maintain variance between PlannedStartDate and ActualStartDate
    project.PlannedStartDate = pm_availability + timedelta(days=random.randint(0, 14))
    actual_start_variance = timedelta(days=random.randint(0, 7))
    project.ActualStartDate = project.PlannedStartDate + actual_start_variance

    # Set initial status
    project.Status = 'Not Started'
    
    # Calculate end date based on working days
    working_days = duration_months * 21  # Assuming 21 working days per month
    project.PlannedEndDate = project.PlannedStartDate
    days_added = 0
    while days_added < working_days:
        project.PlannedEndDate += timedelta(days=1)
        if project.PlannedEndDate.weekday() < 5:  # Monday = 0, Friday = 4
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
    remaining_target_hours = Decimal(str(target_hours))
    project_duration = (project.PlannedEndDate - project.PlannedStartDate).days

    for i in range(num_deliverables):
        is_last_deliverable = (i == num_deliverables - 1)
        
        if is_last_deliverable:
            deliverable_target_hours = remaining_target_hours
        else:
            min_hours = Decimal('10')
            max_hours = max(min_hours, (remaining_target_hours - (num_deliverables - i - 1) * min_hours))
            deliverable_target_hours = Decimal(str(random.uniform(float(min_hours), float(max_hours))))
            remaining_target_hours -= deliverable_target_hours

        start_date = project.PlannedStartDate if i == 0 else deliverables[-1].DueDate + timedelta(days=1)
        deliverable_duration = max(1, int((deliverable_target_hours / Decimal(str(target_hours))) * project_duration))
        due_date = min(start_date + timedelta(days=deliverable_duration), project.PlannedEndDate)

        planned_hours = round_decimal(deliverable_target_hours * (Decimal(str(project.PlannedHours)) / Decimal(str(target_hours))), 1)
        
        deliverable = Deliverable(
            ProjectID=project.ProjectID,
            Name=f"Deliverable {i+1}",
            PlannedStartDate=start_date,
            ActualStartDate=None,  # This will be set when work actually starts on the deliverable
            DueDate=due_date,
            PlannedHours=float(planned_hours),  # Convert to float for database storage
            ActualHours=0.0,
            Progress=0,
            Status='Not Started'
        )
        deliverables.append(deliverable)

    return deliverables

def round_decimal(value, decimal_places=1):
    return value.quantize(Decimal(10) ** -decimal_places, rounding=ROUND_HALF_UP)

def update_project_team(session, project, available_consultants, current_team, current_date):
    target_team_size = random.randint(6, 12)
    
    if len(current_team) < target_team_size:
        potential_new_members = sorted(
            [c for c in available_consultants 
             if c.ConsultantID not in current_team 
             and c.custom_data.get('title_id', 0) <= 3
             and c.custom_data.get('active_project_count', 0) < project_settings.MAX_PROJECTS_PER_CONSULTANT.get(c.custom_data.get('title_id', 1), 2)],
            key=lambda x: (x.custom_data.get('active_project_count', 0), -x.custom_data.get('title_id', 0))
        )
        new_members_count = min(target_team_size - len(current_team), len(potential_new_members))
        
        for consultant in potential_new_members[:new_members_count]:
            team_member = ProjectTeam(
                ProjectID=project.ProjectID,
                ConsultantID=consultant.ConsultantID,
                Role='Team Member',
                StartDate=current_date
            )
            session.add(team_member)
            current_team.append(consultant.ConsultantID)
            consultant.custom_data['active_project_count'] = consultant.custom_data.get('active_project_count', 0) + 1
            #logging.info(f"Added consultant {consultant.ConsultantID} to project {project.ProjectID} team")

    #logging.info(f"Updated team size for project {project.ProjectID}: {len(current_team)} members")

def log_consultant_projects(session, current_date):
    consultants = session.query(Consultant).all()
    for consultant in consultants:
        active_projects = session.query(Project).join(ProjectTeam).filter(
            ProjectTeam.ConsultantID == consultant.ConsultantID,
            ProjectTeam.StartDate <= current_date,
            (ProjectTeam.EndDate.is_(None) | (ProjectTeam.EndDate >= current_date)),
            Project.Status.in_(['Not Started', 'In Progress'])
        ).all()

