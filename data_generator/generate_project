import os
import pandas as pd
import numpy as np
from faker import Faker
import random
from datetime import timedelta

def generate_project_data(num_projects):
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_path = os.path.join(base_path, 'data', 'processed')
    project_csv_file_path = os.path.join(data_path, "Project.csv")
    os.makedirs(data_path, exist_ok=True)

    fake = Faker()

    statuses = ['Not Started', 'In Progress (<50%)', 'In Progress (>50%)', 'Completed', 'On Hold/Cancelled']
    status_probabilities = [0.10, 0.30, 0.30, 0.20, 0.10]

    start_date_delay_probabilities = [0.60, 0.30, 0.10]

    project_data = []

    for i in range(num_projects):
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

        project_data.append([
            i+1,
            fake.bs().title(),
            status,
            planned_start_date,
            planned_end_date,
            actual_start_date,
            actual_end_date
        ])

    project_df = pd.DataFrame(project_data, columns=[
        'ProjectID', 'ProjectName', 'Status', 'PlannedStartDate', 'PlannedEndDate', 'ActualStartDate', 'ActualEndDate'
    ])
    project_df.to_csv(project_csv_file_path, index=False)

def main(num_projects):
    generate_project_data(num_projects)
