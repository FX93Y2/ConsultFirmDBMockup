-- Create log table for update_all_tables procedure
CREATE TABLE LOG_TABLE_UPDATE_DB (
    LOG_ID NUMBER AUTOINCREMENT PRIMARY KEY,
    LOG_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP,
    LOG_LEVEL STRING,
    MESSAGE STRING
);

-- Create the stored procedure to update all tables from their respective staging tables
CREATE OR REPLACE PROCEDURE update_all_tables()
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION = '3.8'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'main'
AS
$$
import snowflake.snowpark.functions as F
from snowflake.snowpark import Session

def log_message(session: Session, level: str, message: str) -> None:
    session.sql(f"INSERT INTO LOG_TABLE_UPDATE_DB (LOG_LEVEL, MESSAGE) VALUES ('{level}', '{message}')").collect()

def main(session: Session) -> str:
    try:
        # Define the list of tables to update
        tables = [
            { 'target': 'TITLE', 'source': 'STG_TITLE' },
            { 'target': 'BUSINESS_UNIT', 'source': 'STG_BUSINESS_UNIT' },
            { 'target': 'CONSULTANT', 'source': 'STG_CONSULTANT' },
            { 'target': 'CONSULTANT_TITLE_HISTORY', 'source': 'STG_CONSULTANT_TITLE_HISTORY' },
            { 'target': 'PAYROLL', 'source': 'STG_PAYROLL' },
            { 'target': 'LOCATION', 'source': 'STG_LOCATION' },
            { 'target': 'CLIENT', 'source': 'STG_CLIENT' },
            { 'target': 'PROJECT', 'source': 'STG_PROJECT' },
            { 'target': 'PROJECT_TEAM', 'source': 'STG_PROJECT_TEAM' },
            { 'target': 'DELIVERABLE', 'source': 'STG_DELIVERABLE' },
            { 'target': 'PROJECT_BILLING_RATE', 'source': 'STG_PROJECT_BILLING_RATE' },
            { 'target': 'CONSULTANT_DELIVERABLE', 'source': 'STG_CONSULTANT_DELIVERABLE' },
            { 'target': 'PROJECT_EXPENSE', 'source': 'STG_PROJECT_EXPENSE' }
        ]

        # Start a transaction
        session.sql("BEGIN TRANSACTION;").collect()
        log_message(session, 'INFO', 'Transaction started')

        # Iterate through the list of tables and perform the merge operations
        for table in tables:
            target_table = table['target']
            source_table = table['source']

            # Get column names of the target table
            target_columns_df = session.sql(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{target_table}' ORDER BY ORDINAL_POSITION")
            target_columns = [row['COLUMN_NAME'] for row in target_columns_df.collect()]

            # Construct the update and insert column lists
            update_columns = ", ".join([f"target.{col} = source.{col}" for col in target_columns])
            insert_columns = ", ".join(target_columns)
            insert_values = ", ".join([f"source.{col}" for col in target_columns])

            # Construct the dynamic MERGE statement
            merge_sql = f"""
                MERGE INTO {target_table} AS target
                USING {source_table} AS source
                ON target.{target_columns[0]} = source.{target_columns[0]}
                WHEN MATCHED THEN
                    UPDATE SET {update_columns}
                WHEN NOT MATCHED THEN
                    INSERT ({insert_columns})
                    VALUES ({insert_values})
            """

            # Execute the dynamic MERGE statement
            session.sql(merge_sql).collect()
            log_message(session, 'INFO', f'Merged {source_table} into {target_table}')

            # Truncate the staging table
            session.sql(f"TRUNCATE TABLE {source_table}").collect()
            log_message(session, 'INFO', f'Truncated table {source_table}')

        # Commit the transaction if all merges are successful
        session.sql("COMMIT;").collect()
        log_message(session, 'INFO', 'Transaction committed')

        return "All tables updated successfully and staging tables truncated"
    except Exception as err:
        # Roll back the transaction if there are any errors
        session.sql("ROLLBACK;").collect()
        log_message(session, 'ERROR', f'Transaction rolled back due to error: {str(err)}')
        return f"Error updating tables: {str(err)}"
$$;

-- Call stored procedure manually, should be called in TASK
CALL update_all_tables();