import os
from data_generator.create_db import main as create_db
from data_generator.gen_client import main as client
from data_generator.gen_location import main as location
from data_generator.gen_title import main as title
from data_generator.gen_busi_unit import main as busi_unit
from data_generator.gen_cons_title_hist import main as consult_title
from data_generator.gen_project import main as project
from data_generator.gen_billing_rate import main as proj_billing_rate

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
    project(100)

    #PROJECT BILLING RATE
    proj_billing_rate()




if __name__ == "__main__":
    main()