import os
import pandas as pd
import random
from datetime import datetime, timedelta


def generate_deliverable(num_deliverables):
    base_path = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(base_path, 'data', 'processed')
    csv_file_path = os.path.join(data_path, "Deliverable.csv")

    os.makedirs(data_path, exist_ok=True)

    statuses = ["Pending", "In Progress", "Completed", "Delayed", "Cancelled"]
    status_weights = [0.20, 0.40, 0.30, 0.05, 0.05]

    def random_date(start, end):
        return start + timedelta(days=random.randint(0, (end - start).days))

    deliverable_data = []
    for i in range(num_deliverables):
        deliverable_id = i + 1
        project_id = random.randint(1, 100)  # Assuming ProjectID ranges from 1 to 100
        name = f"Deliverable_{deliverable_id}"
        planned_start_date = random_date(datetime(2023, 1, 1), datetime(2023, 12, 31))
        actual_start_date = planned_start_date + timedelta(days=random.randint(0, 10))
        due_date = planned_start_date + timedelta(days=random.randint(10, 100))
        submission_date = due_date + timedelta(days=random.randint(0, 10))
        status = random.choices(statuses, status_weights)[0]
        price = round(random.uniform(1000, 50000), 2)

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

    columns = ['DeliverableID', 'ProjectID', 'Name', 'PlannedStartDate', 'ActualStartDate', 'Status',
               'Price', 'DueDate', 'SubmissionDate', 'Progress', 'PlannedHours', 'ActualHours']
    deliverable_df = pd.DataFrame(deliverable_data, columns=columns)

    deliverable_df.to_csv(csv_file_path, index=False)
    print(f"Generated {num_deliverables} consultant project hours and saved to {csv_file_path}")


def main(num_deliverables):
    generate_deliverable(num_deliverables)

if __name__ == "__main__":
    main(10)
