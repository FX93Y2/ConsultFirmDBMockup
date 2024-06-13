import os
import random
from datetime import timedelta, datetime
from faker import Faker
from sqlalchemy.orm import sessionmaker
from data_generator.create_db import Project, Client, BusinessUnit, engine

def adjust_probabilities(base_probabilities, year_diff):
    adjustment_factor = 0.15 * year_diff
    adjusted_probabilities = base_probabilities.copy()
    adjusted_probabilities[0] = max(base_probabilities[0] - adjustment_factor, 0)  # 'Not Started'
    adjusted_probabilities[1] = max(base_probabilities[1] - adjustment_factor, 0)  # 'In Progress (<50%)'
    adjusted_probabilities[2] = max(base_probabilities[2] - adjustment_factor*0.5, 0)  # 'In Progress (>50%)'
    adjusted_probabilities[3] = min(base_probabilities[3] + adjustment_factor*1.5, 1)  # 'Completed'
    adjusted_probabilities[4] = min(base_probabilities[4] + adjustment_factor*0.2, 1)  # 'On Hold/Cancelled'

    total = sum(adjusted_probabilities)
    return [p / total for p in adjusted_probabilities]  # Normalize to ensure they sum to 1

def generate_project_data(num_projects, start_year, end_year):
    Session = sessionmaker(bind=engine)
    session = Session()

    fake = Faker()

    base_status_probabilities = [0.10, 0.30, 0.30, 0.20, 0.10]  # Probabilities for the most recent year
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

    unit_ids = session.query(BusinessUnit.BusinessUnitID).all()
    unit_ids = [unit_id[0] for unit_id in unit_ids]  # Extracting unit ID from tuple

    start_date = datetime(start_year, 1, 1).date()
    end_date = datetime(end_year, 12, 31).date()

    for i in range(num_projects):
        planned_start_date = fake.date_between_dates(date_start=start_date, date_end=end_date)
        planned_end_date = planned_start_date + timedelta(days=random.randint(30, 180))

        year_diff = end_year - planned_start_date.year
        status_probabilities = adjust_probabilities(base_status_probabilities, year_diff)

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

        status = random.choices(['Not Started', 'In Progress (<50%)', 'In Progress (>50%)', 'Completed', 'On Hold/Cancelled'], 
                                weights=status_probabilities, k=1)[0]

        client_id = random.choice(client_ids)  # Use a randomly selected existing ClientID
        unit_id = random.choice(unit_ids)  # This should ideally come from an existing Unit table
        project_name = random.choice(project_names)
        project_type = random.choice(['Fixed-price', 'Time and materials'])
        
        price = round(random.uniform(10000, 150000), 2) if project_type == 'Fixed-price' else None
        credit_at = fake.date_between_dates(date_start=planned_start_date, date_end=planned_end_date)
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
            CreatedAt=credit_at,
            Progress=progress
        )

        project_data.append(project)

    session.add_all(project_data)
    session.commit()
    session.close()

def main(num_projects, start_year, end_year):
    generate_project_data(num_projects, start_year, end_year)