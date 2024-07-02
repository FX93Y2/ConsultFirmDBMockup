import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(project_root, 'database')
os.makedirs(db_path, exist_ok=True)
db_file_path = os.path.join(db_path, 'consulting_firm.db')