import random
from ...db_model import *
from config import project_settings

def all_consultants_fully_allocated(consultant_daily_hours):
    return all(hours >= project_settings.MAX_DAILY_HOURS for hours in consultant_daily_hours.values())

def allocate_work_for_project(session, project_meta, current_date, consultant_daily_hours):
    project_actual_hours = 0

    for deliverable_id, deliverable_meta in project_meta['deliverables'].items():
        deliverable = session.query(Deliverable).get(deliverable_id)
        if deliverable.Status == 'Completed' or deliverable.PlannedStartDate > current_date:
            continue

        remaining_hours = deliverable_meta['target_hours'] - deliverable.ActualHours

        if remaining_hours <= 0:
            continue

        for consultant_id in project_meta['team']:
            if consultant_daily_hours[consultant_id] >= project_settings.MAX_DAILY_HOURS:
                continue

            available_hours = min(project_settings.MAX_DAILY_HOURS - consultant_daily_hours[consultant_id], remaining_hours)

            if available_hours <= 0:
                continue

            hours = round(random.uniform(project_settings.MIN_DAILY_HOURS, min(available_hours, project_settings.MAX_DAILY_HOURS_PER_PROJECT)), 1)
            consultant_deliverable = ConsultantDeliverable(
                ConsultantID=consultant_id,
                DeliverableID=deliverable_id,
                Date=current_date,
                Hours=hours
            )
            session.add(consultant_deliverable)
            deliverable_meta['consultant_deliverables'].append(consultant_deliverable)
            remaining_hours -= hours
            deliverable.ActualHours += hours
            project_actual_hours += hours
            consultant_daily_hours[consultant_id] += hours

        deliverable.Progress = min(100, int((deliverable.ActualHours / deliverable_meta['target_hours']) * 100))

    return project_actual_hours