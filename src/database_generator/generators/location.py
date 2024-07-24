from sqlalchemy.orm import sessionmaker
from models.db_model import Location, engine

def generate_locations():
    print("Generating Location Data...")
    Session = sessionmaker(bind=engine)
    session = Session()

    locations = [
        ('California', 'Los Angeles'),
        ('New York', 'New York City'),
        ('Illinois', 'Chicago'),
        ('Texas', 'Houston'),
        ('Pennsylvania', 'Philadelphia'),
        ('Arizona', 'Phoenix'),
        ('Texas', 'San Antonio'),
        ('California', 'San Diego'),
        ('Texas', 'Dallas'),
        ('California', 'San Jose'),
        ('England', 'London'),
        ('France', 'Paris'),
        ('Germany', 'Berlin'),
        ('Spain', 'Madrid'),
        ('Italy', 'Rome'),
        ('Netherlands', 'Amsterdam'),
        ('Russia', 'Moscow'),
        ('Sweden', 'Stockholm'),
        ('Poland', 'Warsaw'),
        ('Austria', 'Vienna'),
        ('Brazil', 'São Paulo'),
        ('Mexico', 'Mexico City'),
        ('Argentina', 'Buenos Aires'),
        ('Colombia', 'Bogotá'),
        ('Peru', 'Lima'),
        ('Venezuela', 'Caracas'),
        ('Chile', 'Santiago'),
        ('Ecuador', 'Quito'),
        ('Guatemala', 'Guatemala City'),
        ('Cuba', 'Havana'),
        ('China', 'Shanghai'),
        ('Japan', 'Tokyo'),
        ('India', 'Mumbai'),
        ('South Korea', 'Seoul'),
        ('Australia', 'Sydney'),
        ('Indonesia', 'Jakarta'),
        ('Philippines', 'Manila'),
        ('Thailand', 'Bangkok'),
        ('Malaysia', 'Kuala Lumpur'),
        ('Vietnam', 'Ho Chi Minh City')
    ]

    for state, city in locations:
        location = Location(State=state, City=city)
        session.add(location)

    session.commit()
    session.close()
    print("Complete")
    
