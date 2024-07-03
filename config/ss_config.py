import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ss_path = os.path.join(project_root, 'spreadsheets')
os.makedirs(ss_path, exist_ok=True)
ss_file_path = os.path.join(ss_path, 'indirect_costs.xlsx')