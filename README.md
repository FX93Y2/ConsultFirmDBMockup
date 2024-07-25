# Setup
run pip install -r requirements.txt
# Run Data Generation
Powersehll: python src\main.py\
Bash/Zsh: python3 src\main.py
# Run Data Migration
python src\etl_service\setup_snowflake_db.py
# Database Design:
![ERD](docs/ConsultingFirmDB.png)
