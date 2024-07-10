from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass
import random
from datetime import timedelta, date
from dateutil.relativedelta import relativedelta
from sqlalchemy import func, case
from collections import Counter
from ...db_model import *
from config import project_settings
import math
import logging

@dataclass
class ConsultantInfo:
    consultant: Consultant
    title_id: int
    last_project_date: date
    active_project_count: int



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
    for consultant_info in assigned_consultants:
        role = 'Project Manager' if consultant_info.title_id >= project_settings.HIGHER_LEVEL_TITLE_THRESHOLD else 'Team Member'
        
        team_member = ProjectTeam(
            ProjectID=project.ProjectID,
            ConsultantID=consultant_info.consultant.ConsultantID,
            Role=role,
            StartDate=project.ActualStartDate,
            EndDate=None
        )
        session.add(team_member)

def calculate_project_progress(project, deliverables):
    total_planned_hours = sum(d.PlannedHours for d in deliverables)
    
    if total_planned_hours == 0:
        project.Progress = 0
        return

    weighted_progress = sum((d.ActualHours / d.PlannedHours) * (d.PlannedHours / total_planned_hours) * 100 for d in deliverables)
    project.Progress = min(100, int(round(weighted_progress)))

def handle_project_completion(session, project, current_date, project_meta, available_consultants):
    session.query(ProjectTeam).filter(
        ProjectTeam.ProjectID == project.ProjectID,
        ProjectTeam.EndDate.is_(None)
    ).update({ProjectTeam.EndDate: current_date})

    for consultant_id in project_meta[project.ProjectID]['team']:
        consultant_info = next((c for c in available_consultants if c.consultant.ConsultantID == consultant_id), None)
        if consultant_info:
            consultant_info.active_project_count = max(0, consultant_info.active_project_count - 1)
            consultant_info.last_project_date = current_date

    logging.info(f"Project {project.ProjectID} completed on {current_date}. Consultants released.")

def get_available_consultants(session, current_date):
    two_months_ago = current_date - timedelta(days=60)
    
    results = session.query(
        Consultant,
        ConsultantTitleHistory.TitleID,
        func.coalesce(func.max(ProjectTeam.EndDate), func.min(ConsultantTitleHistory.StartDate)).label('last_project_date'),
        func.count(case((ProjectTeam.EndDate.is_(None) | (ProjectTeam.EndDate >= current_date), 1))).label('active_project_count')
    ).join(
        ConsultantTitleHistory,
        (Consultant.ConsultantID == ConsultantTitleHistory.ConsultantID) &
        (ConsultantTitleHistory.StartDate <= current_date) &
        ((ConsultantTitleHistory.EndDate.is_(None)) | (ConsultantTitleHistory.EndDate > current_date))
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

    available_consultants = [ConsultantInfo(consultant, title_id, last_project_date, active_project_count) 
                             for consultant, title_id, last_project_date, active_project_count in results]

    return available_consultants


def assign_project_to_business_unit(session, assigned_consultants, active_units, current_year):
    from ...db_model import Project
    
    consultant_unit_counts = Counter(consultant_info.consultant.BusinessUnitID for consultant_info in assigned_consultants)
    
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
    other_consultants = sorted([c for c in available_consultants if c != project_manager and c.active_project_count < project_settings.MAX_PROJECTS_PER_CONSULTANT], 
                               key=lambda x: (x.active_project_count, -x.title_id))
    
    # Ensure at least one senior consultant (level 3 or 4) if available
    senior_consultants = [c for c in other_consultants if 3 <= c.title_id <= 4]
    if senior_consultants:
        senior_consultant = senior_consultants[0]
        assigned_consultants.append(senior_consultant)
        other_consultants.remove(senior_consultant)
    
    # Assign mix of junior and mid-level consultants, prioritizing those with fewer projects
    remaining_slots = random.randint(project_settings.MIN_TEAM_SIZE - len(assigned_consultants), project_settings.MAX_TEAM_SIZE - len(assigned_consultants))
    junior_mid_consultants = [c for c in other_consultants if c.title_id <= project_settings.HIGHER_LEVEL_TITLE_THRESHOLD]
    team_members = junior_mid_consultants[:remaining_slots]
    assigned_consultants.extend(team_members)

    return assigned_consultants

def set_project_dates(project, current_date, assigned_consultants, session, simulation_start_date):
    if project.Type == 'Fixed':
        duration_months = random.randint(*project_settings.FIXED_PROJECT_DURATION_RANGE)
    else:  # Time and Material
        duration_months = random.randint(*project_settings.TIME_MATERIAL_PROJECT_DURATION_RANGE)
    
    project_manager = next(c for c in assigned_consultants if c.title_id >= project_settings.HIGHER_LEVEL_TITLE_THRESHOLD)
    pm_availability = max(get_consultant_availability(session, project_manager.consultant.ConsultantID, current_date), simulation_start_date)
    
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
             if c.consultant.ConsultantID not in current_team 
             and c.title_id <= 3
             and c.active_project_count < project_settings.MAX_PROJECTS_PER_CONSULTANT],
            key=lambda x: (x.active_project_count, -x.title_id)
        )
        new_members_count = min(target_team_size - len(current_team), len(potential_new_members))
        
        for consultant_info in potential_new_members[:new_members_count]:
            team_member = ProjectTeam(
                ProjectID=project.ProjectID,
                ConsultantID=consultant_info.consultant.ConsultantID,
                Role='Team Member',
                StartDate=current_date
            )
            session.add(team_member)
            current_team.append(consultant_info.consultant.ConsultantID)
            consultant_info.active_project_count += 1
            #logging.info(f"Added consultant {consultant_info.consultant.ConsultantID} to project {project.ProjectID} team")

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

