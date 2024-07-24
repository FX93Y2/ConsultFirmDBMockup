from sqlalchemy.orm import sessionmaker
from models.db_model import BusinessUnit, engine

def generate_business_units():
    Session = sessionmaker(bind=engine)
    session = Session()
    print("Generating Business Units...")

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
    print("Complete")

    
