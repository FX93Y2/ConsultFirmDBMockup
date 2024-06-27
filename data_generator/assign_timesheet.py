import random
from datetime import datetime, timedelta
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from data_generator.create_db import ConsultantDeliverable, Deliverable, Project, engine

def generate_timesheet_entries():
    Session = sessionmaker(bind=engine)
    session = Session()

    # Fetch all existing ConsultantDeliverable entries
    deliverable_assignments = session.query(ConsultantDeliverable).all()

    new_timesheet_entries = []

    for assignment in deliverable_assignments:
        deliverable = session.query(Deliverable).filter_by(DeliverableID=assignment.DeliverableID).first()
        project = session.query(Project).filter_by(ProjectID=deliverable.ProjectID).first()

        # Determine the date range for this deliverable
        start_date = max(deliverable.ActualStartDate, project.ActualStartDate)
        end_date = min(deliverable.SubmissionDate or project.ActualEndDate or project.PlannedEndDate,
                       project.ActualEndDate or project.PlannedEndDate)

        total_hours = assignment.Hours
        remaining_hours = total_hours

        current_date = start_date
        while current_date <= end_date and remaining_hours > 0:
            if current_date.weekday() < 5:  # Monday to Friday
                daily_hours = min(random.randint(1, 8), remaining_hours)
                
                new_entry = ConsultantDeliverable(
                    ConsultantID=assignment.ConsultantID,
                    DeliverableID=assignment.DeliverableID,
                    Date=current_date,
                    Hours=daily_hours
                )
                new_timesheet_entries.append(new_entry)
                
                remaining_hours -= daily_hours
            
            current_date += timedelta(days=1)

    # Remove old entries and add new ones
    session.query(ConsultantDeliverable).delete()
    session.add_all(new_timesheet_entries)
    session.commit()
    session.close()

def main():
    generate_timesheet_entries()

if __name__ == "__main__":
    main()