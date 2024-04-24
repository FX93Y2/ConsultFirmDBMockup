from data_generator.generate_deliverable_plan import main as generate_deliverable_plan
from data_generator.generate_consultant import main as generate_consultant
from data_generator.generate_client import main as generate_client

def main():
    num_clients = 1000
    num_projects = 12600
    num_consultants = 10500
    generate_deliverable_plan(num_projects)
    generate_consultant(num_consultants)
    generate_client(num_clients)

if __name__ == "__main__":
    main()