from decimal import Decimal, ROUND_HALF_UP
import random
from datetime import timedelta
from config import project_settings

def round_to_nearest_thousand(value):
    return int(Decimal(value).quantize(Decimal('1000'), rounding=ROUND_HALF_UP))

def adjust_hours(planned_hours):
    if random.random() < 0.1:  # 10% chance of finishing early
        actual_hours = Decimal(planned_hours) * Decimal(random.uniform(0.8, 0.95))
    else:  # 90% chance of overrunning
        actual_hours = Decimal(planned_hours) * Decimal(random.uniform(1.05, 1.3))
    return actual_hours.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)

def calculate_hourly_cost(session, consultant, year):
    from ...create_db import Payroll
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
    base_count = len(available_consultants) // random.randint(3, 5)
    adjusted_count = int(base_count * (1 + growth_rate))
    return max(5, adjusted_count)

def calculate_project_progress(project, deliverables):
    total_planned_hours = sum(d.PlannedHours for d in deliverables)
    completed_hours = sum(d.PlannedHours for d in deliverables if d.Status == 'Completed')
    
    if total_planned_hours > 0:
        project.Progress = min(100, int((completed_hours / Decimal(total_planned_hours)) * 100))
    else:
        project.Progress = 100 if any(d.Status == 'Completed' for d in deliverables) else 0