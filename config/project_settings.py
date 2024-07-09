from decimal import Decimal
import random

# Project Deliverable Constants
MIN_DAILY_HOURS = 1.0
MAX_DAILY_HOURS = 8.0
WORK_PROBABILITY = 0.9  # 90% chance of working on any given day
MAX_DAILY_CONSULTANT_HOURS = 10.0
AVERAGE_WORKING_HOURS_PER_DAY = 8.0

# Expense Categories and Percentages
EXPENSE_CATEGORIES = {
    'Travel': 0.1,
    'Equipment': 0.05,
    'Software Licenses': 0.03,
    'Training': 0.02,
    'Miscellaneous': 0.05
}

TARGET_TEAM_SIZE = random.randint(10, 15)

PROJECT_GROWTH_RATE = 0.1  # 10% growth rate

# Title Based Billing Rates
BASE_BILLING_RATES = {1: 100, 2: 150, 3: 200, 4: 250, 5: 300, 6: 400}

# Project Type Probabilities
PROJECT_TYPES = ['Fixed', 'Time and Material']
PROJECT_TYPE_WEIGHTS = [0.5, 0.5]  # Equal probability for this example

# Project Duration Ranges (in months)
FIXED_PROJECT_DURATION_RANGE = (3, 24)
TIME_MATERIAL_PROJECT_DURATION_RANGE = (1, 12)

# Deliverable Count Range
DELIVERABLE_COUNT_RANGE = (3, 7)

# Profit Margin Range for Fixed Projects
PROFIT_MARGIN_RANGE = (0.15, 0.30)

# Hourly Cost Overhead Percentage
OVERHEAD_PERCENTAGE = 0.3

# Working Hours per Month
WORKING_HOURS_PER_MONTH = 160

# Estmated Budgets for Time and Material Projects
ESTIMATED_BUDGET_FACTORS = Decimal(random.uniform(1.1, 1.3))
