import os
import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import sessionmaker
from data_generator.create_db import Project, BusinessUnit, engine

def generate_indirect_costs(mean_labor_cost=125000, stddev_labor_cost=5000, mean_other_expense=30000, stddev_other_expense=3000, 
                            outlier_probability=0.01, outlier_multiplier_range=(1.1, 1.3), base_inflation_rate=0.005, 
                            inflation_fluctuation_range=(-0.0005, 0.0005), seasonality_amplitude=0.05, 
                            dependency_factor=0.5, initial_cost_multiplier=2, random_seed=42, output_file="Indirect_Costs.xlsx"):
    # Set the seed for reproducibility
    random.seed(random_seed)
    np.random.seed(random_seed)

    Session = sessionmaker(bind=engine)
    session = Session()

    # Get the earliest and most recent dates from the Project table
    earliest_date = session.query(Project.PlannedStartDate).order_by(Project.PlannedStartDate).first()[0]
    most_recent_date = session.query(Project.PlannedEndDate).order_by(Project.PlannedEndDate.desc()).first()[0]

    # Define the months based on the project dates
    months = pd.date_range(start=earliest_date, end=most_recent_date, freq='M').strftime("%b-%y").tolist()

    # Get all business unit IDs
    business_units = session.query(BusinessUnit.BusinessUnitID).all()
    business_units = [unit[0] for unit in business_units]

    # Function to calculate seasonality factor
    def seasonality(month_index):
        return 1 + seasonality_amplitude * np.sin(1 * np.pi * month_index / 12)

    # Generate sample data with inflation, outliers, seasonality, and month-to-month dependency
    data = []
    current_inflation_rate = base_inflation_rate

    previous_labor_costs = {unit: mean_labor_cost for unit in business_units}
    previous_other_expenses = {unit: mean_other_expense for unit in business_units}

    for i, month in enumerate(months):
        # Apply a fluctuating inflation rate
        inflation_adjustment = random.uniform(*inflation_fluctuation_range)
        current_inflation_rate += inflation_adjustment

        # Adjust mean costs with current inflation rate
        adjusted_mean_labor_cost = mean_labor_cost * (1 + current_inflation_rate)
        adjusted_mean_other_expense = mean_other_expense * (1 + current_inflation_rate)

        # Calculate seasonality factor
        seasonality_factor = seasonality(i)

        for unit in business_units:
            labor_costs = np.random.normal(adjusted_mean_labor_cost, stddev_labor_cost)
            other_expenses = np.random.normal(adjusted_mean_other_expense, stddev_other_expense)

            # Ensure costs are not negative
            labor_costs = max(labor_costs, 0)
            other_expenses = max(other_expenses, 0)

            # Apply seasonality adjustment
            labor_costs *= seasonality_factor
            other_expenses *= seasonality_factor

            # Apply month-to-month dependency
            if i == 0:
                labor_costs *= initial_cost_multiplier  # Apply initial cost multiplier for the first month
                other_expenses *= initial_cost_multiplier
            else:
                labor_costs += dependency_factor * previous_labor_costs[unit]
                other_expenses += dependency_factor * previous_other_expenses[unit]

            # Apply a chance of an outlier
            if random.random() < outlier_probability:
                outlier_multiplier = random.uniform(*outlier_multiplier_range)
                labor_costs *= outlier_multiplier
                other_expenses *= outlier_multiplier

            labor_costs = round(labor_costs, 2)
            other_expenses = round(other_expenses, 2)
            total_costs = labor_costs + other_expenses

            data.append([month, unit, labor_costs, other_expenses, total_costs])

            # Update previous costs for next month's dependency
            previous_labor_costs[unit] = labor_costs
            previous_other_expenses[unit] = other_expenses

    # Create DataFrame
    df = pd.DataFrame(data, columns=["Month", "Business Unit ID", "Non-proj Labor Costs", "Other Expense Costs", "Total Indirect Costs"])

    # Define the base path and the path for the Excel file
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_path = os.path.join(base_path, 'data')
    os.makedirs(data_path, exist_ok=True)
    excel_file_path = os.path.join(data_path, output_file)

    # Save DataFrame to Excel
    df.to_excel(excel_file_path, index=False)
    print(f"Data saved to {excel_file_path}")

    session.close()

def main(mean_labor_cost=125000, stddev_labor_cost=5000, mean_other_expense=30000, stddev_other_expense=3000, 
                            outlier_probability=0.01, outlier_multiplier_range=(1.1, 1.3), base_inflation_rate=0.005, 
                            inflation_fluctuation_range=(-0.0005, 0.0005), seasonality_amplitude=0.05, 
                            dependency_factor=0.5, initial_cost_multiplier=2, random_seed=42, output_file="Indirect_Costs.xlsx"):
    generate_indirect_costs(mean_labor_cost=125000, stddev_labor_cost=5000, mean_other_expense=30000, stddev_other_expense=3000, 
                            outlier_probability=0.01, outlier_multiplier_range=(1.1, 1.3), base_inflation_rate=0.005, 
                            inflation_fluctuation_range=(-0.0005, 0.0005), seasonality_amplitude=0.05, 
                            dependency_factor=0.5, initial_cost_multiplier=2, random_seed=42, output_file="Indirect_Costs.xlsx")