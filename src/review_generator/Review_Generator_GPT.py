import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from sqlalchemy import create_engine, MetaData, Table, inspect, select
import json
from datetime import datetime
import os

model_name = "EleutherAI/gpt-neo-125M"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

# DATABASE_URI = 'sqlite:///consulting_firm.db'
DATABASE_URI = 'sqlite:///' + os.path.abspath(os.path.join(os.path.dirname(__file__), '../../output/database/consulting_firm.db'))
print("Connecting to database at:", DATABASE_URI)
engine = create_engine(DATABASE_URI)
metadata = MetaData(bind=engine)
metadata.reflect(bind=engine)

def refresh_metadata():
    metadata.clear()
    metadata.reflect(bind=engine)

def get_table_names():
    refresh_metadata()  # Ensure metadata is up-to-date
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    print("Available tables in the database (after refresh):", table_names)
    return table_names

def get_table_data(table_name):
    refresh_metadata()  # Ensure metadata is up-to-date
    table = metadata.tables.get(table_name)
    if table is None:
        print(f"Table '{table_name}' does not exist.")
        return []
    
    with engine.connect() as connection:
        query = select([table])
        result = connection.execute(query)
        results = [dict(row) for row in result]
    return results

def generate_random_review():
    prompt = "pros and cons client review for a project"
    inputs = tokenizer(prompt, return_tensors='pt')
    outputs = model.generate(
        inputs.input_ids, 
        max_length=100, 
        num_return_sequences=1, 
        no_repeat_ngram_size=2, 
        do_sample=True, 
        top_k=50, 
        top_p=0.95,
        temperature=0.7
    )
    review = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return review[len(prompt):].strip()

def generate_json():
    table_name = 'Project'
    
    if table_name in get_table_names():
        projects = get_table_data(table_name)
        
        projects_json = []
        for project in projects:
            project_data = {
                "ProjectID": project["ProjectID"],
                "ClientID": project["ClientID"],
                "ProjectName": project["Name"],
                "ReviewComment": project.get("ReviewComment", generate_random_review())
            }
            projects_json.append(project_data)
        
        output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../output/json'))
        os.makedirs(output_dir, exist_ok=True)  # Create directory if it doesn't exist
        output_file_path = os.path.join(output_dir, 'client_reviews.json')

        with open(output_file_path, 'w') as json_file:
            json.dump(projects_json, json_file, indent=4)
        
        print(f"JSON file generated successfully at {output_file_path}")
    else:
        print(f"Table '{table_name}' does not exist in the database.")

if __name__ == "__main__":
    generate_json()
