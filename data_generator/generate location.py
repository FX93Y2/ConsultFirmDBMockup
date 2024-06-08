import os
import pandas as pd
import random

def generate_location(num_locations):
    base_path = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(base_path, 'data', 'processed')
    csv_file_path = os.path.join(data_path, "Location.csv")

    os.makedirs(data_path, exist_ok=True)

    locations = {
        'US': {
            'Country': 'United States',
            'States': ['CA', 'NY', 'TX', 'FL', 'IL'],
            'Cities': ['Los Angeles', 'New York', 'Houston', 'Miami', 'Chicago']
        },
        'Europe': {
            'Country': 'Europe',
            'States': ['ENG', 'GER', 'FRA', 'ITA', 'ESP'],
            'Cities': ['London', 'Berlin', 'Paris', 'Rome', 'Madrid']
        },
        'Asia': {
            'Country': 'Asia',
            'States': ['CHN', 'JPN', 'IND', 'KOR', 'SGP'],
            'Cities': ['Beijing', 'Tokyo', 'Mumbai', 'Seoul', 'Singapore']
        },
        'Other': {
            'Country': 'Other',
            'States': ['AUS', 'BRA', 'RSA', 'CAN', 'MEX'],
            'Cities': ['Sydney', 'São Paulo', 'Johannesburg', 'Toronto', 'Mexico City']
        }
    }

    region_distribution = {
        'US': 0.6,
        'Europe': 0.2,
        'Asia': 0.1,
        'Other': 0.1
    }

    location_data = []
    for _ in range(num_locations):
        region = random.choices(list(region_distribution.keys()), weights=region_distribution.values(), k=1)[0]
        country = locations[region]['Country']
        state = random.choice(locations[region]['States'])
        city = random.choice(locations[region]['Cities'])
        location_data.append([country, state, city])

    location_df = pd.DataFrame(location_data, columns=['Country', 'State', 'City'])
    location_df['LocationID'] = range(1, 1 + len(location_df))

    cols = location_df.columns.tolist()
    cols.insert(0, cols.pop(cols.index('LocationID')))
    location_df = location_df[cols]

    # Save the DataFrame to the CSV file
    location_df.to_csv(csv_file_path, index=False)
    print(f"Generated {num_locations} locations and saved to {csv_file_path}")

def main(num_locations):
    generate_location(num_locations)

if __name__ == "__main__":
    main(30)
