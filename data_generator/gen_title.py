from sqlalchemy.orm import sessionmaker # type: ignore
from .create_db import Title, engine

def generate_titles():
    Session = sessionmaker(bind=engine)
    session = Session()

    titles = [
        Title(TitleID=1, Title='Junior Consultant'),
        Title(TitleID=2, Title='Consultant'),
        Title(TitleID=3, Title='Senior Consultant'),
        Title(TitleID=4, Title='Lead Consultant'),
        Title(TitleID=5, Title='Project Manager'),
        Title(TitleID=6, Title='Vice President')
    ]

    session.add_all(titles)
    session.commit()
    session.close()

def main():
    print("Generating Titles...")
    generate_titles()
    print("Complete")