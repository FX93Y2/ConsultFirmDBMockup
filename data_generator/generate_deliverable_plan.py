import os
import pandas as pd
import numpy as np
from datetime import timedelta, date
from faker import Faker
fake = Faker()
'''
generate deliverable data and save it to a CSV file
'''
def generate_deliverable_plan(num_projects):
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_path = os.path.join(base_path, 'data', 'processed')
    csv_file_path = os.path.join(data_path, "DeliverablePlan.csv")
    os.makedirs(data_path, exist_ok=True)

    deliverable_plan = []
    np.random.seed(42)

    deliverable_name = {
        "Project Plan": 10,
        "Requirements Specification": 20,
        "Design Document": 25,
        "Code": 15,
        "Unit Test": 10,
        "System Test": 40
    }
    standard_deviations = {
        "Project Plan": 2,
        "Requirements Specification": 3,
        "Design Document": 4,
        "Code": 3,
        "Unit Test": 2,
        "System Test": 10
    }


    for i in range(num_projects):
        start_date = fake.date_between(start_date=date(2015,1,1), end_date=date(2020,12,31))
        deliverable_plan_data = []
        for name, base_duration in deliverable_name.items():
            mean_duration = base_duration
            std_dev = standard_deviations[name]
            duration = int(np.random.normal(mean_duration, std_dev))
            duration = max(1, duration)
            end_date = start_date + timedelta(days=duration - 1)
            deliverable_plan_data.append({
                "ProjectID": i + 1,
                "DeliverableName": name,
                "StartDate": start_date.strftime("%Y-%m-%d"),
                "EndDate": end_date.strftime("%Y-%m-%d"),
                "Duration(Days)": duration
            })
            start_date = end_date + timedelta(days=1)

        deliverable_plan.extend(deliverable_plan_data)

    df = pd.DataFrame(deliverable_plan)
    
    df.to_csv(csv_file_path, index=False)
    print(f"Generated deliverable plan data at {csv_file_path}")

def main(num_projects):  
    generate_deliverable_plan(num_projects)