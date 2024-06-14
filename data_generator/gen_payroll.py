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
            payroll_amount = base_salary / 12  # Assuming monthly payroll

            # Add some randomness
            variation_percentage = random.uniform(-0.05, 0.05)
            payroll_amount += payroll_amount * variation_percentage

            # Apply bonus based on performance rating
            if consultant.PerformanceRating == 'High':
                bonus_percentage = random.uniform(0.08, 0.12)
            elif consultant.PerformanceRating == 'Average':
                bonus_percentage = random.uniform(0.03, 0.07)
                bonus_percentage = 0
            payroll_amount += payroll_amount * bonus_percentage
            payroll_amount = round(payroll_amount, 2)

            # Create a Payroll record for the start date of the title
            payroll = Payroll(ConsultantID=consultant.ConsultantID, Amount=payroll_amount, EffectiveDate=start_date)
            session.add(payroll)

            # Create Payroll records for subsequent months until the end date of the title
            current_date = start_date
            while current_date < end_date:
                current_date += relativedelta(months=1)
                if current_date <= end_date:
                    monthly_variation_percentage = random.uniform(-0.02, 0.02)
                    monthly_payroll_amount = payroll_amount + payroll_amount * monthly_variation_percentage
                    monthly_payroll_amount = round(monthly_payroll_amount, 2)
                    payroll = Payroll(ConsultantID=consultant.ConsultantID, Amount=monthly_payroll_amount, EffectiveDate=current_date)
                    session.add(payroll)

    session.commit()
    session.close()

def main():
    generate_payroll()

if __name__ == "__main__":
    main()