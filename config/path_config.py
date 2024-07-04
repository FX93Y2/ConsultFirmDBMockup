import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(project_root, 'output/database')
ss_path = os.path.join(project_root, 'output/spreadsheets')
json_path = os.path.join(project_root, 'output/json')

os.makedirs(db_path, exist_ok=True)
os.makedirs(ss_path, exist_ok=True)
os.makedirs(json_path, exist_ok=True)

db_file_path = os.path.join(db_path, 'consulting_firm.db')
ss_file_path = os.path.join(ss_path, 'indirect_costs.xlsx')
json_path = os.path.join(json_path, 'json_output.json')
