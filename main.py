#from data_generator.generate_consultant import main as generate_consultant
from data_generator.generate_client import main as generate_client

def main():
    num_titles = 1000
    num_years = 10
    num_client = 1000
    #generate_consultant(num_titles, num_years)
    generate_client(num_client)

if __name__ == "__main__":
    main()