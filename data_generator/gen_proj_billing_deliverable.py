import os
import pandas as pd
import numpy as np
from faker import Faker
import random
from datetime import timedelta

# Generate Project start here
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

        status = random.choices(statuses, weights=status_probabilities, k=1)[0]

        client_id = random.randint(1, 100)
        unit_id = random.randint(1, 10)
        project_name = random.choice(project_names)
        project_type = random.choice(['Fixed-price', 'Time and materials'])
        
        price = round(random.uniform(10000, 100000), 2) if project_type == 'Fixed-price' else None
        credit_at = fake.date_between_dates(date_start=actual_start_date, date_end=planned_end_date)
        actual_end_date = actual_start_date + timedelta(days=(planned_end_date - planned_start_date).days + random.randint(-10, 30)) if status == 'Completed' else None
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
    return project_df

# Generate Billing Rate start here
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

# Generate Deliverable start here
def generate_deliverable(project_df):
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_path = os.path.join(base_path, 'data', 'processed')
    csv_file_path = os.path.join(data_path, "Deliverable.csv")

    os.makedirs(data_path, exist_ok=True)

    statuses = ["Pending", "In Progress", "Completed", "Delayed", "Cancelled"]
    status_weights = [0.20, 0.40, 0.30, 0.05, 0.05]

    def random_date_within(start, end):
        if start >= end:
            return start
        return start + timedelta(days=random.randint(0, (end - start).days))

    deliverable_data = []
    deliverable_id = 1

    for _, project in project_df.iterrows():
        project_id = project['ProjectID']
        num_deliverables = random.randint(1, 10) # Number of deliverables per project
        project_type = project['Type']
        #project_price = project['Price'] if pd.notnull(project['Price']) else 0
        #remaining_project_price = project_price

        project_planned_start = project['PlannedStartDate']
        project_planned_end = project['PlannedEndDate']
        project_actual_start = project['ActualStartDate']
        project_actual_end = project['ActualEndDate'] if not pd.isnull(project['ActualEndDate']) else project_planned_end

        for _ in range(num_deliverables):
            name = f"Deliverable_{deliverable_id}"
            planned_start_date = random_date_within(pd.to_datetime(project_planned_start), pd.to_datetime(project_planned_end))
            actual_start_date = random_date_within(planned_start_date, pd.to_datetime(project_actual_end))
            due_date = random_date_within(planned_start_date, pd.to_datetime(project_planned_end))
            status = random.choices(statuses, status_weights)[0]
            submission_date = random_date_within(due_date, pd.to_datetime(project_actual_end)) if status == "Completed" else None

            price = None
            if project_type == 'Fixed-price':
                price = round(random.uniform(1000, 20000), 2) # Deliverable price range
                #remaining_project_price -= price

            if status == "Pending":
                planned_hours = random.randint(10, 100)
                actual_hours = 0
                progress = 0
            elif status == "In Progress":
                planned_hours = random.randint(10, 100)
                actual_hours = random.randint(int(0.5 * planned_hours), int(0.9 * planned_hours))
                progress = random.randint(10, 90)
            elif status == "Completed":
                planned_hours = random.randint(10, 100)
                actual_hours = random.randint(int(0.9 * planned_hours), int(1.1 * planned_hours))
                progress = 100
            elif status == "Delayed" or status == "Cancelled":
                planned_hours = random.randint(10, 100)
                actual_hours = random.randint(int(0.5 * planned_hours), int(1.2 * planned_hours))
                progress = random.randint(0, 90)

            deliverable_data.append([
                deliverable_id, project_id, name, planned_start_date, actual_start_date, status, price, due_date,
                submission_date, progress, planned_hours, actual_hours
            ])
            deliverable_id += 1

    columns = ['DeliverableID', 'ProjectID', 'Name', 'PlannedStartDate', 'ActualStartDate', 'Status',
               'Price', 'DueDate', 'SubmissionDate', 'Progress', 'PlannedHours', 'ActualHours']
    deliverable_df = pd.DataFrame(deliverable_data, columns=columns)

    deliverable_df.to_csv(csv_file_path, index=False)
    print(f"Generated {len(deliverable_data)} deliverables and saved to {csv_file_path}")

def main(num_projects):
    project_df = generate_project_data(num_projects)
    project_ids = project_df['ProjectID'].tolist()
    generate_project_billing_rate(project_ids)
    generate_deliverable(project_df)

if __name__ == "__main__":
    num_projects = 100
    main(num_projects)