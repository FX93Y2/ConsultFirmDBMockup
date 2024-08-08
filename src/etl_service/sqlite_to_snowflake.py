import os
import sqlite3
import pandas as pd
from snowflake.connector import connect, SnowflakeConnection
from snowflake.connector.pandas_tools import write_pandas
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

# SQLite Configuration
SQLITE_DB_PATH = os.path.join("example_output", "database", "consulting_firm.db")

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
    'Title': 'TITLE',
    'BusinessUnit': 'BUSINESS_UNIT',
    'Consultant': 'CONSULTANT',
    'Consultant_Title_History': 'CONSULTANT_TITLE_HISTORY',
    'Payroll': 'PAYROLL',
    'Location': 'LOCATION',
    'Client': 'CLIENT',
    'Project': 'PROJECT',
    'ProjectTeam': 'PROJECT_TEAM',
    'Deliverable': 'DELIVERABLE',
    'ProjectBillingRate': 'PROJECT_BILLING_RATE',
    'Consultant_Deliverable': 'CONSULTANT_DELIVERABLE',
    'ProjectExpense': 'PROJECT_EXPENSE'
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

def verify_snowflake_connection(conn: SnowflakeConnection) -> bool:
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT current_version()")
        version = cursor.fetchone()[0]
        logging.info(f"Successfully connected to Snowflake. Version: {version}")
        return True
    except Exception as e:
        logging.error(f"Failed to connect to Snowflake: {str(e)}")
        return False
    
def extract_from_sqlite():
    """Extract data from SQLite database."""
    if not os.path.exists(SQLITE_DB_PATH):
        raise FileNotFoundError(f"SQLite database not found at {SQLITE_DB_PATH}")

    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [table[0] for table in cursor.fetchall() if table[0] not in EXCLUDED_TABLES]

    data = {}
    for table in tables:
        logging.info(f"Extracting data from table: {table}")
        df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
        if df.empty:
            logging.warning(f"No data found in table: {table}")
        else:
            logging.info(f"Extracted {len(df)} rows from table: {table}")
        data[table] = df

    conn.close()
    return data

def transform_data(data):
    """Transform data by renaming columns to match Snowflake schema."""
    logging.info("Transforming data (renaming columns)")
    for table, df in data.items():
        df.rename(columns=COLUMN_NAME_MAPPING, inplace=True)
    return data

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

    if not verify_snowflake_connection(conn):
        return

    cursor = conn.cursor()

    for table, df in data.items():
        snowflake_table_name = TABLE_NAME_MAPPING.get(table, table.upper())
        if df.empty:
            logging.warning(f"Skipping empty table: {snowflake_table_name}")
            continue

        try:
            logging.info(f"Loading data into table: {snowflake_table_name}")
            success, nchunks, nrows, _ = write_pandas(conn, df, snowflake_table_name)
            if success:
                logging.info(f"Successfully loaded {nrows} rows into {snowflake_table_name}")
            else:
                logging.error(f"Failed to load data into {snowflake_table_name}")
        except Exception as e:
            logging.error(f"Error loading data into {snowflake_table_name}: {str(e)}")
            raise  # Re-raise the exception to stop the process

    conn.close()

def main():
    logging.info("Starting ETL process...")
    print(f"SQLite DB path: {SQLITE_DB_PATH}")
    print(f"File exists: {os.path.exists(SQLITE_DB_PATH)}")

    try:
        logging.info("Extracting data from SQLite...")
        extracted_data = extract_from_sqlite()

        if not extracted_data:
            raise ValueError("No data extracted from SQLite")

        logging.info("Transforming data...")
        transformed_data = transform_data(extracted_data)

        logging.info("Loading data to Snowflake...")
        load_to_snowflake(transformed_data)

        logging.info("ETL process completed successfully.")
    except Exception as e:
        logging.error(f"An error occurred during the ETL process: {str(e)}")
        raise

if __name__ == "__main__":
    main()