from sqlalchemy.orm import sessionmaker # type: ignore
from data_generator.create_db import BusinessUnit, engine

def generate_business_units():
    Session = sessionmaker(bind=engine)
    session = Session()

    business_units = [
        "North America",
        "Central and South America",
        "EMEA",
        "Asia Pacific"
    ]

    for unit_name in business_units:
        business_unit = BusinessUnit(BusinessUnitName=unit_name)
        session.add(business_unit)

    session.commit()
    session.close()



def main():
    generate_business_units()
