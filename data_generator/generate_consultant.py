import os
import pandas as pd
import random
from faker import Faker
from datetime import timedelta, date
'''
generate consultant and title history and split it into two datasets
'''
def generate_consultant_data(num_consultants):
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_path = os.path.join(base_path, 'data', 'processed')
    consultant_csv_file_path = os.path.join(data_path, "Consultant.csv")
    title_history_csv_file_path = os.path.join(data_path, "Consultant_Title_History.csv")
    os.makedirs(data_path, exist_ok=True)

    fake = Faker()
    consultant_data = []
    title_history_data = []

    # Distribution of current titles
    current_title_counts = {
        'T1': int(0.30 * num_consultants),
        'T2': int(0.20 * num_consultants),
        'T3': int(0.20 * num_consultants),
        'T4': int(0.10 * num_consultants),
        'T5': int(0.10 * num_consultants)
    }
    while sum(current_title_counts.values()) < num_consultants:
        current_title_counts['T1'] += 1

    # Promotion intervals
    promotion_intervals = {
        'T1': (1, 2),
        'T2': (2, 3),
        'T3': (3, 5),
        'T4': (1, 2),  # T4 to T5
        'T5': (0,0)
    }

    for i in range(num_consultants):
        consultant_id = f"C{i+1:04d}"
        name = fake.name()
        email = f"{name.replace(' ', '.').lower()}@ise558.com"
        phone = fake.phone_number()

        # Initialize current title based on distribution
        current_title = random.choices(list(current_title_counts.keys()), weights=list(current_title_counts.values()))[0]
        current_title_counts[current_title] -= 1

        # Randomly initialize entry title based on the current title
        if current_title == 'T1':
            entry_title = 'T1'
        elif current_title == 'T2':
            entry_title = random.choice(['T1', 'T2'])
        elif current_title == 'T3':
            entry_title = random.choice(['T1', 'T2', 'T3'])
        elif current_title == 'T4':
            entry_title = random.choice(['T1', 'T2', 'T3', 'T4'])
        else:  # T5
            entry_title = random.choice(['T1', 'T2', 'T3', 'T4', 'T5'])

        # Initialize start date
        start_dates = {
            'T1': None,
            'T2': None,
            'T3': None,
            'T4': None,
            'T5': None
        }

        current_date = date(2020, 12, 31)
        for title in range(int(current_title[1]), int(entry_title[1])-1, -1):
            title_key = f"T{title}"
            interval_min, interval_max = promotion_intervals[title_key]
            interval = random.randint(interval_min, interval_max)
            year = current_date.year - interval
            start_date = fake.date_between(start_date=date(year, 1, 1), end_date=date(year, 12, 31))
            start_dates[title_key] = start_date
            current_date = start_date

            title_history_data.append([consultant_id, title_key, start_date])

        consultant_data.append([
            consultant_id, name, email, phone, current_title
        ])

    # Store to df
    consultant_df = pd.DataFrame(consultant_data, columns=['Consultant_ID', 'Name', 'Email', 'Phone', 'CurrentTitle'])
    title_history_df = pd.DataFrame(title_history_data, columns=['Consultant_ID', 'Title', 'StartDate'])

    # Save to CSV
    consultant_df.to_csv(consultant_csv_file_path, index=False)
    title_history_df.to_csv(title_history_csv_file_path, index=False)

def main(num_consultants):
    generate_consultant_data(num_consultants)