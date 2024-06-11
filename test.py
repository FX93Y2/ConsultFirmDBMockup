import os
from data_generator.create_db import main as create_db
from data_generator.gen_client import main as client
from data_generator.gen_location import main as location
from data_generator.gen_title import main as title
from data_generator.gen_cons_title_hist import main as consult_title
from data_generator.gen_project import main as project

def main():
    #INITIALIZE DB
    create_db()
    
    #LOCATION
    location(100)

    # CLIENT
    client(300)

    #TITLE
    title()

    #CONSULTANT AND TITLE HISTORY
    consult_title(1000, 10)

    # PROJECT
    project(100)


if __name__ == "__main__":
    main()