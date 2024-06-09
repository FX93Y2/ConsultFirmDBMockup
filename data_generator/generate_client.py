import os
import pandas as pd
from faker import Faker
from random_address import real_random_address

def generate_location(num_locations):
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_path = os.path.join(base_path, 'data', 'processed')
    location_csv_file_path = os.path.join(data_path, "Location.csv")

    location_data = {}

    while len(location_data) < num_locations:
        address = real_random_address()
        state = address.get('state', '')
        city = address.get('city', '')

        if city:
            location_key = (state, city)
            if location_key not in location_data:
                location_id = len(location_data) + 1
                location_data[location_key] = location_id

    location_df = pd.DataFrame([(location_id, state, city) for (state, city), location_id in location_data.items()],
                               columns=['LocationID', 'State', 'City'])
    location_df.to_csv(location_csv_file_path, index=False)

    return location_data


def generate_client(num_clients, location_data):
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_path = os.path.join(base_path, 'data', 'processed')
    client_csv_file_path = os.path.join(data_path, "Client.csv")

    fake = Faker('en_US')
    client_data = []

    for i in range(num_clients):
        location_id = fake.random_element(elements=list(location_data.values()))
        client_data.append([
            i+1,
            f"{fake.word().capitalize()} {fake.company_suffix()}",
            location_id,
            fake.phone_number(),
            fake.email()
        ])

    client_df = pd.DataFrame(client_data, columns=['ClientID', 'ClientName', 'LocationID', 'PhoneNumber', 'Email'])
    client_df.to_csv(client_csv_file_path, index=False)


def main(num_clients, num_locations):
    location_data = generate_location(num_locations)
    generate_client(num_clients, location_data)