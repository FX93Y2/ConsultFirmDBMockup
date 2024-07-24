from sqlalchemy.orm import sessionmaker
from models.db_model import Title, engine

def generate_titles():
    print("Generating Titles...")
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
    print("Complete")
    