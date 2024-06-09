#from data_generator.generate_consultant import main as generate_consultant
#from data_generator.generate_client import main as generate_client
#from data_generator.generate_consultant import main as generate_consultant
from data_generator.generate_project import main as generate_project

def main():
    num_titles = 1000
    num_years = 10
    num_client = 100
    num_projects = 100
    #generate_consultant(num_titles, num_years)
    #generate_client(num_client)
    generate_project(num_projects)

if __name__ == "__main__":
    main()