from data_generator.create_db import main as create_db
from data_generator.gen_client import main as client
from data_generator.gen_location import main as location
from data_generator.gen_title import main as title
from data_generator.gen_busi_unit import main as busi_unit
from data_generator.gen_cons_title_hist import generate_consultant_data as consult_title
from data_generator.gen_cons_title_hist import assign_business_units_to_consultants as consult_busi_unit
from data_generator.gen_project import main as project
from data_generator.gen_proj_billing_rate import main as proj_billing_rate
from data_generator.gen_deliverable import main as deliverable
from data_generator.gen_proj_expense import main as proj_expense
from data_generator.gen_payroll import main as payroll
from data_generator.Indirect_Cost_Excel import main as indirect_cost_excel

business_unit_distribution = {
    "North America": 0.6,
    "Central and South America": 0.1,
    "EMEA": 0.2,
    "Asia Pacific": 0.1
}

startYear = 2015
endYear = 2022

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

    #CONSULTANT AND TITLE HISTORY AND ASSIGNING BUSINESS UNIT
    consult_title(num_titles=1000, start_year=startYear, end_year=endYear)
    consult_busi_unit(business_unit_distribution)

    #CONSULTANT PAYROLL
    payroll()

    # PROJECT
    project(num_projects=300, start_year=startYear, end_year=endYear)

    # PROJECT BILLING RATE
    proj_billing_rate()

    # ASSIGN DELIVERABLES
    deliverable()




if __name__ == "__main__":
    main()