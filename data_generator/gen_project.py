import random
from datetime import timedelta, date
from sqlalchemy.orm import sessionmaker
from sqlalchemy import func, or_
from data_generator.create_db import Project, Client, ConsultantTitleHistory, BusinessUnit, engine

def generate_project_data(num_projects, start_year, end_year):
    Session = sessionmaker(bind=engine)
    session = Session()

    # Initializing distributions
    project_distribution = {
        2019: 0.8,  # Pre-COVID, normal project volume
        2020: 0.6,  # COVID outbreak
        2021: 0.7, 
        2022: 1.0,  # Back to normal project volume
        2023: 1.1,  # Thriving period, increased project volume
        2024: 1.2
    }

    # Adjust the project distribution based on the specified start and end years
    project_distribution = {year: project_distribution.get(year, 1.0) for year in range(start_year, end_year + 1)}
    
    # Calculate projects per year based on the distribution
    projects_per_year = {}
    total_projects = 0
    for year in range(start_year, end_year + 1):
        projects_per_year[year] = int(num_projects * project_distribution[year])
        total_projects += projects_per_year[year]

    # Adjust the number of projects per year to match the total num_projects
    for year in projects_per_year:
        projects_per_year[year] = int(projects_per_year[year] * num_projects / total_projects)

    base_status_probabilities = [0.10, 0.30, 0.30, 0.20, 0.10]
    start_date_delay_probabilities = [0.60, 0.30, 0.10]
    project_names = [
        "Strategy Development Plan", "Market Analysis Report", "Operational Efficiency Project",
        "Digital Transformation Initiative", "Customer Experience Improvement", "Financial Performance Review",
        "Organizational Restructuring", "Supply Chain Optimization", "IT System Integration",
        "Talent Management Program", "Risk Management Assessment", "Competitive Benchmarking Study",
        "Change Management Strategy", "Sustainability Plan", "Business Process Reengineering"
    ]

    # Generation rules
    project_data = []

    # Query all client IDs and unit IDs
    client_ids = [client_id[0] for client_id in session.query(Client.ClientID).all()]
    unit_ids = [unit_id[0] for unit_id in session.query(BusinessUnit.BusinessUnitID).all()]

    # Generate projects for each year
    for year in range(start_year, end_year + 1):
        num_projects_year = projects_per_year.get(year, 0)
        for _ in range(num_projects_year):
            planned_start_date = date(year, 1, 1) + timedelta(days=random.randint(0, 364))
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

            current_year = end_year
            years_since_planned_end = current_year - planned_end_date.year

            if years_since_planned_end > 0:
                completion_probability = min(0.95, years_since_planned_end * 0.2)
                cancellation_probability = 0.05
                status_probabilities = [0.0, 0.0, 0.0, completion_probability, cancellation_probability]
            else:
                status_probabilities = base_status_probabilities

            status = random.choices(
                ['Not Started', 'In Progress (<50%)', 'In Progress (>50%)', 'Completed', 'On Hold/Cancelled'],
                weights=status_probabilities,
                k=1
            )[0]

            client_id = random.choice(client_ids)
            unit_id = random.choice(unit_ids)
            project_name = random.choice(project_names)
            project_type = random.choice(['Fixed-price', 'Time-and-Materials'])

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
                Progress=progress
            )
            project_data.append(project)

    session.add_all(project_data)
    session.commit()
    session.close()

def main(num_projects, start_year, end_year):
    generate_project_data(num_projects, start_year, end_year)