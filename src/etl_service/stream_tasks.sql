-- TASKS triggered by new data inserted into staging tables

-- Create the stream on STG_PAYROLL table
CREATE OR REPLACE STREAM trigger_stream ON TABLE STG_PAYROLL;

-- Task to call update_all_tables procedure, triggered by stream
CREATE OR REPLACE TASK update_all_tables_task
  WAREHOUSE = COMPUTE_WH
  WHEN SYSTEM$STREAM_HAS_DATA('trigger_stream')
AS
BEGIN
  CALL update_all_tables();
END;

-- Step 3: Create the Dependent Tasks

-- 
CREATE OR REPLACE TASK update_datamart_task
  WAREHOUSE = my_warehouse
  AFTER update_all_tables_task
AS
  CALL update_datamart();

-- 
CREATE OR REPLACE TASK procedure_3_task
  WAREHOUSE = my_warehouse
  AFTER update_datamart_task
AS
  CALL procedure_3();
