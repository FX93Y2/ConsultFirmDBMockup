import random
from faker import Faker
from unidecode import unidecode
from datetime import timedelta, date
from sqlalchemy.orm import sessionmaker
from collections import defaultdict
from data_generator.create_db import Consultant, Title, BusinessUnit, ConsultantTitleHistory, engine

# Constants and Distributions
HIRING_SEASON_PROB = {'Spring': 0.4, 'Fall': 0.4, 'Other': 0.2}
ATTRITION_RATE = {1: 0.01, 2: 0.005, 3: 0.005, 4: 0.005, 5: 0.005, 6: 0.005}
SALARY_RANGE = {
    1: (60000, 80000), 2: (80000, 100000), 3: (100000, 120000),
    4: (120000, 150000), 5: (150000, 200000), 6: (200000, 250000)
}
TITLE_DISTRIBUTION = {1: 0.35, 2: 0.3, 3: 0.2, 4: 0.10, 5: 0.04, 6: 0.01}
BUSINESS_UNIT_DISTRIBUTION = {
    "North America": 0.6,
    "Central and South America": 0.1,
    "EMEA": 0.2,
    "Asia Pacific": 0.1
}
REGION_LOCALE_MAPPING = {
    "North America": ["en_US", "en_CA"],
    "Central and South America": ["es_MX", "pt_BR", "es_CO"],
    "EMEA": ["en_GB", "de_DE", "fr_FR"],
    "Asia Pacific": ["zh_CN", "ja_JP", "ko_KR", "en_AU"]
}
EXPANSION_THRESHOLDS = {
    400: "EMEA",
    800: "Asia Pacific",
    1500: "Central and South America"
}
MIN_PROMOTION_YEARS = {
    1: 0.5, 2: 2, 3: 2, 4: 3, 5: 3, 6: 0
}
PROMOTION_CHANCE = 0.5

fake = Faker()
faker_instances = {locale: Faker(locale) for region in REGION_LOCALE_MAPPING for locale in REGION_LOCALE_MAPPING[region]}

# Basic Helper functions
def get_growth_rate(year):
    yearly_growth_rates = {
        2015: 0.50, 2016: 0.60, 2017: 0.40, 2018: 0.30,
        2019: 0.20, 2020: 0.10, 2021: 0.05, 2022: 0.05, 
        2023: -0.05, 2024: -0.06
    }
    default_rate = 0.25
    variation = random.uniform(-0.05, 0.05)
    return yearly_growth_rates.get(year, default_rate) + variation

def get_faker_for_region(region):
    if region in REGION_LOCALE_MAPPING:
        locale = random.choice(REGION_LOCALE_MAPPING[region])
        return faker_instances[locale]
    else:
        return faker_instances["en_US"]

def transliterate_name(name, locale):
    if locale in ['zh_CN', 'ja_JP', 'ko_KR']:
        return unidecode(name)
    return name

def calculate_target_consultants(year, initial_num, start_year):
    current_num = initial_num
    for y in range(start_year, year + 1):
        current_num = int(current_num * (1 + get_growth_rate(y)))
    return current_num

def generate_title_slots(num_consultants):
    slots = {title: max(1, int(num_consultants * percentage)) for title, percentage in TITLE_DISTRIBUTION.items()}
    
    # Ensure there are always some slots available for higher titles
    for title in range(2, 7):
        slots[title] = max(slots[title], int(slots[title - 1] * 0.3))
    
    for title in range(1, 6):
        slots[title + 1] += int(slots[title] * 0.1)
    
    return slots

# Functions for attrition

def should_leave_company(title_id):
    return random.random() < ATTRITION_RATE[title_id]

# Functions for promotion

