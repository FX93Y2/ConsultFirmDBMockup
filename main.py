from data_generator.generate_client import generate_location, generate_client

def main():
    num_clients = 1000
    num_locations = 200
    location_data = generate_location(num_locations)
    generate_client(num_clients, location_data)

if __name__ == "__main__":
    main()