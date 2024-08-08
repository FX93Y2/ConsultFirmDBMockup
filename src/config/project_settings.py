from decimal import Decimal
import random

'''
Adjust a bigger team size and smaller concurrent active project per consultant
to get less nonbillable time
'''
# Maximum projects per consultant based on title
MAX_PROJECTS_PER_CONSULTANT = {
    1: 1, 2: 2, 3: 3, 
    4: 4, 5: 5, 6: 6
}

# Maximum daily working hours based on title
MAX_DAILY_HOURS_PER_TITLE = {
    1: 8.0, 2: 8.0, 3: 7.0, 
    4: 6.0, 5: 5.5, 6: 5   
}

# Minimum daily hours per project based on title
MIN_DAILY_HOURS_PER_PROJECT = {
    1: 4.0, 2: 4.0, 3: 3.0,
    4: 2.5, 5: 2.0, 6: 2.0
}



# Team composition
MAX_TEAM_SIZE = 15
MIN_TEAM_SIZE = 10
# Title distribution targets for team composition
TITLE_DISTRIBUTION_TARGETS = {
    1: 0.4,2: 0.3, 3: 0.15,
    4: 0.1, 5: 0.04, 6: 0.01
}
# Minimum number of consultants per title in a team
MIN_CONSULTANTS_PER_TITLE = {
    1: 2, 2: 2, 3: 2,
    4: 1, 5: 1, 6: 1
}



# Keep the existing MAX_DAILY_HOURS and MIN_DAILY_HOURS for backward compatibility
MAX_DAILY_HOURS = 8.0
MIN_DAILY_HOURS = 2.0
MAX_DAILY_HOURS_PER_PROJECT = 4.0
WORK_PROBABILITY = 0.95 # 95% chance of working on any given day
WORKING_DAYES = 21
AVERAGE_WORKING_HOURS_PER_DAY = 6.0
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
    1: (100, 200), 2: (150, 300), 3: (200, 400), 
    4: (250, 500), 5: (300, 600), 6: (400, 800)
}

# Title Based Billing Rates
BASE_BILLING_RATES = {1: 100, 2: 150, 3: 200, 4: 250, 5: 300, 6: 400}

# Project Type Probabilities
PROJECT_TYPES = ['Fixed', 'Time and Material']
PROJECT_TYPE_WEIGHTS = [0.5, 0.5]  # Equal probability for this example

# Project Duration Ranges (in months)
PROJECT_DURATION_RANGE =  [
        ((1, 3), 0.5), 
        ((3, 6), 0.3),
        ((6, 12), 0.2),
    ]

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

EXPENSE_CATEGORIES = {
    'Travel': {'percentage': 0.15, 'billable': True, 'range': (1000, 50000)},
    'Equipment': {'percentage': 0.10, 'billable': False, 'range': (2000, 100000)},
    'Software Licenses': {'percentage': 0.08, 'billable': True, 'range': (1000, 75000)},
    'Training': {'percentage': 0.05, 'billable': True, 'range': (500, 25000)},
    'Subcontractor Fees': {'percentage': 0.20, 'billable': True, 'range': (5000, 200000)},
    'Client Entertainment': {'percentage': 0.03, 'billable': False, 'range': (200, 10000)},
    'Office Supplies': {'percentage': 0.02, 'billable': False, 'range': (100, 5000)},
    'Telecommunication': {'percentage': 0.04, 'billable': True, 'range': (500, 15000)},
    'Legal and Professional Fees': {'percentage': 0.05, 'billable': False, 'range': (1000, 50000)},
    'Miscellaneous': {'percentage': 0.03, 'billable': False, 'range': (200, 10000)}
}