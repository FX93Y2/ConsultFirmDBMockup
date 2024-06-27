import random
from datetime import timedelta
from sqlalchemy import func, or_
from sqlalchemy.orm import sessionmaker
from data_generator.create_db import Project, Consultant, ConsultantTitleHistory, Deliverable, ConsultantDeliverable, ProjectBillingRate, Payroll, engine

def assign_projects_to_consultants():
    Session = sessionmaker(bind=engine)
    session = Session()

    projects = session.query(Project).all()

    for project in projects:
        # Step 1: Determine the required skill level for the project
        project_complexity = random.choice(['Low', 'Medium', 'High'])
        required_title_levels = {
            'Low': [1, 2, 3],
            'Medium': [2, 3, 4],
            'High': [3, 4, 5, 6]
        }[project_complexity]

        # Step 2: Find suitable consultants
        suitable_consultants = session.query(Consultant).join(ConsultantTitleHistory).filter(
            ConsultantTitleHistory.TitleID.in_(required_title_levels),
            ConsultantTitleHistory.StartDate <= project.PlannedEndDate,
            or_(ConsultantTitleHistory.EndDate >= project.PlannedStartDate, ConsultantTitleHistory.EndDate == None)
        ).all()

        # Assign consultants to the project
        num_consultants = random.randint(2, min(5, len(suitable_consultants)))
        assigned_consultants = random.sample(suitable_consultants, num_consultants)

        # Generate project billing rates
        for title_id in range(1, 7):  # Assuming 6 title levels
            base_rate = {
                1: random.uniform(80, 120),
                2: random.uniform(120, 180),
                3: random.uniform(180, 250),
                4: random.uniform(250, 350),
                5: random.uniform(350, 500),
                6: random.uniform(500, 700)
            }[title_id]

            # Adjust rate based on project complexity
            complexity_factor = {'Low': 0.9, 'Medium': 1.0, 'High': 1.2}[project_complexity]
            rate = base_rate * complexity_factor

            # Add some randomness
            rate *= random.uniform(0.95, 1.05)

            # Add the BillingRate table
            billing_rate = ProjectBillingRate(
                ProjectID=project.ProjectID,
                TitleID=title_id,
                Rate=round(rate, 2)
            )
            session.add(billing_rate)

        # Step5: Distribute work across deliverables
        deliverables = session.query(Deliverable).filter(Deliverable.ProjectID == project.ProjectID).all()
        
        for deliverable in deliverables:
            total_hours = deliverable.PlannedHours
            remaining_hours = total_hours

            for consultant in assigned_consultants:
                if remaining_hours <= 0:
                    break

                # Assign hours to consultant
                consultant_hours = min(remaining_hours, random.randint(8, 40))  # Assign 8 to 40 hours per consultant
                remaining_hours -= consultant_hours

                # Create ConsultantDeliverable entry
                consultant_deliverable = ConsultantDeliverable(
                    ConsultantID=consultant.ConsultantID,
                    DeliverableID=deliverable.DeliverableID,
                    Hours=consultant_hours
                )
                session.add(consultant_deliverable)

        # Step 6: Calculate project cost and revenue
        if project.Type == 'Time-and-Materials':
            cost = 0
            revenue = 0
            for deliverable in deliverables:
                for consultant_deliverable in session.query(ConsultantDeliverable).filter(ConsultantDeliverable.DeliverableID == deliverable.DeliverableID):
                    consultant_title = session.query(ConsultantTitleHistory).filter(
                        ConsultantTitleHistory.ConsultantID == consultant_deliverable.ConsultantID,
                        ConsultantTitleHistory.StartDate <= project.PlannedEndDate,
                        or_(ConsultantTitleHistory.EndDate >= project.PlannedStartDate, ConsultantTitleHistory.EndDate == None)
                    ).first()

                    if consultant_title:
                        # Calculate cost (based on consultant's salary)
                        avg_monthly_salary = session.query(func.avg(Payroll.Amount)).filter(
                            Payroll.ConsultantID == consultant_deliverable.ConsultantID
                        ).scalar() or 0
                        daily_rate = avg_monthly_salary / 22  # Assuming 22 working days per month
                        hourly_rate = daily_rate / 8  # Assuming 8 working hours per day
                        cost += hourly_rate * consultant_deliverable.Hours

                        # Calculate revenue (based on project billing rate)
                        billing_rate = session.query(ProjectBillingRate).filter(
                            ProjectBillingRate.ProjectID == project.ProjectID,
                            ProjectBillingRate.TitleID == consultant_title.TitleID
                        ).first()
                        if billing_rate:
                            revenue += billing_rate.Rate * consultant_deliverable.Hours

            project.PlannedHours = sum(d.PlannedHours for d in deliverables)
            
        else:  # Fixed-price project
            cost = sum(d.PlannedHours for d in deliverables) * random.uniform(100, 200)  # Assume average hourly cost between $100 and $200
            revenue = project.Price or 0

        # Step 7: Introduce some variability to make some projects profitable and others unprofitable
        profit_factor = random.uniform(0.8, 1.2)  # This will make some projects lose money and others profit
        if project.Type == 'Fixed-price':
            project.Price = revenue * profit_factor
        else:
            project.PlannedHours = int(sum(d.PlannedHours for d in deliverables) * profit_factor)

    session.commit()
    session.close()

def main():
    assign_projects_to_consultants()