import os
from data_generator.create_db import main as create_db
from data_generator.gen_client import main as client
from data_generator.gen_location import main as location
from data_generator.gen_title import main as title
from data_generator.gen_busi_unit import main as busi_unit
from data_generator.gen_cons_title_hist import main as consult_title
from data_generator.gen_project import main as project
from data_generator.gen_proj_billing_rate import main as proj_billing_rate
from data_generator.gen_deliverable import main as deliverable
from data_generator.gen_proj_expense import main as proj_expense
from data_generator.Indirect_Cost_Excel import main as indirect_cost_excel

def main():
    #INITIALIZE DB
    create_db()

    #LOCATION
    location()

    #BUSINESS UNIT
    busi_unit()

    # CLIENT
    client(500)

    #TITLE
    title()

    #CONSULTANT AND TITLE HISTORY
    consult_title(1000, 10)

    # PROJECT
    project(num_projects=1000, start_year=2019, end_year=2024)

    #PROJECT BILLING RATE
    proj_billing_rate()

    #DELIVERABLE
    deliverable()

    #PROJECT EXPENSE
    proj_expense()

    #INDIRECT COST EXCEL
    indirect_cost_excel(
        mean_labor_cost=125000,
        stddev_labor_cost=5000,
        mean_other_expense=30000,
        stddev_other_expense=3000,
        outlier_probability=0.01,
        outlier_multiplier_range=(1.1, 1.3),
        base_inflation_rate=0.005,
        inflation_fluctuation_range=(-0.0005, 0.0005),
        seasonality_amplitude=0.05,
        dependency_factor=0.5,
        initial_cost_multiplier=2,
        random_seed=42)




if __name__ == "__main__":
    main()