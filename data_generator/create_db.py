import os
from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from config import db_file_path

"""if using sqlite3
def create_database(db_file_path):
    conn = sqlite3.connect(db_file_path)
    cursor = conn.cursor()

    # Location table 
    cursor.execute('''CREATE TABLE IF NOT EXISTS Location
                      (LocationID INTEGER PRIMARY KEY,
                       State TEXT,
                       City TEXT)''')
    # Client table
    cursor.execute('''CREATE TABLE IF NOT EXISTS Client
                      (ClientID INTEGER PRIMARY KEY,
                       ClientName TEXT,
                       LocationID INTEGER,
                       PhoneNumber TEXT,
                       Email TEXT,
                       FOREIGN KEY (LocationID) REFERENCES Location (LocationID))''')

    conn.commit()
    conn.close()
"""
# Using SQL Alchemy
Base = declarative_base()

class Title(Base):
    __tablename__ = 'Title'
    TitleID = Column(Integer, primary_key=True)
    Title = Column(String)

class BusinessUnit(Base):
    __tablename__ = 'BusinessUnit'
    BusinessUnitID = Column(Integer, primary_key=True)
    BusinessUnitName = Column(String)
    Consultants = relationship("Consultant", back_populates="BusinessUnit")

class Consultant(Base):
    __tablename__ = 'Consultant'
    ConsultantID = Column(String, primary_key=True)
    BusinessUnitID = Column(Integer, ForeignKey('BusinessUnit.BusinessUnitID'))
    FirstName = Column(String)
    LastName = Column(String)
    Email = Column(String)
    Contact = Column(String)
    PerformanceRating = Column(String)
    BusinessUnit = relationship("BusinessUnit", back_populates="Consultants")
    TitleHistory = relationship("ConsultantTitleHistory", back_populates="Consultant")

class ConsultantTitleHistory(Base):
    __tablename__ = 'Consultant_Title_History'
    ID = Column(Integer, primary_key=True)
    ConsultantID = Column(String, ForeignKey('Consultant.ConsultantID'))
    TitleID = Column(Integer, ForeignKey('Title.TitleID'))
    StartDate = Column(Date)
    EndDate = Column(Date, nullable=True)
    EventType = Column(String)
    Salary = Column(Integer)
    Consultant = relationship("Consultant", back_populates="TitleHistory")
    Title = relationship("Title")

class Location(Base):
    __tablename__ = 'Location'
    LocationID = Column(Integer, primary_key=True)
    State = Column(String)
    City = Column(String)

class Client(Base):
    __tablename__ = 'Client'
    ClientID = Column(Integer, primary_key=True)
    ClientName = Column(String)
    LocationID = Column(Integer, ForeignKey('Location.LocationID'))
    PhoneNumber = Column(String)
    Email = Column(String)
    Location = relationship("Location")

class Project(Base):
    __tablename__ = 'Project'
    ProjectID = Column(Integer, primary_key=True)
    ClientID = Column(Integer, ForeignKey('Client.ClientID'))
    UnitID = Column(Integer, ForeignKey('BusinessUnit.BusinessUnitID'))
    Name = Column(String)
    Type = Column(String)
    Status = Column(String)
    PlannedStartDate = Column(Date)
    PlannedEndDate = Column(Date)
    ActualStartDate = Column(Date)
    ActualEndDate = Column(Date, nullable=True)
    Price = Column(Float, nullable=True)
    CreditAt = Column(Date)
    Progress = Column(Integer)
    Client = relationship("Client")
    BusinessUnit = relationship("BusinessUnit")

class ProjectBillingRate(Base):
    __tablename__ = 'ProjectBillingRate'
    BillingRateID = Column(Integer, primary_key=True)
    ProjectID = Column(Integer, ForeignKey('Project.ProjectID'))
    TitleID = Column(Integer, ForeignKey('Title.TitleID'))
    Rate = Column(Float)
    Project = relationship("Project")
    Title = relationship("Title")

class Deliverable(Base):
    __tablename__ = 'Deliverable'
    DeliverableID = Column(Integer, primary_key=True)
    ProjectID = Column(Integer, ForeignKey('Project.ProjectID'))
    Name = Column(String)
    PlannedStartDate = Column(Date)
    ActualStartDate = Column(Date)
    Status = Column(String)
    Price = Column(Float, nullable=True)
    DueDate = Column(Date)
    SubmissionDate = Column(Date, nullable=True)
    Progress = Column(Integer)
    PlannedHours = Column(Integer)
    ActualHours = Column(Integer)
    Project = relationship("Project")

class ProjectExpense(Base):
    __tablename__ = 'ProjectExpense'
    ProjectExpenseID = Column(Integer, primary_key=True)
    ProjectID = Column(Integer, ForeignKey('Project.ProjectID'))
    DeliverableID = Column(Integer, ForeignKey('Deliverable.DeliverableID'))
    Date = Column(Date)
    Amount = Column(Float)
    Description = Column(String)
    Category = Column(String)
    Project = relationship("Project")
    Deliverable = relationship("Deliverable")

engine = create_engine(f'sqlite:///{db_file_path}')

def create_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

def main():
    create_database()

if __name__ == "__main__":
    main()