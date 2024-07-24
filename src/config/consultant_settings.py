# Constants and Distributions
HIRING_SEASON_PROB = {'Spring': 0.4, 'Fall': 0.4, 'Other': 0.2}
ATTRITION_RATE = {1: 0.01, 2: 0.005, 3: 0.005, 4: 0.005, 5: 0.005, 6: 0.005}
CONSULTANT_YEARLY_GROWTHRATE = {
        2015: 0.2, 2016: 0.30, 2017: 0.20, 2018: 0.10,
        2019: 0.10, 2020: 0.05, 2021: 0.04, 2022: 0.02, 
        2023: -0.05, 2024: -0.06
    }
SALARY_RANGE = {
    1: (50000, 60000), 2: (70000, 80000), 3: (90000, 120000),
    4: (120000, 150000), 5: (150000, 200000), 6: (200000, 250000)
}
TITLE_DISTRIBUTION = {1: 0.25, 2: 0.30, 3: 0.25, 4: 0.12, 5: 0.06, 6: 0.02}
BUSINESS_UNIT_DISTRIBUTION = {
    1: 0.6,
    2: 0.1,
    3: 0.2,
    4: 0.1
}
UNIT_LOCALE_MAPPING = {
    1: ["en_US", "en_CA"],
    2: ["es_MX", "pt_BR", "es_CO"],
    3: ["en_GB", "de_DE", "fr_FR"],
    4: ["zh_CN", "ja_JP", "ko_KR", "en_AU"]
}
EXPANSION_THRESHOLDS = {
    400: 3, #EMEA
    800: 4, # AP
    200: 2 # Central and South America
}
MIN_PROMOTION_YEARS = {
    1: 0.5, 2: 2, 3: 2, 4: 3, 5: 3, 6: 0
}
PROMOTION_CHANCE = 0.5