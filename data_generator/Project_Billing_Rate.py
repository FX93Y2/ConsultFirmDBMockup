import os
import pandas as pd
import random

billing_rate_ranges = {
    1: ('Junior Consultant (Time and Materials)', (100, 150)),
    2: ('Junior Consultant (Fixed Price)', (80, 120)),
    3: ('Consultant (Time and Materials)', (150, 200)),
    4: ('Consultant (Fixed Price)', (120, 180)),
    5: ('Senior Consultant (Time and Materials)', (200, 300)),
    6: ('Senior Consultant (Fixed Price)', (180, 250))
}

def get_random_rate(title_id):
    title, rate_range = billing_rate_ranges[title_id]
    rate = random.uniform(rate_range[0], rate_range[1])
    return f"{title},{round(rate, 2)}"

def generate_project_billing_rate(num_entries, project_ids):
    # Define the base path and the path for the CSV file
    base_path = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(base_path, 'data', 'processed')
    csv_file_path = os.path.join(data_path, "Project_Billing_Rate.csv")

    os.makedirs(data_path, exist_ok=True)

    billing_rate_data = []

    for i in range(num_entries):
        project_id = random.choice(project_ids)
        title_id = random.randint(1, len(billing_rate_ranges))  # Randomly select a title ID
        rate = get_random_rate(title_id)
        billing_rate_data.append([
            i + 1,
            project_id,
            title_id,
            rate
        ])

    billing_rate_df = pd.DataFrame(billing_rate_data, columns=['Billing_Rate_ID', 'Project_ID', 'Title_ID', 'Rate'])

    billing_rate_df.to_csv(csv_file_path, index=False)

def main(num_entries, project_ids):
    generate_project_billing_rate(num_entries, project_ids)

if __name__ == "__main__":
    # Define example project IDs for testing purposes
    project_ids = [1, 2, 3, 4, 5]  # Replace with actual project IDs
    num_entries = 100  # Define the number of entries to generate
    main(num_entries, project_ids)
