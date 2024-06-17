import random
from datetime import timedelta
from sqlalchemy.orm import sessionmaker
from data_generator.create_db import Project, Deliverable, Consultant, ConsultantTitleHistory, ConsultantDeliverable, engine

def random_date_within(start, end):
    if start >= end:
        return start
    return start + timedelta(days=random.randint(0, (end - start).days))

def generate_deliverable():
    Session = sessionmaker(bind=engine)
    session = Session()

    # Query all project IDs from the Project table
    projects = session.query(Project).all()

    statuses = ["Pending", "In Progress", "Completed", "Delayed", "Cancelled"]
    status_weights = [0.20, 0.40, 0.30, 0.05, 0.05]

    deliverable_data = []
    deliverable_id = 1

    for project in projects:
        project_id = project.ProjectID
        num_deliverables = random.randint(1, 10)  # Number of deliverables per project
        project_type = project.Type

        project_planned_start = project.PlannedStartDate
        project_planned_end = project.PlannedEndDate
        project_actual_start = project.ActualStartDate
        project_actual_end = project.ActualEndDate if project.ActualEndDate else project_planned_end

        for _ in range(num_deliverables):
            name = f"Deliverable_{deliverable_id}"
            planned_start_date = random_date_within(project_planned_start, project_planned_end)
            actual_start_date = random_date_within(planned_start_date, project_actual_end)
            due_date = random_date_within(planned_start_date, project_planned_end)
            status = random.choices(statuses, status_weights)[0]
            submission_date = random_date_within(actual_start_date, project_actual_end) if status == "Completed" else None

            price = None
            if project_type == 'Fixed-price':
                price = round(random.uniform(1000, 20000), 2)  # Deliverable price range

            if status == "Pending":
                planned_hours = random.randint(10, 100)
                actual_hours = 0
                progress = 0
            elif status == "In Progress":
                planned_hours = random.randint(10, 100)
                actual_hours = random.randint(int(0.5 * planned_hours), int(0.9 * planned_hours))
                progress = random.randint(10, 90)
            elif status == "Completed":
                planned_hours = random.randint(10, 100)
                actual_hours = random.randint(int(0.9 * planned_hours), int(1.1 * planned_hours))
                progress = 100
            elif status == "Delayed" or status == "Cancelled":
                planned_hours = random.randint(10, 100)
                actual_hours = random.randint(int(0.5 * planned_hours), int(1.2 * planned_hours))
                progress = random.randint(0, 90)

            deliverable = Deliverable(
                DeliverableID=deliverable_id,
                ProjectID=project_id,
                Name=name,
                PlannedStartDate=planned_start_date,
                ActualStartDate=actual_start_date,
                Status=status,
                Price=price,
                DueDate=due_date,
                SubmissionDate=submission_date,
                Progress=progress,
                PlannedHours=planned_hours,
                ActualHours=actual_hours
            )
            deliverable_data.append(deliverable)
            deliverable_id += 1

    session.add_all(deliverable_data)
    session.commit()
    session.close()

def assign_consultants_to_deliverables():
    Session = sessionmaker(bind=engine)
    session = Session()

    deliverables = session.query(Deliverable).all()

    for deliverable in deliverables:
        project = session.query(Project).filter(Project.ProjectID == deliverable.ProjectID).first()
        project_year = project.PlannedStartDate.year

        # Query available consultants for the project year based on their title history
        available_consultants = []
        for consultant in session.query(Consultant).all():
            title_history = session.query(ConsultantTitleHistory).filter(
                ConsultantTitleHistory.ConsultantID == consultant.ConsultantID,
                ConsultantTitleHistory.StartDate <= project.PlannedEndDate,
                or_(ConsultantTitleHistory.EndDate >= project.PlannedStartDate, ConsultantTitleHistory.EndDate == None)
            ).first()

            if title_history and title_history.EventType != 'Attrition':
                available_consultants.append((consultant, title_history.TitleID))

        # Assign consultants to the deliverable based on the project requirements and consultant availability
        num_consultants = random.randint(1, 5)  # Number of consultants assigned to each deliverable
        assigned_consultants = []
        for _ in range(num_consultants):
            if available_consultants:
                consultant, title_id = random.choice(available_consultants)
                assigned_consultants.append((consultant, title_id))
                available_consultants.remove((consultant, title_id))

        planned_duration = (project.PlannedEndDate - project.PlannedStartDate).days
        total_hours = planned_duration * 8  # Assume 8 hours per day

        assigned_hours = 0
        for consultant, title_id in assigned_consultants:
            if assigned_hours < total_hours:
                remaining_hours = total_hours - assigned_hours
                consultant_hours = min(remaining_hours, random.randint(int(0.2 * total_hours), int(0.5 * total_hours)))
                assigned_hours += consultant_hours

                start_date = deliverable.ActualStartDate
                end_date = deliverable.SubmissionDate if deliverable.SubmissionDate else deliverable.DueDate

                if start_date and end_date:
                    current_date = start_date
                    while current_date <= end_date and consultant_hours > 0:
                        daily_hours = min(consultant_hours, 8)  # Assign up to 8 hours per day
                        consultant_deliverable = ConsultantDeliverable(
                            ConsultantID=consultant.ConsultantID,
                            DeliverableID=deliverable.DeliverableID,
                            Date=current_date,
                            Hours=daily_hours
                        )
                        session.add(consultant_deliverable)

                        consultant_hours -= daily_hours
                        current_date += timedelta(days=1)

    session.commit()
    session.close()

def main():
    generate_deliverable()
    assign_consultants_to_deliverables()