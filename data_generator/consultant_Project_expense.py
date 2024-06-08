import os
import pandas as pd
import numpy as np
from faker import Faker

# Define ranges for Consultant_Expense
consultant_expense_ranges = {
    "Travel": {
        "Junior Consultant": (500, 1500),
        "Consultant": (1000, 3000),
        "Senior Consultant": (2000, 5000),
        "Manager": (3000, 7000)
    }
}

# Define ranges for Project_Expense
project_expense_ranges = {
    "Supplies": {
        "Project Type A": (1000, 5000),
        "Project Type B": (2000, 8000)
    },
    "Equipment": {
        "Project Type A": (5000, 20000),
        "Project Type B": (10000, 50000)
    }
}

# Generate combined Project and Consultant expense data
def generate_combined_expense(num_records):
    fake = Faker()
    consultant_titles = ["Junior Consultant", "Consultant", "Senior Consultant", "Manager"]
    project_types = ["Project Type A", "Project Type B"]
    expense_categories = ["Travel", "Supplies", "Equipment"]

    data = []
    for i in range(num_records):
        project_consultant_expense_id = i + 1
        project_id = np.random.randint(1, 101)  # Random ProjectID between 1 and 100
        consultant_id = np.random.randint(1, 101)  # Random ConsultantID between 1 and 100
        category = np.random.choice(expense_categories)

        if category == "Travel":
            title = np.random.choice(consultant_titles)
            amount_range = consultant_expense_ranges[category][title]
            amount = np.random.uniform(amount_range[0], amount_range[1])
            data.append([
                project_consultant_expense_id, project_id, consultant_id,
                title, category, round(amount, 2)
            ])
        else:
            project_type = np.random.choice(project_types)
            amount_range = project_expense_ranges[category][project_type]
            amount = np.random.uniform(amount_range[0], amount_range[1])
            data.append([
                project_consultant_expense_id, project_id, consultant_id,
                project_type, category, round(amount, 2)
            ])

    df = pd.DataFrame(data, columns=[
        'Project_Consultant_Expense_ID', 'ProjectID', 'ConsultantID',
        'Consultant_Title/Project_Type', 'Category', 'Amount'])
    return df

# Define paths and save the data to a CSV file
def save_combined_dataframe_to_csv():
    base_path = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(base_path, 'data', 'processed')
    os.makedirs(data_path, exist_ok=True)

    combined_expense_df = generate_combined_expense(200)  # Generate 200 records for example
    combined_expense_csv = os.path.join(data_path, 'Project_Consultant_Expense.csv')
    combined_expense_df.to_csv(combined_expense_csv, index=False)

def main():
    save_combined_dataframe_to_csv()

if __name__ == "__main__":
    main()
