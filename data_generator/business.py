import os
import pandas as pd
import random
import subprocess
import platform

def generate_business_unit(num_units):
    # Define the base path and the path for the CSV file
    base_path = os.getcwd()  # Use current working directory
    data_path = os.path.join(base_path, 'data', 'processed')
    csv_file_path = os.path.join(data_path, "BusinessUnit.csv")

    # Ensure the data directory exists
    os.makedirs(data_path, exist_ok=True)

    # Predefined lists for industry-specific words and locations
    industry_words = ["Digital", "Analytics", "Cloud", "Cyber", "Strategy", "Consulting", "Solutions", "Innovation", "Enterprise"]
    locations = ["North America", "Europe", "Asia Pacific", "South America", "Africa", "Middle East", "Australia"]

    # Generate mock data for BusinessUnit
    business_unit_data = []
    for i in range(num_units):
        industry_word = random.choice(industry_words)
        location = random.choice(locations)
        name = f"{industry_word} {location}"
        business_unit_data.append([i + 1, name, location])

    # Convert the list to a DataFrame
    business_unit_df = pd.DataFrame(business_unit_data, columns=['Unit_ID', 'Name', 'Location'])

    # Check if the CSV file already exists
    if os.path.exists(csv_file_path):
        # Read the existing data
        df_existing = pd.read_csv(csv_file_path)
        max_existing_id = df_existing['Unit_ID'].max()
        # Adjust the Unit_ID for the new data
        business_unit_df['Unit_ID'] = range(max_existing_id + 1, max_existing_id + 1 + len(business_unit_df))
        # Combine with existing data
        df_combined = pd.concat([df_existing, business_unit_df], ignore_index=True)
    else:
        # If no existing file, the new data is the combined data
        df_combined = business_unit_df

    # Remove duplicates based on 'Name'
    df_combined.drop_duplicates(subset=['Name'], keep='first', inplace=True)

    # Reset the Unit_ID after removing duplicates
    df_combined['Unit_ID'] = range(1, 1 + len(df_combined))

    # Save the combined data back to the CSV file
    df_combined.to_csv(csv_file_path, index=False)

    return csv_file_path

def open_file(csv_file_path):
    try:
        if platform.system() == "Darwin":  # macOS
            subprocess.call(('open', csv_file_path))
        elif platform.system() == "Windows":  # Windows
            os.startfile(csv_file_path)
        else:  # Linux
            subprocess.call(('xdg-open', csv_file_path))
        print(f"Opening file: {csv_file_path}")
    except Exception as e:
        print(f"Failed to open file: {csv_file_path}. Error: {e}")

def main(num_units):
    csv_file_path = generate_business_unit(num_units)
    open_file(csv_file_path)

if __name__ == "__main__":
    num_units = 50  # Specify the number of business units to generate
    main(num_units)
