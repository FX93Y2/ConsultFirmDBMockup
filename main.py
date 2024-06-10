import os
from data_generator.create_db import main as create_db
from data_generator.gen_client import main as generate_client
from data_generator.gen_location import main as generate_location
"""
test in test.py, do not change the generation work flow here
"""
def main():

    # PATH SETUP
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_path, 'database')
    db_file_path = os.path.join(db_path, "consulting_firm.db")
    os.makedirs(os.path.dirname(db_file_path), exist_ok=True)

    # DEFINE ARGS
    num_locations = 100
    num_client = 300

#======================================================START GENERATING========================================================================
    create_db(db_file_path)
    
    #LOCATION
    generate_location(num_locations, db_file_path)

    # CLIENT
    generate_client(num_client, db_file_path)

if __name__ == "__main__":
    main()