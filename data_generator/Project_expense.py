import os
import pandas as pd
import numpy as np
from faker import Faker
from datetime import datetime



def generate_project_expense(num_expenses, project_start_date, project_end_date):
    # Define the base path and the path for the CSV file
    base_path = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(base_path, 'data', 'processed')
    csv_file_path = os.path.join(data_path, "Project_Expense.csv")

    # Ensure the data directory exists
    os.makedirs(data_path, exist_ok=True)

    # Initialize Faker
    fake = Faker()

    # Convert string dates to date objects
    project_start_date = datetime.strptime(project_start_date, '%Y-%m-%d').date()
    project_end_date = datetime.strptime(project_end_date, '%Y-%m-%d').date()

    # Predefined expense categories with probabilities
    categories = ['Travel', 'Supplies', 'Equipment', 'Other']
    probabilities = [0.4, 0.3, 0.2, 0.1]

    # Generate expense data
    expense_data = []
    for i in range(num_expenses):
        project_expense_id = i + 1
        project_id = fake.random_int(min=1, max=100)  # Assuming project IDs range from 1 to 100
        deliverable_id = fake.random_int(min=1, max=100)  # Assuming deliverable IDs range from 1 to 100
        date = fake.date_between(start_date=project_start_date, end_date=project_end_date)
        amount = round(fake.random_number(digits=4, fix_len=True) / 100, 2)  # Generate a realistic expense amount
        description = fake.sentence(nb_words=6)
        category = np.random.choice(categories, p=probabilities)

        expense_data.append([project_expense_id, project_id, deliverable_id, date, amount, description, category])

    # Create a DataFrame
    expense_df = pd.DataFrame(expense_data,
                              columns=['ProjectExpenseID', 'Project_ID', 'DeliverableID', 'Date', 'Amount',
                                       'Description', 'Category'])

    # If the CSV file already exists, append the new data to it
    if os.path.exists(csv_file_path):
        existing_df = pd.read_csv(csv_file_path)
        combined_df = pd.concat([existing_df, expense_df], ignore_index=True)
    else:
        combined_df = expense_df

    # Save the combined data back to the CSV file
    combined_df.to_csv(csv_file_path, index=False)
    print(f"Data saved to {csv_file_path}")

def main(num_expenses, project_start_date, project_end_date):
    generate_project_expense(num_expenses, project_start_date, project_end_date)


if __name__ == "__main__":
    # Example usage
    num_expenses = 100  # Define the number of expenses to generate
    project_start_date = '2023-01-01'  # Define the project start date
    project_end_date = '2023-12-31'  # Define the project end date
    main(num_expenses, project_start_date, project_end_date)
