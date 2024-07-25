from src.db_model import main as create_db
from src.database_generator.generators.client import generate_clients
from src.database_generator.generators.location import generate_locations
from src.database_generator.generators.title import generate_titles
from src.database_generator.generators.business_unit import generate_business_units
from src.database_generator.generators.consultant_title_history import main as generate_consultant_title_history
from src.database_generator.generators.payroll import generate_payroll
from src.database_generator.generators.project_deliverable import generate_projects
from src.spreadsheet_generator.indirect_cost import generate_indirect_costs
from src.spreadsheet_generator.non_billable_time import generate_non_billable_time_report
from src.review_generator.Review_Generator_GPT import generate_json
import os
import time

START_YEAR = 2015
END_YEAR = 2015
INITIAL_CONSULTANTS = 5

def main():
    # Initialize DB
    create_db()

    # Generate database
    generate_locations()
    generate_business_units()
    generate_clients(5)
    generate_titles()
    generate_consultant_title_history(INITIAL_CONSULTANTS, start_year=START_YEAR, end_year=END_YEAR)
    generate_payroll(END_YEAR)
    generate_projects(START_YEAR, END_YEAR, INITIAL_CONSULTANTS)
    
    # Generate Spreadsheet
    generate_indirect_costs()

    # Generate non-billable time report
    generate_non_billable_time_report()

    # Wait for 10 seconds to ensure database creation
    # time.sleep(10)

    # Generate JSON file with reviews
    generate_json()  # Call the function to generate the JSON file

if __name__ == "__main__":
    main()