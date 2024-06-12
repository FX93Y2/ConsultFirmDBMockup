import os
import random
from datetime import timedelta
from faker import Faker
from sqlalchemy.orm import sessionmaker
from data_generator.create_db import Project, Client, BusinessUnit, engine

def generate_project_data(num_projects):
    Session = sessionmaker(bind=engine)
    session = Session()

    fake = Faker()

    statuses = ['Not Started', 'In Progress (<50%)', 'In Progress (>50%)', 'Completed', 'On Hold/Cancelled']
    status_probabilities = [0.10, 0.30, 0.30, 0.20, 0.10]
    start_date_delay_probabilities = [0.60, 0.30, 0.10]
    project_names = [
        "Strategy Development Plan", "Market Analysis Report", "Operational Efficiency Project",
        "Digital Transformation Initiative", "Customer Experience Improvement", "Financial Performance Review",
        "Organizational Restructuring", "Supply Chain Optimization", "IT System Integration",
        "Talent Management Program", "Risk Management Assessment", "Competitive Benchmarking Study",
        "Change Management Strategy", "Sustainability Plan", "Business Process Reengineering"
    ]

    project_data = []

    # Query all client IDs from the Client table
    client_ids = session.query(Client.ClientID).all()
    client_ids = [client_id[0] for client_id in client_ids]  # Extracting client ID from tuple

    unit_ides = session.query(BusinessUnit.BusinessUnitID).all()
    unit_ides = [unit_id[0] for unit_id in unit_ides]  # Extracting unit ID from tuple

    for i in range(num_projects):
        planned_start_date = fake.date_this_year()
        planned_end_date = planned_start_date + timedelta(days=random.randint(30, 180))

        start_delay_category = random.choices(
            ['within 1 week', '2-4 weeks', 'more than 4 weeks'],
            weights=start_date_delay_probabilities,
            k=1
        )[0]

        if start_delay_category == 'within 1 week':
            actual_start_date = planned_start_date + timedelta(days=random.randint(0, 7))
        elif start_delay_category == '2-4 weeks':
            actual_start_date = planned_start_date + timedelta(days=random.randint(14, 28))
        else:
            actual_start_date = planned_start_date + timedelta(days=random.randint(29, 60))

        status = random.choices(statuses, weights=status_probabilities, k=1)[0]

        client_id = random.choice(client_ids)  # Use a randomly selected existing ClientID
        unit_id = random.choice(unit_ides)  # This should ideally come from an existing Unit table
        project_name = random.choice(project_names)
        project_type = random.choice(['Fixed-price', 'Time and materials'])
        
        price = round(random.uniform(10000, 100000), 2) if project_type == 'Fixed-price' else None
        credit_at = fake.date_between_dates(date_start=actual_start_date, date_end=planned_end_date)
        actual_end_date = actual_start_date + timedelta(days=(planned_end_date - planned_start_date).days + random.randint(-10, 30)) if status == 'Completed' else None
        progress = random.randint(0, 100) if 'In Progress' in status else (100 if status == 'Completed' else 0)

        project = Project(
            ClientID=client_id,
            UnitID=unit_id,
            Name=project_name,
            Type=project_type,
            Status=status,
            PlannedStartDate=planned_start_date,
            PlannedEndDate=planned_end_date,
            ActualStartDate=actual_start_date,
            ActualEndDate=actual_end_date,
            Price=price,
            CreditAt=credit_at,
            Progress=progress
        )

        project_data.append(project)

    session.add_all(project_data)
    session.commit()
    session.close()

def main(num_projects):
    generate_project_data(num_projects)