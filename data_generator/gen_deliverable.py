import random
from datetime import timedelta
from sqlalchemy.orm import sessionmaker
from data_generator.create_db import Project, Deliverable, Consultant, ConsultantDeliverable, engine

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
    consultants = session.query(Consultant).all()

    consultant_deliverable_data = []

    for deliverable in deliverables:
        num_consultants = random.randint(1, 5)  # Number of consultants assigned to each deliverable
        assigned_consultants = random.sample(consultants, num_consultants)

        for consultant in assigned_consultants:
            start_date = deliverable.ActualStartDate
            end_date = deliverable.SubmissionDate if deliverable.SubmissionDate else deliverable.DueDate

            if start_date and end_date:
                current_date = start_date
                while current_date <= end_date:
                    allocation = random.choices(['Full-time', 'Part-time'], weights=[0.85, 0.15])[0]
                    base_hours = random.randint(6, 10) if allocation == 'Full-time' else random.randint(3, 5)
                    actual_hours = int(base_hours * random.uniform(0.8, 1.2))  # Introduce variations in daily hours

                    consultant_deliverable = ConsultantDeliverable(
                        ConsultantID=consultant.ConsultantID,
                        DeliverableID=deliverable.DeliverableID,
                        Date=current_date,
                        Hours=actual_hours
                    )
                    consultant_deliverable_data.append(consultant_deliverable)

                    current_date += timedelta(days=1)

    session.add_all(consultant_deliverable_data)
    session.commit()
    session.close()

def main():
    generate_deliverable()
    assign_consultants_to_deliverables()