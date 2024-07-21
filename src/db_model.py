from sqlalchemy import create_engine, Column, Integer, String, Date, DateTime, ForeignKey, Float, Boolean, PickleType
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.ext.mutable import MutableDict
from config.path_config import db_file_path
from datetime import datetime

Base = declarative_base()

engine = create_engine(f'sqlite:///{db_file_path}')

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
    HireYear = Column(Integer)
    
    BusinessUnit = relationship("BusinessUnit", back_populates="Consultants")
    TitleHistory = relationship("ConsultantTitleHistory", back_populates="Consultant")
    
    _custom_data = Column(MutableDict.as_mutable(PickleType), default={})

    @property
    def custom_data(self):
        return self._custom_data

    @custom_data.setter
    def custom_data(self, value):
        self._custom_data = value

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

class Payroll(Base):
    __tablename__ = 'Payroll'
    PayRollID = Column(Integer, primary_key=True)
    ConsultantID = Column(String, ForeignKey('Consultant.ConsultantID'))
    Amount = Column(Float)
    EffectiveDate = Column(Date)
    Consultant = relationship("Consultant")

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
    EstimatedBudget = Column(Float, nullable=True)
    PlannedHours = Column(Integer, nullable=True)
    ActualHours = Column(Float, nullable=True)
    Progress = Column(Integer, nullable=True)
    CreatedAt = Column(DateTime, default=datetime.utcnow)
    Client = relationship("Client")
    BusinessUnit = relationship("BusinessUnit")
    Deliverables = relationship("Deliverable", back_populates="Project")
    Team = relationship("ProjectTeam", back_populates="Project")
    
    _custom_data = Column(MutableDict.as_mutable(PickleType), default={})

    @property
    def custom_data(self):
        return self._custom_data

    @custom_data.setter
    def custom_data(self, value):
        self._custom_data = value

class ProjectTeam(Base):
    __tablename__ = 'ProjectTeam'
    ID = Column(Integer, primary_key=True)
    ProjectID = Column(Integer, ForeignKey('Project.ProjectID'))
    ConsultantID = Column(String, ForeignKey('Consultant.ConsultantID'))
    Role = Column(String)
    StartDate = Column(Date)
    EndDate = Column(Date, nullable=True)
    Project = relationship("Project", back_populates="Team")
    Consultant = relationship("Consultant")

class Deliverable(Base):
    __tablename__ = 'Deliverable'
    DeliverableID = Column(Integer, primary_key=True)
    ProjectID = Column(Integer, ForeignKey('Project.ProjectID'))
    Name = Column(String)
    PlannedStartDate = Column(Date)
    ActualStartDate = Column(Date, nullable=True)
    Status = Column(String)
    Price = Column(Float, nullable=True)
    DueDate = Column(Date)
    SubmissionDate = Column(Date, nullable=True)
    InvoicedDate = Column(Date, nullable=True)
    Progress = Column(Integer, nullable=True)
    PlannedHours = Column(Float)
    ActualHours = Column(Float, nullable=True)
    Project = relationship("Project", back_populates="Deliverables")
    ConsultantDeliverables = relationship("ConsultantDeliverable", back_populates="Deliverable")

class ProjectBillingRate(Base):
    __tablename__ = 'ProjectBillingRate'
    BillingRateID = Column(Integer, primary_key=True)
    ProjectID = Column(Integer, ForeignKey('Project.ProjectID'))
    TitleID = Column(Integer, ForeignKey('Title.TitleID'))
    Rate = Column(Float)
    Project = relationship("Project")
    Title = relationship("Title")

class ConsultantDeliverable(Base):
    __tablename__ = 'Consultant_Deliverable'
    ID = Column(Integer, primary_key=True)
    ConsultantID = Column(String, ForeignKey('Consultant.ConsultantID'))
    DeliverableID = Column(Integer, ForeignKey('Deliverable.DeliverableID'))
    Date = Column(Date)
    Hours = Column(Integer)
    Consultant = relationship("Consultant")
    Deliverable = relationship("Deliverable")

class ProjectExpense(Base):
    __tablename__ = 'ProjectExpense'
    ProjectExpenseID = Column(Integer, primary_key=True)
    ProjectID = Column(Integer, ForeignKey('Project.ProjectID'))
    DeliverableID = Column(Integer, ForeignKey('Deliverable.DeliverableID'))
    Date = Column(Date)
    Amount = Column(Float)
    Description = Column(String)
    Category = Column(String)
    IsBillable = Column(Boolean)
    Project = relationship("Project")
    Deliverable = relationship("Deliverable")

def create_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

def main():
    print("Creating Database...")
    create_database()
    print("Complete")

if __name__ == "__main__":
    main()