def should_be_promoted(current_title_id, years_in_role, total_years_in_company):
    if current_title_id == 6:  # Highest title, can't be promoted
        return False
    
    min_years = MIN_PROMOTION_YEARS[current_title_id]
    if years_in_role < min_years:
        return False
    
    base_promotion_chance = PROMOTION_CHANCE
    # Increase base promotion chance for higher titles
    base_promotion_chance += (current_title_id - 1) * 0.05
    
    additional_years = years_in_role - min_years
    promotion_chance = base_promotion_chance + min(0.4, additional_years * 0.1)
    tenure_bonus = min(0.2, total_years_in_company * 0.02)
    promotion_chance += tenure_bonus
    
    result = random.random() < promotion_chance
    return result

def get_years_in_current_role(consultant_id, current_title_id, current_year, title_history_data):
    relevant_history = [th for th in title_history_data if th.ConsultantID == consultant_id and th.TitleID == current_title_id]
    relevant_history.sort(key=lambda x: x.StartDate, reverse=True)
    
    for entry in relevant_history:
        if entry.EventType in ['Hire', 'Promotion']:
            return (date(current_year, 1, 1) - entry.StartDate).days / 365.25
    
    # If no hire or promotion event found, use the earliest record for this title
    return (date(current_year, 1, 1) - relevant_history[-1].StartDate).days / 365.25

# Salary adjustment

def get_new_salary(title_id):
    return random.randint(SALARY_RANGE[title_id][0], SALARY_RANGE[title_id][1])

def get_yearly_salary_adjustment():
    return random.uniform(0.02, 0.05)

# Handling Layoffs

def should_layoff(year, growth_rate):
    return growth_rate < 0

def get_layoff_percentage(growth_rate):
    return min(0.2, abs(growth_rate))

def perform_layoffs(active_consultants, growth_rate, year, title_history_data, consultant_data):
    layoff_percentage = get_layoff_percentage(growth_rate)
    total_consultants = sum(len(consultants) for consultants in active_consultants.values())
    num_layoffs = int(total_consultants * layoff_percentage)
    layoffs = []
    layoff_distribution = {
        1: 0.35, 2: 0.25, 3: 0.20, 4: 0.10, 5: 0.07, 6: 0.03
    }

    for title in range(1, 7):
        title_layoffs = int(num_layoffs * layoff_distribution[title])
        consultants = active_consultants[title]
        consultants.sort(key=lambda x: x[1])  # Sort by years_in_role
        layoffs.extend(consultants[:title_layoffs])
        active_consultants[title] = consultants[title_layoffs:]

    for consultant, years_in_role, total_years in layoffs:
        current_title_history = next(th for th in reversed(title_history_data) 
                                     if th.ConsultantID == consultant.ConsultantID and th.EndDate is None)
        layoff_date = date(year, random.randint(1, 12), random.randint(1, 28))
        current_title_history.EndDate = layoff_date
        title_history_data.append(ConsultantTitleHistory(
            ConsultantID=consultant.ConsultantID, 
            TitleID=current_title_history.TitleID,
            StartDate=date(year, 1, 1), 
            EndDate=layoff_date, 
            EventType='Layoff', 
            Salary=current_title_history.Salary
        ))
        consultant_data.remove(consultant)

    return num_layoffs, title_history_data, consultant_data

