import os
import pandas as pd
import random
from datetime import datetime

# Define the salary for each title
title_salaries = {
    'Junior Consultant': 60000,
    'Consultant': 80000,
    'Senior Consultant': 100000,
    'Manager': 120000,
    'Senior Manager': 140000,
}

# Example states for tax calculation
states = ['California', 'Texas', 'New York', 'Florida', 'Illinois']

# Function to calculate the amount
def calculate_amount(title, base_salary, bonus, overtime_hours):
    pay_periods_per_year = 12  # Monthly pay
    overtime_rate = 1.5
    tax_rate = 0.25  # Example tax rate

    monthly_salary = base_salary / pay_periods_per_year
    overtime_pay = overtime_hours * (base_salary / (40 * 4)) * overtime_rate
    gross_pay = monthly_salary + bonus + overtime_pay
    tax_deductions = gross_pay * tax_rate
    net_pay = gross_pay - tax_deductions

    return round(net_pay, 2)

# Function to generate payroll data
def generate_payroll(num_records):
    # Define the base path and the path for the CSV file
    base_path = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(base_path, 'data', 'processed')
    payroll_csv_file_path = os.path.join(data_path, "Payroll.csv")
    os.makedirs(data_path, exist_ok=True)

    # Generate random consultants
    consultants = []
    for i in range(1, 101):
        consultants.append({
            'ConsultantID': i,
            'Title': random.choice(list(title_salaries.keys())),
            'State': random.choice(states)
        })
    consultants_df = pd.DataFrame(consultants)

    # Generate random project hours and deliverables
    project_hours = []
    deliverables = []
    for i in range(1, 101):
        project_hours.append({
            'ConsultantID': i,
            'OvertimeHours': random.uniform(0, 20)
        })
        deliverables.append({
            'ConsultantID': i,
            'OvertimeHours': random.uniform(0, 20)
        })
    project_hours_df = pd.DataFrame(project_hours)
    deliverables_df = pd.DataFrame(deliverables)

    payroll_data = []

    for _ in range(num_records):
        consultant = consultants_df.sample().iloc[0]
        consultant_id = consultant['ConsultantID']
        title = consultant['Title']
        base_salary = title_salaries.get(title, 80000)  # Default salary if title not found

        # Calculate bonus randomly based on title and performance rating
        bonus = random.choice([0, 500, 1000, 1500, 2000])

        # Calculate overtime hours from project hours and deliverables
        overtime_hours = project_hours_df[project_hours_df['ConsultantID'] == consultant_id]['OvertimeHours'].sum()
        overtime_hours += deliverables_df[deliverables_df['ConsultantID'] == consultant_id]['OvertimeHours'].sum()

        amount = calculate_amount(title, base_salary, bonus, overtime_hours)

        payroll_data.append([
            len(payroll_data) + 1,
            consultant_id,
            datetime.now().strftime("%Y-%m-%d"),
            amount
        ])

    payroll_df = pd.DataFrame(payroll_data, columns=['Payroll_ID', 'Consultant_ID', 'EffectiveDate', 'Amount'])

    if os.path.exists(payroll_csv_file_path):
        payroll_df_existing = pd.read_csv(payroll_csv_file_path)
        payroll_df_combined = pd.concat([payroll_df_existing, payroll_df], ignore_index=True)
    else:
        payroll_df_combined = payroll_df

    payroll_df_combined.to_csv(payroll_csv_file_path, index=False)

def main(num_records):
    generate_payroll(num_records)

if __name__ == "__main__":
    main(10)
