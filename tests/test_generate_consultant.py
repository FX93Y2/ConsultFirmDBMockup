import os
import pandas as pd
import random
from faker import Faker
from datetime import timedelta, date

def generate_consultant_data(num_consultants):
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_path = os.path.join(base_path, 'data', 'raw')
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
        'T4': (1, 2),
        'T5': (0, 0)  # No further promotions from T5
    }

    for i in range(num_consultants):
        consultant_id = f"C{i+1:04d}"
        name = fake.name()
        email = f"{name.replace(' ', '.').lower()}@ise558.com"
        phone = fake.phone_number()

        # Determine the current title
        current_title = random.choices(list(current_title_counts.keys()), weights=list(current_title_counts.values()))[0]
        current_title_counts[current_title] -= 1

        # Determine the entry title based on the current title
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

        consultant_data.append([consultant_id, name, email, phone, entry_title, current_title])

        # Generate title history for the consultant
        current_date = date(2020, 12, 31)
        prev_title = None
        for title in range(int(current_title[1]), int(entry_title[1])-1, -1):
            title_key = f"T{title}"
            interval_min, interval_max = promotion_intervals[title_key]
            interval = random.randint(interval_min, interval_max)
            year = current_date.year - interval
            start_date = fake.date_between(start_date=date(year, 1, 1), end_date=date(year, 12, 31))
            current_date = start_date

            if title_key != prev_title:
                title_history_data.append([consultant_id, title_key, start_date])
                prev_title = title_key

        if entry_title != prev_title:
            title_history_data.append([consultant_id, entry_title, current_date])

    # Create DataFrames from the consultant data and title history data
    consultant_df = pd.DataFrame(consultant_data, columns=['Consultant_ID', 'Name', 'Email', 'Phone', 'EntryTitle', 'CurrentTitle'])
    title_history_df = pd.DataFrame(title_history_data, columns=['Consultant_ID', 'Title', 'StartDate'])

    # Adjust title counts for each year
    for year in range(2010, 2021):
        year_start_date = date(year, 1, 1)
        year_end_date = date(year, 12, 31)

        year_title_counts = {
            'T1': int(0.30 * num_consultants),
            'T2': int(0.20 * num_consultants),
            'T3': int(0.20 * num_consultants),
            'T4': int(0.10 * num_consultants),
            'T5': int(0.10 * num_consultants)
        }

        year_title_history = title_history_df[(title_history_df['StartDate'] >= year_start_date) & (title_history_df['StartDate'] <= year_end_date)]

        for _, row in year_title_history.iterrows():
            consultant_id = row['Consultant_ID']
            title = row['Title']

            if year_title_counts[title] > 0:
                year_title_counts[title] -= 1
            else:
                new_title = random.choices(list(year_title_counts.keys()), weights=list(year_title_counts.values()))[0]
                year_title_counts[new_title] -= 1
                title_history_df.loc[(title_history_df['Consultant_ID'] == consultant_id) & (title_history_df['StartDate'] == row['StartDate']), 'Title'] = new_title

    # Save the DataFrames to CSV files
    consultant_df.to_csv(consultant_csv_file_path, index=False)
    title_history_df.to_csv(title_history_csv_file_path, index=False)

def main(num_consultants):
    generate_consultant_data(num_consultants)