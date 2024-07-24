import os

# Get the absolute path to the project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Define paths
db_path = os.path.join(project_root, 'output', 'database')
ss_path = os.path.join(project_root, 'output', 'spreadsheets')
json_path = os.path.join(project_root, 'output', 'json')

# Create directories if they don't exist
os.makedirs(db_path, exist_ok=True)
os.makedirs(ss_path, exist_ok=True)
os.makedirs(json_path, exist_ok=True)

# Define file paths
db_file_path = os.path.join(db_path, 'consulting_firm.db')
indirect_costs_path = os.path.join(ss_path, 'indirect_costs.xlsx')
non_billable_time_path = os.path.join(ss_path, 'non_billable_time.xlsx')
json_output_path = os.path.join(json_path, 'client_feedback.json')

# Print paths for debugging
print(f"Project root: {project_root}")
print(f"Database file path: {db_file_path}")
print(f"Indirect costs path: {indirect_costs_path}")
print(f"Non-billable time path: {non_billable_time_path}")
print(f"JSON output path: {json_output_path}")
