# Project Deliverable Constants
MIN_DAILY_HOURS = 1.0
MAX_DAILY_HOURS = 8.0
WORK_PROBABILITY = 0.9  # 90% chance of working on any given day
MAX_DAILY_CONSULTANT_HOURS = 10.0

# Expense Categories and Percentages
EXPENSE_CATEGORIES = {
    'Travel': 0.1,
    'Equipment': 0.05,
    'Software Licenses': 0.03,
    'Training': 0.02,
    'Miscellaneous': 0.05
}

# Title Based Billing Rates
BASE_BILLING_RATES = {1: 100, 2: 150, 3: 200, 4: 250, 5: 300, 6: 400}

# Project Type Probabilities
PROJECT_TYPES = ['Fixed', 'Time and Material']
PROJECT_TYPE_WEIGHTS = [0.5, 0.5]  # Equal probability for this example

# Project Duration Ranges (in months)
FIXED_PROJECT_DURATION_RANGE = (3, 24)
TIME_MATERIAL_PROJECT_DURATION_RANGE = (1, 36)

# Deliverable Count Range
DELIVERABLE_COUNT_RANGE = (3, 7)

# Profit Margin Range for Fixed Projects
PROFIT_MARGIN_RANGE = (0.15, 0.30)

# Hourly Cost Overhead Percentage
OVERHEAD_PERCENTAGE = 0.3

# Working Hours per Month
WORKING_HOURS_PER_MONTH = 160

