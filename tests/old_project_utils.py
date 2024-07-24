from decimal import Decimal, ROUND_HALF_UP
import random
from datetime import timedelta, date
from dateutil.relativedelta import relativedelta
from config import project_settings
from sqlalchemy import func


def round_to_nearest_thousand(value):
    return int(Decimal(value).quantize(Decimal('1000'), rounding=ROUND_HALF_UP))

def adjust_hours(planned_hours):
    if random.random() < 0.1:  # 10% chance of finishing early
        actual_hours = Decimal(planned_hours) * Decimal(random.uniform(0.8, 0.95))
    else:  # 90% chance of overrunning
        actual_hours = Decimal(planned_hours) * Decimal(random.uniform(1.05, 1.3))
    return actual_hours.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)

def calculate_hourly_cost(session, consultant, year):
    from ..src.models.db_model import Payroll
    from sqlalchemy import func
    
    payroll_data = session.query(Payroll).filter(
        Payroll.ConsultantID == consultant.ConsultantID,
        func.extract('year', Payroll.EffectiveDate) == year
    ).all()
    
    if not payroll_data:
        return 0
    
    total_salary = sum(p.Amount for p in payroll_data)
    avg_monthly_salary = total_salary / len(payroll_data)
    hourly_cost = (avg_monthly_salary * 12) / (52 * 40)  # Assuming 52 weeks and 40 hours per week
    return hourly_cost * (1 + project_settings.OVERHEAD_PERCENTAGE)

def determine_project_count(available_consultants, growth_rate):
    base_count = len(available_consultants) // random.randint(3, 5) # number of consultants per project
    adjusted_count = int(base_count * (1 + growth_rate))
    return max(5, adjusted_count)

def calculate_project_progress(project, deliverables):
    total_planned_hours = sum(d.PlannedHours for d in deliverables)
    
    if total_planned_hours == 0:
        project.Progress = 0
        return

    weighted_progress = Decimal(0)
    for deliverable in deliverables:
        weight = Decimal(deliverable.PlannedHours) / Decimal(total_planned_hours)
        weighted_progress += weight * Decimal(deliverable.Progress)

    project.Progress = int(weighted_progress.quantize(Decimal('1.'), rounding=ROUND_HALF_UP))

def get_working_days(year, month):
    start_date = date(year, month, 1)
    end_date = start_date + relativedelta(months=1) - timedelta(days=1)
    return [d for d in daterange(start_date, end_date) if d.weekday() < 5]  # Monday = 0, Friday = 4

def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(n)


