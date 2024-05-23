'''
older version generate client profile without using Mockaroo API
import os
import pandas as pd
from faker import Faker

def generate_client_data(num_clients):
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_path = os.path.join(base_path, 'data', 'processed')
    client_csv_file_path = os.path.join(data_path, "Client.csv")

    fake = Faker('en_US')
    client_data = []

    for i in range(num_clients):
        client_data.append([
            i+1,
            f"{fake.word().capitalize()} {fake.company_suffix()}}",
            fake.state_abbr(),
            fake.city(),
            fake.phone_number(),
            fake.email()
        ])

    client_df = pd.DataFrame(client_data, columns=['ClientID', 'ClientName', 'State', 'City', 'PhoneNumber', 'Email'])
    client_df.to_csv(client_csv_file_path, index=False)

def main(num_clients):
    generate_client_data(num_clients)
'''

import os
import pandas as pd
import numpy as np
import requests
from io import StringIO
'''
calls MockAPI to generate clients data. More realistic company name and city and state names
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
            max_existing_id = df_existing['ClientID'].max()
            # Find the maximum ClientID and add 1 to start from the next ID
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

        # Remove duplicates based on the company name
        df_combined.drop_duplicates(subset=['CompanyName'], keep='first', inplace=True)

        # Reset the ClientID after removing duplicates
        df_combined['ClientID'] = range(1, 1 + len(df_combined))

        df_combined.to_csv(csv_file_path, index=False)
    else:
        print(f"Failed to retrieve data: Status code {response.status_code}")

def main(num_clients):
    generate_client(num_clients)


