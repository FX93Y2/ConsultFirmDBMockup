#from data_generator.generate_consultant import main as generate_consultant
#from data_generator.generate_client import main as generate_client
#from data_generator.generate_consultant import main as generate_consultant
from data_generator.generate_client import generate_location, generate_client
from data_generator.generate_project import main as generate_project
from data_generator.Project_Billing_Rate import main as project_Billing_Rate
from data_generator.generate_proj_and_billing_rate import main as generate_proj_and_billing_rate


def main():
    num_titles = 1000
    num_years = 10
    num_clients = 100
    num_projects = 100
    #generate_consultant(num_titles, num_years)
    #generate_client(num_client)
    #generate_project(num_projects)
    #project_Billing_Rate(100, [1, 2, 3, 4, 5])
    location_data = generate_location(num_locations)
    generate_client(num_clients, location_data)
    generate_proj_and_billing_rate(num_projects)

if __name__ == "__main__":
    main()