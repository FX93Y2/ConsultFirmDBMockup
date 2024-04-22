import os
import pandas as pd
import numpy as np
import requests
from io import StringIO
'''
the script generates clients data and saves it to a CSV file
if the file already exists, it appends the new data to the existing data
'''
def generate_client(num_clients):
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_path = os.path.join(base_path, 'data', 'processed')
    csv_file_path = os.path.join(data_path, "Client.csv")
    os.makedirs(data_path, exist_ok=True)

    url = f"https://api.mockaroo.com/api/48294200?count={num_clients}&key=d07cf880"
    response = requests.get(url)

    if response.status_code == 200:
        df_new = pd.read_csv(StringIO(response.text))

        if os.path.exists(csv_file_path):
            df_existing = pd.read_csv(csv_file_path)
            max_existing_id = df_existing['ClientID'].max()  # Find the maximum ClientID and add 1 to start from the next ID
            df_new['ClientID'] = range(max_existing_id + 1, max_existing_id + 1 + len(df_new))
        else:
            # If no file, start IDs from 1
            df_new['ClientID'] = range(1, 1 + len(df_new))
        cols = df_new.columns.tolist()
        cols.insert(0, cols.pop(cols.index('ClientID')))  # Move 'ClientID' to the front
        df_new = df_new[cols]

        if os.path.exists(csv_file_path):
            df_existing = pd.read_csv(csv_file_path)
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        else:
            df_combined = df_new
        df_combined.to_csv(csv_file_path, index=False)

    else:
        print(f"Failed to retrieve data: Status code {response.status_code}")

def main(num_clients):
    generate_client(num_clients)


