from datetime import date, timedelta
from sqlalchemy.orm import sessionmaker
from data_generator.create_db import Consultant, ConsultantTitleHistory, Payroll, engine

def generate_payroll():
    Session = sessionmaker(bind=engine)
    session = Session()

    # Retrieve all consultants
    consultants = session.query(Consultant).all()

    for consultant in consultants:
        # Retrieve the consultant's title history
        title_history = session.query(ConsultantTitleHistory).filter_by(ConsultantID=consultant.ConsultantID).order_by(ConsultantTitleHistory.StartDate).all()

        for i in range(len(title_history)):
            start_date = title_history[i].StartDate
            end_date = title_history[i].EndDate if title_history[i].EndDate else date.today()

            # Calculate the number of months between start and end dates
            num_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)

            # Calculate the payroll amount for each month
            for j in range(num_months):
                payroll_date = start_date + timedelta(days=j * 30)
                payroll_amount = title_history[i].Salary / 12  # Assuming monthly payroll

                # Apply bonus based on consultant's performance rating and title
                if consultant.PerformanceRating == 'High':
                    bonus_percentage = 0.1
                elif consultant.PerformanceRating == 'Average':
                    bonus_percentage = 0.05
                else:
                    bonus_percentage = 0
                payroll_amount += payroll_amount * bonus_percentage

                # Apply tax deductions based on consultant's location and salary
                # Need tax calculation logic
                tax_rate = 0.2  # Assuming a flat tax rate of 20%
                payroll_amount -= payroll_amount * tax_rate

                # Create a Payroll record
                payroll = Payroll(ConsultantID=consultant.ConsultantID, Amount=payroll_amount, EffectiveDate=payroll_date)
                session.add(payroll)

    session.commit()
    session.close()

def main():
    generate_payroll()

if __name__ == "__main__":
    main()