import random
from sqlalchemy.orm import sessionmaker
from data_generator.create_db import Project, Title, ProjectBillingRate, engine

billing_rate_ranges = {
    1: ('Junior Consultant (Time and Materials)', (100, 150)),
    2: ('Junior Consultant (Fixed Price)', (80, 120)),
    3: ('Consultant (Time and Materials)', (150, 200)),
    4: ('Consultant (Fixed Price)', (120, 180)),
    5: ('Senior Consultant (Time and Materials)', (200, 300)),
    6: ('Senior Consultant (Fixed Price)', (180, 250))
}

def get_random_rate(title_id):
    title, rate_range = billing_rate_ranges[title_id]
    rate = random.uniform(rate_range[0], rate_range[1])
    return round(rate, 2)

def generate_project_billing_rate():
    Session = sessionmaker(bind=engine)
    session = Session()

    # Query all project IDs from the Project table
    project_ids = session.query(Project.ProjectID).all()
    project_ids = [project_id[0] for project_id in project_ids]  # Extracting project ID from tuple

    # Query all title IDs from the Title table
    title_ids = session.query(Title.TitleID).all()
    title_ids = [title_id[0] for title_id in title_ids]  # Extracting title ID from tuple

    billing_rate_data = []

    billing_rate_id = 1
    for project_id in project_ids:
        for title_id in title_ids:
            rate = get_random_rate(title_id)
            billing_rate = ProjectBillingRate(
                BillingRateID=billing_rate_id,
                ProjectID=project_id,
                TitleID=title_id,
                Rate=rate
            )
            billing_rate_data.append(billing_rate)
            billing_rate_id += 1

    session.add_all(billing_rate_data)
    session.commit()
    session.close()

def main():
    generate_project_billing_rate()
