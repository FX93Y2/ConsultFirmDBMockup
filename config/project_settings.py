from decimal import Decimal
import random

'''
Adjust a bigger team size and smaller concurrent active project per consultant
to get less nonbillable time
'''
# Project Deliverable Constants
MIN_DAILY_HOURS = 2.0
MAX_DAILY_HOURS = 7.0
MAX_DAILY_HOURS_PER_PROJECT = 4.0
WORK_PROBABILITY = 1.0# 90% chance of working on any given day
WORKING_DAYES = 21
AVERAGE_WORKING_HOURS_PER_DAY = 6.0
MAX_PROJECTS_PER_CONSULTANT = 5
HIGHER_LEVEL_TITLE_THRESHOLD = 3
LOWER_LEVEL_TITLE_THRESHOLD = 2

PROJECT_MONTH_DISTRIBUTION = [3, 4, 5, 6, 7, 8, 9, 10]

# Expense Categories and Percentages
EXPENSE_CATEGORIES = {
    'Travel': 0.1,
    'Equipment': 0.05,
    'Software Licenses': 0.03,
    'Training': 0.02,
    'Miscellaneous': 0.05
}

HOURLY_RATE_RANGES = {
    1: (100, 200),  # Junior Consultant
    2: (150, 300),  # Consultant
    3: (200, 400),  # Senior Consultant
    4: (250, 500),  # Lead Consultant
    5: (300, 600),  # Project Manager
    6: (400, 800)   # Vice President
}

MAX_TEAM_SIZE = 20
MIN_TEAM_SIZE = 10 

# Title Based Billing Rates
BASE_BILLING_RATES = {1: 100, 2: 150, 3: 200, 4: 250, 5: 300, 6: 400}

# Project Type Probabilities
PROJECT_TYPES = ['Fixed', 'Time and Material']
PROJECT_TYPE_WEIGHTS = [0.5, 0.5]  # Equal probability for this example

# Project Duration Ranges (in months)
FIXED_PROJECT_DURATION_RANGE = (3, 12)
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
