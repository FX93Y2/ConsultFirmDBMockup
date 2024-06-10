from random_address import real_random_address
from sqlalchemy.orm import sessionmaker
from data_generator.create_db import Location, engine

def generate_location(num_locations):
    Session = sessionmaker(bind=engine)
    session = Session()

    location_data = {}

    while len(location_data) < num_locations:
        address = real_random_address()
        state = address.get('state', '')
        city = address.get('city', '')

        if city:
            location_key = (state, city)
            if location_key not in location_data:
                location = Location(State=state, City=city)
                session.add(location)
                location_data[location_key] = location

    session.commit()
    session.close()

def main(num_locations):
    generate_location(num_locations)