# Main generation logic
def generate_consultant_data(initial_num_titles, start_year, end_year):
    consultant_data = []
    title_history_data = []
    consultant_id_counter = 1

    def create_consultant(region, title_id, year):
        nonlocal consultant_id_counter
        faker = get_faker_for_region(region)
        consultant_id = f"C{consultant_id_counter:04d}"
        
        if faker.locale in ['zh_CN', 'ja_JP', 'ko_KR']:
            first_name = unidecode(faker.first_name())
            last_name = unidecode(faker.last_name())
        else:
            first_name = faker.first_name()
            last_name = faker.last_name()
        
        email = f"{first_name[0].lower()}{last_name.lower()}{random.randint(100, 999)}@ise558.com"
        phone = faker.phone_number()

        consultant = Consultant(ConsultantID=consultant_id, FirstName=first_name, LastName=last_name, 
                                Email=email, Contact=phone, Region=region, HireYear=year)
        consultant_id_counter += 1

        start_date = date(year, random.randint(1, 12), random.randint(1, 28))
        salary = get_new_salary(title_id)
        title_history = ConsultantTitleHistory(
            ConsultantID=consultant_id, TitleID=title_id, 
            StartDate=start_date, EventType='Hire', Salary=salary
        )

        return consultant, title_history

    # Initialize consultants for the start year
    title_slots = generate_title_slots(initial_num_titles)
    for title_id in sorted(title_slots.keys(), reverse=True):
        num_slots = title_slots[title_id]
        for _ in range(num_slots):
            consultant, title_history = create_consultant("North America", title_id, start_year)
            consultant_data.append(consultant)
            title_history_data.append(title_history)

    for year in range(start_year + 1, end_year + 1):
        growth_rate = get_growth_rate(year)
        target_consultants = calculate_target_consultants(year, initial_num_titles, start_year)
        title_slots = generate_title_slots(target_consultants)

        active_consultants = defaultdict(list)
        
        # Process existing consultants
        for consultant in list(consultant_data):
            current_title_history = next((th for th in reversed(title_history_data) 
                                        if th.ConsultantID == consultant.ConsultantID and th.EndDate is None), None)
            if not current_title_history:
                continue

            current_title_id = current_title_history.TitleID
            years_in_role = get_years_in_current_role(consultant.ConsultantID, current_title_id, year, title_history_data)
            total_years = year - consultant.HireYear

            if should_leave_company(current_title_id):
                leave_date = date(year, random.randint(1, 12), random.randint(1, 28))
                current_title_history.EndDate = leave_date
                title_history_data.append(ConsultantTitleHistory(
                    ConsultantID=consultant.ConsultantID, TitleID=current_title_id, 
                    StartDate=date(year, 1, 1), EndDate=leave_date, 
                    EventType='Attrition', Salary=current_title_history.Salary
                ))
                consultant_data.remove(consultant)
            else:
                active_consultants[current_title_id].append((consultant, years_in_role, total_years))

        # Handle layoffs
        if should_layoff(year, growth_rate):
            num_layoffs, title_history_data, consultant_data = perform_layoffs(
                active_consultants, growth_rate, year, title_history_data, consultant_data
            )

        # Process promotions
        promotions = 0
        for title_id in range(1, 6):  # We don't process promotions for title 6
            promotion_candidates = []
            for consultant, years_in_role, total_years in active_consultants[title_id]:
                if should_be_promoted(title_id, years_in_role, total_years):
                    promotion_candidates.append((consultant, years_in_role, total_years))
            
            available_slots = max(0, title_slots[title_id + 1] - len(active_consultants[title_id + 1]))
                
            for candidate, years_in_role, total_years in promotion_candidates[:available_slots]:
                promotion_date = date(year, random.randint(1, 12), random.randint(1, 28))
                current_title_history = next(th for th in reversed(title_history_data) 
                                            if th.ConsultantID == candidate.ConsultantID and th.EndDate is None)
                current_title_history.EndDate = promotion_date - timedelta(days=1)
                
                new_salary = max(get_new_salary(title_id + 1), int(current_title_history.Salary * 1.1))
                title_history_data.append(ConsultantTitleHistory(
                    ConsultantID=candidate.ConsultantID, TitleID=title_id + 1, 
                    StartDate=promotion_date, EventType='Promotion', Salary=new_salary
                ))
                active_consultants[title_id + 1].append((candidate, 0, total_years + 1))
                active_consultants[title_id] = [c for c in active_consultants[title_id] if c[0].ConsultantID != candidate.ConsultantID]
                promotions += 1

        # Handle new hires
        new_hires = 0
        for title_id in range(1, 7):
            while len(active_consultants[title_id]) < title_slots[title_id]:
                region = random.choices(list(BUSINESS_UNIT_DISTRIBUTION.keys()), 
                                        weights=list(BUSINESS_UNIT_DISTRIBUTION.values()))[0]
                new_consultant, new_title_history = create_consultant(region, title_id, year)
                consultant_data.append(new_consultant)
                title_history_data.append(new_title_history)
                active_consultants[title_id].append((new_consultant, 0, 0))
                new_hires += 1

        # Create continuation records
        for title_id, consultants in active_consultants.items():
            for consultant, years_in_role, total_years in consultants:
                current_title_history = next(th for th in reversed(title_history_data) 
                                            if th.ConsultantID == consultant.ConsultantID and th.EndDate is None)
                if current_title_history.StartDate.year < year:
                    salary_adjustment = get_yearly_salary_adjustment()
                    new_salary = int(current_title_history.Salary * (1 + salary_adjustment))
                    current_title_history.EndDate = date(year, 1, 1) - timedelta(days=1)
                    title_history_data.append(ConsultantTitleHistory(
                        ConsultantID=consultant.ConsultantID, TitleID=title_id, 
                        StartDate=date(year, 1, 1), EventType='Continuation', Salary=new_salary
                    ))

        print(f"Year {year}: Total consultants: {len(consultant_data)}, Promotions: {promotions}, New Hires: {new_hires}")

    return consultant_data, title_history_data

