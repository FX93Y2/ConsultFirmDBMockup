from sqlalchemy.orm import sessionmaker
from data_generator.create_db import Client, Location, engine
from faker import Faker

def generate_client(num_clients):
    Session = sessionmaker(bind=engine)
    session = Session()

    fake = Faker('en_US')
    client_data = []

    locations = session.query(Location).all()

    for i in range(num_clients):
        location = fake.random_element(elements=locations)
        client = Client(
            ClientName=f"{fake.word().capitalize()} {fake.company_suffix()}",
            LocationID=location.LocationID,
            PhoneNumber=fake.phone_number(),
            Email=fake.email()
        )
        client_data.append(client)

    session.add_all(client_data)
    session.commit()
    session.close()

def main(num_clients):
    generate_client(num_clients)