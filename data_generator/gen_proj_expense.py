import random
from faker import Faker
from sqlalchemy.orm import sessionmaker
from data_generator.create_db import Project, Deliverable, ProjectExpense, engine

def generate_project_expense():
    Session = sessionmaker(bind=engine)
    session = Session()

    fake = Faker()

    categories = ['Travel', 'Supplies', 'Equipment', 'Other']
    probabilities = [0.4, 0.3, 0.2, 0.1]

    expense_data = []

    # Query all deliverables and their associated projects
    deliverables = session.query(Deliverable).all()

    for deliverable in deliverables:
        project_id = deliverable.ProjectID
        deliverable_id = deliverable.DeliverableID
        start_date = deliverable.ActualStartDate
        end_date = deliverable.SubmissionDate

        if start_date and end_date:
            date = fake.date_between(start_date=start_date, end_date=end_date)
        else:
            date = fake.date_this_year()

        amount = round(fake.random_number(digits=4, fix_len=True) / 100, 2)  # Generate a realistic expense amount
        category = random.choices(categories, weights=probabilities)[0]

        expense = ProjectExpense(
            ProjectID=project_id,
            DeliverableID=deliverable_id,
            Date=date,
            Amount=amount,
            Category=category
        )

        expense_data.append(expense)

    session.add_all(expense_data)
    session.commit()
    session.close()

def main():
    generate_project_expense()