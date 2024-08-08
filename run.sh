#!/bin/bash

echo "Running main.py..."
python3 src/main.py

if [ $? -eq 0 ]; then
    echo "main.py completed successfully."
    
    # Run the Snowflake setup script
    echo "Running setup_snowflake_db.py..."
    python3 src/etl_service/setup_snowflake_db.py
    
    if [ $? -eq 0 ]; then
        echo "setup_snowflake_db.py completed successfully."
        
        echo "Running sqlite_to_snowflake.py..."
        python3 src/etl_service/sqlite_to_snowflake.py
        
        if [ $? -eq 0 ]; then
            echo "sqlite_to_snowflake.py completed successfully."
            echo "All scripts have been executed successfully."
        else
            echo "Error: sqlite_to_snowflake.py failed to execute."
            exit 1
        fi
    else
        echo "Error: setup_snowflake_db.py failed to execute."
        exit 1
    fi
else
    echo "Error: main.py failed to execute."
    exit 1
fi