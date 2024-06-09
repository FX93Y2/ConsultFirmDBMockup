import os
import pandas as pd
import numpy as np
from faker import Faker
import random
from datetime import timedelta

# Define billing rate ranges as a global variable
billing_rate_ranges = {
    1: ('Junior Consultant (Time and Materials)', (100, 150)),
    2: ('Junior Consultant (Fixed Price)', (80, 120)),
    3: ('Consultant (Time and Materials)', (150, 200)),
    4: ('Consultant (Fixed Price)', (120, 180)),
    5: ('Senior Consultant (Time and Materials)', (200, 300)),
    6: ('Senior Consultant (Fixed Price)', (180, 250))
}

def generate_project_data(num_projects):
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_path = os.path.join(base_path, 'data', 'processed')
    project_csv_file_path = os.path.join(data_path, "Project.csv")
    os.makedirs(data_path, exist_ok=True)

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

        duration = (planned_end_date - planned_start_date).days
        actual_end_date = actual_start_date + timedelta(days=duration + random.randint(-10, 30))

        status = random.choices(statuses, weights=status_probabilities, k=1)[0]

        client_id = random.randint(1, 100)
        unit_id = random.randint(1, 10)
        project_name = random.choice(project_names)
        project_type = random.choice(['Fixed-price', 'Time and materials'])
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

    project_df = pd.DataFrame(project_data, columns=[
        'ProjectID', 'ClientID', 'UnitID', 'Name', 'Type', 'Status', 'PlannedStartDate', 'PlannedEndDate', 'ActualStartDate', 'ActualEndDate', 'Price', 'CreditAt', 'Progress'
    ])
    project_df.to_csv(project_csv_file_path, index=False)
    return project_df['ProjectID'].tolist()

def get_random_rate(title_id):
    title, rate_range = billing_rate_ranges[title_id]
    rate = random.uniform(rate_range[0], rate_range[1])
    return f"{title},{round(rate, 2)}"

def generate_project_billing_rate(project_ids):
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_path = os.path.join(base_path, 'data', 'processed')
    csv_file_path = os.path.join(data_path, "Project_Billing_Rate.csv")

    os.makedirs(data_path, exist_ok=True)

    billing_rate_data = []

    billing_rate_id = 1
    for project_id in project_ids:
        for title_id in billing_rate_ranges.keys():
            rate = get_random_rate(title_id)
            billing_rate_data.append([
                billing_rate_id,
                project_id,
                title_id,
                rate
            ])
            billing_rate_id += 1

    billing_rate_df = pd.DataFrame(billing_rate_data, columns=['Billing_Rate_ID', 'Project_ID', 'Title_ID', 'Rate'])

    billing_rate_df.to_csv(csv_file_path, index=False)

def main(num_projects):
    project_ids = generate_project_data(num_projects)
    generate_project_billing_rate(project_ids)

if __name__ == "__main__":
    num_projects = 100
    main(num_projects)
