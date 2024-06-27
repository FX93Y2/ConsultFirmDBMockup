from data_generator.create_db import main as create_db
from data_generator.gen_client import main as client
from data_generator.gen_location import main as location
from data_generator.gen_title import main as title
from data_generator.gen_busi_unit import main as busi_unit
from data_generator.gen_cons_title_hist import main as consult_title
from data_generator.gen_project import main as project
from data_generator.gen_deliverable import main as deliverable
from data_generator.gen_payroll import generate_payroll as payroll
from data_generator.assign_proj import main as assign_proj
from data_generator.assign_timesheet import main as assign_timesheet

startYear = 2015
endYear = 2024


def main():
    #INITIALIZE DB
    create_db()

    #LOCATION
    location()

    #BUSINESS UNIT
    busi_unit()

    # CLIENT
    client(800)

    #TITLE
    title()

    #CONSULTANT AND TITLE HISTORY AND ASSIGNING BUSINESS UNIT
    consult_title(initial_num_titles=200, start_year=startYear, end_year=endYear)

    #CONSULTANT PAYROLL
    payroll()

    # PROJECT
    #project(num_projects=1000, start_year=startYear, end_year=endYear)

    # DELIVERABLES
    #deliverable()

    # DISTRIBUTE PROJECTS
    #assign_proj()

    # CREATING TIMESHEET
    #assign_timesheet()




if __name__ == "__main__":
    main()