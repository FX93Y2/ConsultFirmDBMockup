import os
import pandas as pd
from faker import Faker
from random_address import real_random_address

def generate_client_and_location(num_clients):
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_path = os.path.join(base_path, 'data', 'processed')
    client_csv_file_path = os.path.join(data_path, "Client.csv")
    location_csv_file_path = os.path.join(data_path, "Location.csv")

    fake = Faker('en_US')
    client_data = []
    location_data = []
    location_ids = []

    for i in range(num_clients):
        address = real_random_address()
        location_data.append([
            i+1,
            address['state'],
            address['city']
        ])
        location_ids.append(i+1)

    location_df = pd.DataFrame(location_data, columns=['LocationID', 'State', 'City'])
    location_df.to_csv(location_csv_file_path, index=False)

    for i in range(num_clients):
        client_data.append([
            i+1,
            f"{fake.word().capitalize()} {fake.company_suffix()}",
            pd.Series(location_ids).sample().values[0],
            fake.phone_number(),
            fake.email()
        ])

    client_df = pd.DataFrame(client_data, columns=['ClientID', 'ClientName', 'LocationID', 'PhoneNumber', 'Email'])
    client_df.to_csv(client_csv_file_path, index=False)

def main(num_clients):
    generate_client_and_location(num_clients)


