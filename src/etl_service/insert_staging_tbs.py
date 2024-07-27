# Insert new batch of data into Snowflake staging tables
#   if all staging tables are empty.
import os
import sqlite3
import pandas as pd
from snowflake.connector import connect
from snowflake.connector.pandas_tools import write_pandas
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

# SQLite Configuration
SQLITE_DB_PATH = r"C:\Users\putti\Documents\Projects\ConsultFirmDBMockup\example_output\database\NEW_BATCH.db"

# Snowflake Configuration
SNOWFLAKE_ACCOUNT = os.getenv('SNOWFLAKE_ACCOUNT')
SNOWFLAKE_USER = os.getenv('SNOWFLAKE_USER')
SNOWFLAKE_PASSWORD = os.getenv('SNOWFLAKE_PASSWORD')
SNOWFLAKE_WAREHOUSE = os.getenv('SNOWFLAKE_WAREHOUSE')
SNOWFLAKE_DATABASE = 'consulting_firm_db'
SNOWFLAKE_SCHEMA = 'public'

# Helper tables to exclude
EXCLUDED_TABLES = ['ConsultantCustomData', 'ProjectCustomData']

# Mapping of SQLite table names to Snowflake table names
TABLE_NAME_MAPPING = {
    'Title': 'STG_TITLE',
    'BusinessUnit': 'STG_BUSINESS_UNIT',
    'Consultant': 'STG_CONSULTANT',
    'Consultant_Title_History': 'STG_CONSULTANT_TITLE_HISTORY',
    'Payroll': 'STG_PAYROLL',
    'Location': 'STG_LOCATION',
    'Client': 'STG_CLIENT',
    'Project': 'STG_PROJECT',
    'ProjectTeam': 'STG_PROJECT_TEAM',
    'Deliverable': 'STG_DELIVERABLE',
    'ProjectBillingRate': 'STG_PROJECT_BILLING_RATE',
    'Consultant_Deliverable': 'STG_CONSULTANT_DELIVERABLE',
    'ProjectExpense': 'STG_PROJECT_EXPENSE'
}

COLUMN_NAME_MAPPING = {
    'TitleID': 'TITLEID',
    'Title': 'TITLE',
    'BusinessUnitID': 'BUSINESSUNITID',
    'BusinessUnitName': 'BUSINESSUNITNAME',
    'ConsultantID': 'CONSULTANTID',
    'BusinessUnitID': 'BUSINESSUNITID',
    'FirstName': 'FIRSTNAME',
    'LastName': 'LASTNAME',
    'Email': 'EMAIL',
    'Contact': 'CONTACT',
    'HireYear': 'HIREYEAR',
    'ID': 'ID',
    'ConsultantID': 'CONSULTANTID',
    'TitleID': 'TITLEID',
    'StartDate': 'STARTDATE',
    'EndDate': 'ENDDATE',
    'EventType': 'EVENTTYPE',
    'Salary': 'SALARY',
    'PayRollID': 'PAYROLLID',
    'ConsultantID': 'CONSULTANTID',
    'Amount': 'AMOUNT',
    'EffectiveDate': 'EFFECTIVEDATE',
    'LocationID': 'LOCATIONID',
    'State': 'STATE',
    'City': 'CITY',
    'ClientID': 'CLIENTID',
    'ClientName': 'CLIENTNAME',
    'LocationID': 'LOCATIONID',
    'PhoneNumber': 'PHONENUMBER',
    'Email': 'EMAIL',
    'ProjectID': 'PROJECTID',
    'ClientID': 'CLIENTID',
    'UnitID': 'UNITID',
    'Name': 'NAME',
    'Type': 'TYPE',
    'Status': 'STATUS',
    'PlannedStartDate': 'PLANNEDSTARTDATE',
    'PlannedEndDate': 'PLANNEDENDDATE',
    'ActualStartDate': 'ACTUALSTARTDATE',
    'ActualEndDate': 'ACTUALENDDATE',
    'Price': 'PRICE',
    'EstimatedBudget': 'ESTIMATEDBUDGET',
    'PlannedHours': 'PLANNEDHOURS',
    'ActualHours': 'ACTUALHOURS',
    'Progress': 'PROGRESS',
    'CreatedAt': 'CREATEDAT',
    'ID': 'ID',
    'ProjectID': 'PROJECTID',
    'ConsultantID': 'CONSULTANTID',
    'Role': 'ROLE',
    'StartDate': 'STARTDATE',
    'EndDate': 'ENDDATE',
    'DeliverableID': 'DELIVERABLEID',
    'ProjectID': 'PROJECTID',
    'Name': 'NAME',
    'PlannedStartDate': 'PLANNEDSTARTDATE',
    'ActualStartDate': 'ACTUALSTARTDATE',
    'Status': 'STATUS',
    'Price': 'PRICE',
    'DueDate': 'DUEDATE',
    'SubmissionDate': 'SUBMISSIONDATE',
    'InvoicedDate': 'INVOICEDDATE',
    'Progress': 'PROGRESS',
    'PlannedHours': 'PLANNEDHOURS',
    'ActualHours': 'ACTUALHOURS',
    'BillingRateID': 'BILLINGRATEID',
    'ProjectID': 'PROJECTID',
    'TitleID': 'TITLEID',
    'Rate': 'RATE',
    'ID': 'ID',
    'ConsultantID': 'CONSULTANTID',
    'DeliverableID': 'DELIVERABLEID',
    'Date': 'DATE',
    'Hours': 'HOURS',
    'ProjectExpenseID': 'PROJECTEXPENSEID',
    'ProjectID': 'PROJECTID',
    'DeliverableID': 'DELIVERABLEID',
    'Date': 'DATE',
    'Amount': 'AMOUNT',
    'Description': 'DESCRIPTION',
    'Category': 'CATEGORY',
    'IsBillable': 'ISBILLABLE',
    'ConsultantID': 'CONSULTANTID',
    'ProjectID': 'PROJECTID'
}


