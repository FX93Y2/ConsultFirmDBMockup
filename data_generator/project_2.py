import os
import pandas as pd
import numpy as np
from faker import Faker
import random
from datetime import timedelta

def generate_project_data(num_projects):
    # Set up paths
    base_path = os.path.dirname(os.path.abspath(__file__))  # Changed this line to work correctly in the current context
    data_path = os.path.join(base_path, 'data', 'processed')
    project_csv_file_path = os.path.join(data_path, "Project.csv")
    os.makedirs(data_path, exist_ok=True)

    # Initialize Faker
    fake = Faker()

    # Define the distributions
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

    for i in range(num_projects):
        # Generate random dates
        planned_start_date = fake.date_this_year()
        planned_end_date = planned_start_date + timedelta(days=random.randint(30, 180))

        # Determine the actual start date based on the delay distribution
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

        # Determine the actual end date
        duration = (planned_end_date - planned_start_date).days
        actual_end_date = actual_start_date + timedelta(days=duration + random.randint(-10, 30))

        # Assign a project status
        status = random.choices(statuses, weights=status_probabilities, k=1)[0]

        # Generate additional fields
        client_id = random.randint(1, 100)
        unit_id = random.randint(1, 10)
        project_name = random.choice(project_names)
        project_type = random.choice(['Type A', 'Type B', 'Type C'])
        price = round(random.uniform(10000, 100000), 2)
        credit_at = fake.date_between_dates(date_start=actual_start_date, date_end=actual_end_date)
        progress = random.randint(0, 100) if 'In Progress' in status else (100 if status == 'Completed' else 0)

        project_data.append([
            i+1,
            client_id,
            unit_id,
            project_name,
            project_type,
            status,
            planned_start_date,
            planned_end_date,
            actual_start_date,
            actual_end_date,
            price,
            credit_at,
            progress
        ])

    # Create DataFrame and save to CSV
    project_df = pd.DataFrame(project_data, columns=[
        'ProjectID', 'ClientID', 'UnitID', 'Name', 'Type', 'Status', 'PlannedStartDate', 'PlannedEndDate', 'ActualStartDate', 'ActualEndDate', 'Price', 'CreditAt', 'Progress'
    ])
    project_df.to_csv(project_csv_file_path, index=False)

def main(num_projects):
    generate_project_data(num_projects)

# Example usage
if __name__ == "__main__":
    main(100)
