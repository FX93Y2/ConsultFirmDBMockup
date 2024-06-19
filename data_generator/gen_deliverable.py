import random
from datetime import timedelta
from sqlalchemy.orm import sessionmaker
from sqlalchemy import func, or_, extract
from data_generator.create_db import Project, Deliverable, Consultant, ConsultantTitleHistory, ConsultantDeliverable, ProjectBillingRate, Payroll, engine

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

        # Ensure at least one higher level consultant (senior consultant) is assigned to each project
        senior_consultant_titles = [4, 5, 6]  # Title IDs 4, 5 and 6 must be in projects
        senior_consultants = [consultant for consultant in available_consultants if consultant[1] in senior_consultant_titles]
        if senior_consultants:
            senior_consultant = random.choice(senior_consultants)
            assigned_consultants.append(senior_consultant)
            available_consultants.remove(senior_consultant)
            num_consultants -= 1

        for _ in range(num_consultants):
            if available_consultants:
                consultant = random.choice(available_consultants)
                assigned_consultants.append(consultant)
                available_consultants.remove(consultant)

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

        # Calculate the aggregated hour * billing rate and fake a profit margin
        aggregated_cost = 0
        if project.Type == 'Time-and-Materials':
            for consultant in assigned_consultants:
                billing_rate = session.query(ProjectBillingRate).filter(
                    ProjectBillingRate.ProjectID == project.ProjectID,
                    ProjectBillingRate.TitleID == consultant[1]
                ).first()
                if billing_rate:
                    consultant_aggregated_cost = sum(
                        consultant_deliverable.Hours * billing_rate.Rate for consultant_deliverable in session.query(ConsultantDeliverable).filter(
                            ConsultantDeliverable.ConsultantID == consultant[0].ConsultantID,
                            ConsultantDeliverable.DeliverableID == deliverable.DeliverableID
                        ).all()
                    )
                    aggregated_cost += consultant_aggregated_cost

        # Calculate aggregated cost from Payroll table for fixed-price projects
        if project.Type == 'Fixed-price':
            payroll_cost = 0
            for consultant in assigned_consultants:
                monthly_payrolls = session.query(func.avg(Payroll.Amount)).filter(
                    Payroll.ConsultantID == consultant[0].ConsultantID,
                    extract('year', Payroll.EffectiveDate) == project_year
                ).group_by(extract('month', Payroll.EffectiveDate)).all()
                
                average_monthly_payroll = sum([mp[0] for mp in monthly_payrolls]) / len(monthly_payrolls) if monthly_payrolls else 0
                payroll_cost += average_monthly_payroll

            aggregated_cost_fixed = aggregated_cost + payroll_cost
            deliverable.Price = aggregated_cost_fixed * (1 + random.uniform(0.1, 0.5))  # Adding profit margin

        profit_margin = random.uniform(0.1, 0.5)  # Fake a profit margin between 10% and 50%
        if project.Type == 'Time-and-Materials':
            project.PlannedHours = int(aggregated_cost / (1 + profit_margin))
        else:  # Fixed-price
            additional_expense = random.uniform(0.05, 0.2) * aggregated_cost  # Fake additional expense between 5% and 20%
            deliverable_prices = [d.Price for d in session.query(Deliverable.Price).filter(Deliverable.ProjectID == project.ProjectID).all() if d.Price is not None]
            project.Price = sum(deliverable_prices) + additional_expense

    session.commit()
    session.close()


def main():
    generate_deliverable()
    assign_consultants_to_deliverables()

if __name__ == "__main__":
    main()
