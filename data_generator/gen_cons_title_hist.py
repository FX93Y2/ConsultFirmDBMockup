import random
from faker import Faker
from datetime import timedelta, date
from sqlalchemy.orm import sessionmaker
from data_generator.create_db import Consultant, Title, ConsultantTitleHistory, engine

def generate_consultant_data(num_titles, num_years):
    Session = sessionmaker(bind=engine)
    session = Session()

    fake = Faker()
    consultant_data = []
    title_history_data = []

    # Hiring Season Probability
    hiring_season_prob = {
        'Spring': 0.4,
        'Fall': 0.4,
        'Other': 0.2
    }

    # Attrition Rate per Title
    attrition_rate = {
        1: 0.1,
        2: 0.08,
        3: 0.06,
        4: 0.04,
        5: 0.02,
        6: 0.01
    }

    # Performance Ratings Distribution
    performance_rating_dist = {
        'High': 0.2,
        'Average': 0.75,
        'Low': 0.05
    }

    # Promotion Intervals based on Performance Ratings
    promotion_intervals = {
        'High': {
            1: (1, 2),
            2: (1, 3),
            3: (2, 4),
            4: (1, 3),
            5: (1, 3),
            6: (0, 0)
        },
        'Average': {
            1: (1, 3),
            2: (2, 4),
            3: (3, 5),
            4: (2, 4),
            5: (2, 4),
            6: (0, 0)
        },
        'Low': {
            1: (2, 4),
            2: (3, 5),
            3: (4, 6),
            4: (3, 5),
            5: (3, 5),
            6: (0, 0)
        }
    }
    # Distribution of titles
    title_distribution = {
        1: 0.30,
        2: 0.20,
        3: 0.20,
        4: 0.15,
        5: 0.10,
        6: 0.05
    }

    # Generate title slots for each year based on the distribution
    start_year = 2010
    end_year = start_year + num_years
    titles_per_year = {year: [] for year in range(start_year, end_year + 1)}

    for title, percentage in title_distribution.items():
        num_title = int(num_titles * percentage)
        for _ in range(num_title):
            year = random.randint(start_year, end_year)
            titles_per_year[year].append(title)

    # Start generating consultants
    consultant_id_counter = 1
    for year in range(start_year, end_year + 1):
        for title_id in titles_per_year[year]:
            # Find a suitable consultant for promotion
            suitable_consultant = None
            for consultant in session.query(Consultant).all():
                current_title_history = session.query(ConsultantTitleHistory).filter_by(ConsultantID=consultant.ConsultantID).order_by(ConsultantTitleHistory.StartDate.desc()).first()
                if current_title_history:
                    current_title_id = current_title_history.TitleID
                    if current_title_id == title_id:
                        continue
                    if current_title_id == 6 or title_id != current_title_id + 1:
                        continue
                    last_promotion_date = current_title_history.StartDate
                    performance_rating = consultant.PerformanceRating
                    interval_min, interval_max = promotion_intervals[performance_rating][current_title_id]
                    years_since_last_promotion = (date(year, 1, 1) - last_promotion_date).days // 365
                    if interval_min <= years_since_last_promotion <= interval_max:
                        suitable_consultant = consultant
                        break

            if suitable_consultant:
                consultant_id = suitable_consultant.ConsultantID

                # Check for attrition
                if random.random() < attrition_rate[title_id]:
                    end_date = date(year, 1, 1) + timedelta(days=random.randint(0, 364))
                    title_history = ConsultantTitleHistory(ConsultantID=consultant_id, TitleID=title_id, StartDate=end_date, EndDate=end_date, EventType='Attrition')
                    session.add(title_history)
                    session.delete(suitable_consultant)
                    continue

                # Add promotion entry
                start_date = date(year, 1, 1) + timedelta(days=random.randint(0, 364))
                title_history = ConsultantTitleHistory(ConsultantID=consultant_id, TitleID=title_id, StartDate=start_date, EventType='Promotion')
                session.add(title_history)
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
                performance_rating = random.choices(list(performance_rating_dist.keys()), weights=performance_rating_dist.values())[0]

                consultant = Consultant(ConsultantID=consultant_id, FirstName=first_name, LastName=last_name, Email=email, Contact=phone, PerformanceRating=performance_rating)
                session.add(consultant)

                # Add hiring entry
                hiring_season = random.choices(list(hiring_season_prob.keys()), weights=hiring_season_prob.values())[0]
                if hiring_season == 'Spring':
                    start_date = date(year, random.randint(3, 5), random.randint(1, 30))
                elif hiring_season == 'Fall':
                    start_date = date(year, random.randint(9, 11), random.randint(1, 30))
                else:
                    start_date = date(year, 1, 1) + timedelta(days=random.randint(0, 364))

                title_history = ConsultantTitleHistory(ConsultantID=consultant_id, TitleID=title_id, StartDate=start_date, EventType='Hire')
                session.add(title_history)

    session.commit()
    session.close()

def main(num_titles, num_years):
    generate_consultant_data(num_titles, num_years)