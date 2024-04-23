from data_generator.generate_deliverable_plan import main as generate_deliverable_plan
from data_generator.generate_consultant import main as generate_consultant

def main():
    num_projects = 1000
    num_consultants = 456
    generate_deliverable_plan(num_projects)
    generate_consultant(num_consultants)

if __name__ == "__main__":
    main()