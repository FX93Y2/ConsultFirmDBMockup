import random
from datetime import timedelta, date
from sqlalchemy.orm import sessionmaker
from sqlalchemy import func
from data_generator.create_db import Project, Client, BusinessUnit, engine

def generate_project_data(num_projects, start_year, end_year):
    Session = sessionmaker(bind=engine)
    session = Session()

    # Pre-fetch all client IDs and business unit IDs
    client_ids = [client_id[0] for client_id in session.query(Client.ClientID).all()]
    unit_ids = [unit_id[0] for unit_id in session.query(BusinessUnit.BusinessUnitID).all()]

    # Project distribution
    project_distribution = {
        2016: 0.7, 2017: 0.8, 2018: 0.9, 2019: 1.0, 2020: 0.6, 2021: 0.7, 2022: 1.0, 2023: 1.1, 2024: 1.2
    }

    # Project type probabilities
    project_type_prob = {'Fixed-price': 0.6, 'Time-and-Materials': 0.4}

    # Status probabilities (adjust based on current year and project end date)
    base_status_prob = {
        'Not Started': 0.1, 'In Progress (<50%)': 0.25, 
        'In Progress (>50%)': 0.25, 'Completed': 0.2, 'On Hold/Cancelled': 0.05
    }

    project_names = [
        "Strategy Development", "Market Analysis", "Operational Efficiency",
        "Digital Transformation", "Customer Experience", "Financial Performance Review",
        "Organizational Restructuring", "Supply Chain Optimization", "IT System Integration",
        "Talent Management", "Risk Assessment", "Competitive Benchmarking",
        "Change Management", "Sustainability Plan", "Business Process Reengineering"
    ]

    projects = []
    for year in range(start_year, end_year + 1):
        num_projects_year = int(num_projects * project_distribution.get(year, 1.0) / len(range(start_year, end_year + 1)))
        
        for _ in range(num_projects_year):
            project_type = random.choices(list(project_type_prob.keys()), 
                                          weights=list(project_type_prob.values()))[0]
            
            planned_start_date = date(year, random.randint(1, 12), random.randint(1, 28))
            planned_duration = random.randint(30, 365)  # projects from 1 month to 1 year
            planned_end_date = planned_start_date + timedelta(days=planned_duration)

# Adjust status probabilities based on current date
            current_date = date(end_year, 12, 31)  # Use the end of the simulation period as current date
            time_since_start = (current_date - planned_start_date).days
            completion_factor = min(1, time_since_start / planned_duration)
            
            adjusted_status_prob = base_status_prob.copy()
            if completion_factor >= 1:
                adjusted_status_prob['Completed'] += (adjusted_status_prob['Not Started'] + 
                                                      adjusted_status_prob['In Progress (<50%)'] + 
                                                      adjusted_status_prob['In Progress (>50%)'])
                adjusted_status_prob['Not Started'] = adjusted_status_prob['In Progress (<50%)'] = adjusted_status_prob['In Progress (>50%)'] = 0
            elif completion_factor > 0.5:
                adjusted_status_prob['In Progress (>50%)'] += adjusted_status_prob['Not Started']
                adjusted_status_prob['Not Started'] = 0

            status = random.choices(list(adjusted_status_prob.keys()), 
                                    weights=list(adjusted_status_prob.values()))[0]

            actual_start_date = planned_start_date + timedelta(days=random.randint(-7, 30))
            actual_end_date = None

# Handle "On Hold" projects
            if status == 'On Hold/Cancelled':
                hold_duration = random.choices(
                    [30, 90, 180, 365, 730, 1460],  # 1 month, 3 months, 6 months, 1 year, 2 years, 4 years
                    weights=[0.4, 0.3, 0.15, 0.1, 0.04, 0.01],  # Adjust these weights as needed
                    k=1
                )[0]
                
                if hold_duration > 365:  # For long holds, adjust the project
                    planned_end_date = current_date + timedelta(days=random.randint(30, 180))
                    status = 'In Progress (<50%)'  # Assume it's been restarted
                    progress = random.randint(1, 30)  # Low progress due to restart
                else:
                    progress = 0  # No progress for shorter holds
                
                actual_end_date = None  # On hold projects don't have an actual end date
            elif status == 'Completed':
                actual_end_date = min(current_date, planned_end_date + timedelta(days=random.randint(-30, 60)))
                progress = 100
            else:
                progress = {
                    'Not Started': 0,
                    'In Progress (<50%)': random.randint(1, 49),
                    'In Progress (>50%)': random.randint(50, 99),
                }[status]

# Price and PlannedHour

            # Generate Price for Fixed-price projects
            if project_type == 'Fixed-price':
                base_price = random.uniform(500000, 10000000)  # Increased base price range
                price = base_price * (1 + (planned_duration / 365) * 0.5)  # 50% increase for year-long projects
                price = round(price, -3)  # Round to nearest thousand
            else:
                price = None

            # Generate PlannedHours
            base_hours = random.randint(100, 10000)  # Increased max hours
            planned_hours = int(base_hours * (1 + (planned_duration / 365) * 0.5))  # 50% increase for year-long projects

            project = Project(
                ClientID=random.choice(client_ids),
                UnitID=random.choice(unit_ids),
                Name=f"{random.choice(project_names)} Project",
                Type=project_type,
                Status=status,
                PlannedStartDate=planned_start_date,
                PlannedEndDate=planned_end_date,
                ActualStartDate=actual_start_date,
                ActualEndDate=actual_end_date,
                Progress=progress,
                Price=price,
                PlannedHours=planned_hours
            )
            projects.append(project)

    session.add_all(projects)
    session.commit()
    session.close()

def main(num_projects, start_year, end_year):
    generate_project_data(num_projects, start_year, end_year)