def assign_business_units(consultant_data, session):
    business_units = session.query(BusinessUnit).all()
    business_unit_dict = {bu.BusinessUnitName: bu for bu in business_units}
    
    unmatched_regions = set()
    assigned_count = defaultdict(int)
    
    for consultant in consultant_data:
        if consultant.Region in business_unit_dict:
            consultant.BusinessUnitID = business_unit_dict[consultant.Region].BusinessUnitID
            assigned_count[consultant.Region] += 1
        else:
            unmatched_regions.add(consultant.Region)
            # Assign to a default business unit (e.g., North America) if region doesn't match
            consultant.BusinessUnitID = business_unit_dict["North America"].BusinessUnitID
            assigned_count["North America"] += 1

    if unmatched_regions:
        print(f"Warning: The following regions did not match any business unit: {unmatched_regions}")
        print("These consultants will be assigned to North America")

    print("\nBusiness Unit Assignment Summary:")
    for bu_name, count in assigned_count.items():
        print(f"{bu_name}: {count} consultants")

    return consultant_data

def simulate_global_expansion(consultant_data, start_year, end_year):
    regions = list(BUSINESS_UNIT_DISTRIBUTION.keys())
    active_regions = ["North America"]
    
    for year in range(start_year, end_year + 1):
        total_consultants = len([c for c in consultant_data if c.HireYear <= year])
        
        # Check if we need to expand to a new region
        for threshold, new_region in EXPANSION_THRESHOLDS.items():
            if total_consultants >= threshold and new_region not in active_regions:
                active_regions.append(new_region)
                print(f"Year {year}: Expanded to {new_region}")
                break
        
        # Update regions for consultants hired this year
        new_consultants = [c for c in consultant_data if c.HireYear == year]
        for consultant in new_consultants:
            consultant.Region = random.choices(
                active_regions,
                weights=[BUSINESS_UNIT_DISTRIBUTION[r] for r in active_regions]
            )[0]

    return active_regions

def main(initial_num_titles, start_year, end_year):
    print("Generating consultant data...")
    consultant_data, title_history_data = generate_consultant_data(initial_num_titles, start_year, end_year)
    
    print("\nSimulating global expansion...")
    final_regions = simulate_global_expansion(consultant_data, start_year, end_year)
    print(f"Final regions at {end_year}: {', '.join(final_regions)}")

    print("\nAssigning business units...")
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        consultant_data = assign_business_units(consultant_data, session)
        session.bulk_save_objects(consultant_data)
        session.bulk_save_objects(title_history_data)
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"An error occurred while processing or inserting data: {e}")
    finally:
        session.close()

    print("Complete")