def extract_from_sqlite():
    """Extract data from SQLite database."""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()

    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [table[0] for table in cursor.fetchall() if table[0] not in EXCLUDED_TABLES]

    data = {}
    for table in tables:
        logging.info(f"Extracting data from table: {table}")
        data[table] = pd.read_sql_query(f"SELECT * FROM {table}", conn)

    conn.close()
    return data

def transform_data(data):
    """Transform data by renaming columns to match Snowflake schema."""
    logging.info("Transforming data (renaming columns)")
    for table, df in data.items():
        df.rename(columns=COLUMN_NAME_MAPPING, inplace=True)
        # Ensure correct data types
        if table == 'ProjectExpense':
            df['ISBILLABLE'] = df['ISBILLABLE'].astype(bool)
    return data

def check_if_all_tables_empty(cursor):
    """Check if all staging tables are empty."""
    for table in TABLE_NAME_MAPPING.values():
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        result = cursor.fetchone()
        if result[0] != 0:
            logging.error(f"Table {table} is not empty.")
            return False
    return True

def load_to_snowflake(data):
    """Load data into Snowflake."""
    conn = connect(
        account=SNOWFLAKE_ACCOUNT,
        user=SNOWFLAKE_USER,
        password=SNOWFLAKE_PASSWORD,
        warehouse=SNOWFLAKE_WAREHOUSE,
        database=SNOWFLAKE_DATABASE,
        schema=SNOWFLAKE_SCHEMA
    )

    cursor = conn.cursor()

    try:
        logging.info("Checking if all staging tables are empty")
        if check_if_all_tables_empty(cursor):
            for table, df in data.items():
                snowflake_table_name = TABLE_NAME_MAPPING.get(table, table.upper())
                try:
                    logging.info(f"Loading data into table: {snowflake_table_name}")
                    success, nchunks, nrows, _ = write_pandas(conn, df, snowflake_table_name)
                    logging.info(f"Loaded {nrows} rows into {snowflake_table_name}")
                except Exception as e:
                    logging.error(f"Error loading data into {snowflake_table_name}: {str(e)}")
        else:
            logging.error("Not all staging tables are empty. Aborting the insert operation.")
    except Exception as e:
        logging.error(f"Error during checking or loading data: {str(e)}")
    finally:
        conn.close()

def main():
    logging.info("Starting ETL process...")

    try:
        logging.info("Extracting data from SQLite...")
        extracted_data = extract_from_sqlite()

        logging.info("Transforming data...")
        transformed_data = transform_data(extracted_data)

        logging.info("Loading data to Snowflake...")
        load_to_snowflake(transformed_data)

        logging.info("ETL process completed successfully.")
    except Exception as e:
        logging.error(f"An error occurred during the ETL process: {str(e)}")

if __name__ == "__main__":
    main()