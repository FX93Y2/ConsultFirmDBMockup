import os

base_path = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(base_path, 'database')
os.makedirs(db_path, exist_ok=True)
db_file_path = os.path.join(db_path, 'consulting_firm.db')