from data_generator.create_db import main as create_db
from data_generator.gen_client import main as client
from data_generator.gen_location import main as location
from data_generator.gen_title import main as title
from data_generator.gen_busi_unit import main as busi_unit
from data_generator.gen_cons_title_hist import main as consult_title
from data_generator.gen_payroll import main as payroll
from data_generator.gen_proj_deli import main as project_deliverable

startYear = 2015
endYear = 2016


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

    # PROJECT, DELIVERABLES
    project_deliverable(startYear, endYear)





if __name__ == "__main__":
    main()