import random
from sqlalchemy.orm import sessionmaker
from data_generator.create_db import Project, Title, ProjectBillingRate, engine

def generate_project_billing_rate():
    Session = sessionmaker(bind=engine)
    session = Session()

    # Query all project IDs from the Project table for Time-and-Materials projects
    project_ids = session.query(Project.ProjectID).filter(Project.Type == 'Time-and-Materials').all()
    project_ids = [project_id[0] for project_id in project_ids]  # Extracting project ID from tuple

    # Query all title IDs from the Title table
    title_ids = session.query(Title.TitleID).all()
    title_ids = [title_id[0] for title_id in title_ids]  # Extracting title ID from tuple

    billing_rate_data = []

    for project_id in project_ids:
        base_rates = {
            1: random.randint(80, 120),
            2: random.randint(120, 160),
            3: random.randint(160, 200),
            4: random.randint(200, 240),
            5: random.randint(240, 280),
            6: random.randint(280, 320)
        }

        for title_id in title_ids:
            base_rate = base_rates[title_id]
            min_rate = base_rate * 0.9
            max_rate = base_rate * 1.1
            rate = round(random.uniform(min_rate, max_rate), 2)

            billing_rate = ProjectBillingRate(
                ProjectID=project_id,
                TitleID=title_id,
                Rate=rate
            )
            billing_rate_data.append(billing_rate)

    session.add_all(billing_rate_data)
    session.commit()
    session.close()

def main():
    generate_project_billing_rate()