import os
import pandas as pd
import random
from faker import Faker
from datetime import timedelta, date

def generate_consultant_data(num_titles, num_years):
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_path = os.path.join(base_path, 'data', 'processed')
    consultant_csv_file_path = os.path.join(data_path, "Consultant.csv")
    title_history_csv_file_path = os.path.join(data_path, "Consultant_Title_History.csv")

    os.makedirs(data_path, exist_ok=True)

    fake = Faker()
    consultant_data = []
    title_history_data = []

    # Distribution of titles
    title_distribution = {
        '1': 0.30,
        '2': 0.20,
        '3': 0.20,
        '4': 0.15,
        '5': 0.10,
        '6': 0.05
    }

    # Promotion intervals
    promotion_intervals = {
        '1': (1, 3),
        '2': (2, 4),
        '3': (3, 5),
        '4': (2, 4),
        '5': (2, 4),
        '6': (0, 0)
    }

    # Generate title slots for each year based on the distribution
    titles_per_year = {year: [] for year in range(2010, 2010 + num_years)}  # start with 2010

    for title, percentage in title_distribution.items():
        num_title = int(num_titles * percentage)
        for _ in range(num_title):
            year = random.randint(2010, 2010 + num_years)
            titles_per_year[year].append(title)

    # Fill the titles_per_year dictionary with the titles
    consultant_id_counter = 1
    for year in range(2010, 2010 + num_years):
        for title in titles_per_year[year]:
            # Find a suitable consultant for promotion
            suitable_consultant = None
            for consultant in consultant_data:
                current_title = consultant[5]
                if current_title == title:
                    continue
                if current_title == '6' or int(title) != int(current_title) + 1:
                    continue
                last_promotion_date = max(entry[2] for entry in title_history_data if entry[0] == consultant[0])
                interval_min, interval_max = promotion_intervals[current_title]
                years_since_last_promotion = (date(year, 1, 1) - last_promotion_date).days // 365
                if interval_min <= years_since_last_promotion <= interval_max:
                    suitable_consultant = consultant
                    break

            if suitable_consultant:
                consultant_id = suitable_consultant[0]
                suitable_consultant[5] = title
            else:
                # Create a new consultant
                consultant_id = f"C{consultant_id_counter:04d}"
                consultant_id_counter += 1
                name = fake.name()
                first_name, last_name = name.split(' ', 1)
                email_format = random.choice(['first_initial', 'full_first_name'])
                if email_format == 'first_initial':
                    email = f"{first_name[0].lower()}{last_name.lower()}{random.randint(100, 999)}@ise558.com"
                else:
                    email = f"{first_name.lower()}{last_name.lower()}{random.randint(100, 999)}@ise558.com"
                phone = fake.phone_number()
                consultant_data.append([consultant_id, name, email, phone, title, title])

            # Add title history entry
            start_date = date(year, 1, 1) + timedelta(days=random.randint(0, 364))
            title_history_data.append([consultant_id, title, start_date])

    # Store data in DataFrames
    consultant_df = pd.DataFrame(consultant_data, columns=['Consultant_ID', 'Name', 'Email', 'Phone', 'EntryTitle', 'CurrentTitle'])
    title_history_df = pd.DataFrame(title_history_data, columns=['Consultant_ID', 'Title', 'StartDate'])

    # Save DataFrames to CSV
    consultant_df.to_csv(consultant_csv_file_path, index=False)
    title_history_df.to_csv(title_history_csv_file_path, index=False)

def main(num_titles, num_years):
    generate_consultant_data(num_titles, num_years)