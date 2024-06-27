import random
from datetime import date
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import sessionmaker
from data_generator.create_db import Consultant, ConsultantTitleHistory, Payroll, engine

def generate_payroll():
    Session = sessionmaker(bind=engine)
    session = Session()

    consultants = session.query(Consultant).all()

    for consultant in consultants:
        title_history = session.query(ConsultantTitleHistory).filter_by(ConsultantID=consultant.ConsultantID).order_by(ConsultantTitleHistory.StartDate).all()

        for i in range(len(title_history)):
            start_date = title_history[i].StartDate
            end_date = title_history[i].EndDate if title_history[i].EndDate else date.today()

            base_salary = title_history[i].Salary
            monthly_base = base_salary / 12  # Monthly base salary

            current_date = start_date
            while current_date <= end_date:
                # Calculate monthly payroll amount
                payroll_amount = monthly_base

                # Add some randomness (up to 5% variation)
                variation_percentage = random.uniform(-0.05, 0.05)
                payroll_amount += payroll_amount * variation_percentage

                # Round to two decimal places
                payroll_amount = round(payroll_amount, 2)

                # Create Payroll record for the month
                payroll = Payroll(ConsultantID=consultant.ConsultantID, Amount=payroll_amount, EffectiveDate=current_date)
                session.add(payroll)

                # Move to the next month
                current_date += relativedelta(months=1)
                
                # If we've moved past the end_date, break the loop
                if current_date > end_date:
                    break

    session.commit()
    session.close()

def main():
    print("Generating Payroll Data...")
    generate_payroll()
    print("Complete")

if __name__ == "__main__":
    main()