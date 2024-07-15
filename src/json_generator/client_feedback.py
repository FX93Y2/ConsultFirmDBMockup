import random
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import sessionmaker
from collections import defaultdict
from decimal import Decimal
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch
from ..db_model import Project, engine
from config.path_config import json_path
import re

def generate_client_feedback():
    # Initialize the model and tokenizer
    model_id = "meta-llama/Meta-Llama-3-8B-Instruct"
    access_token = "your_token_here"

    tokenizer = AutoTokenizer.from_pretrained(model_id, use_auth_token=access_token)
    model = AutoModelForCausalLM.from_pretrained(model_id, use_auth_token=access_token, torch_dtype=torch.bfloat16)
    text_gen_pipeline = pipeline("text-generation", model=model, tokenizer=tokenizer, device=0)

    Session = sessionmaker(bind=engine)
    session = Session()

    completed_projects = session.query(Project).filter(Project.Status == "Completed").all()
    feedback_data = []

    def get_scaled_response():
        """ Returns a scaled response with 1 and 2 being less common. """
        return random.choices([1, 2, 3, 4, 5], [0.05, 0.05, 0.2, 0.4, 0.3])[0]

    def generate_feedback_response(prompt):
        """ Generate a feedback response using the model. """
        response = text_gen_pipeline(
            prompt,
            max_new_tokens=100,  # Limit to 20 tokens (approx. 20 words)
            eos_token_id=tokenizer.eos_token_id,
            do_sample=True,
            temperature=0.6,
            top_p=0.9,
        )
        # Extract the assistant's content
        assistant_content = response[0]['generated_text'][-1]['content']
        cleaned_content = re.sub(r'[\\]', '', assistant_content)  # Remove backslashes
        cleaned_content = cleaned_content.strip('"')  # Remove outer quotes
        
        return cleaned_content


    for project in completed_projects:
        q1_response = get_scaled_response()
        q2_response = get_scaled_response()
        overall_satisfaction = (q1_response + q2_response) / 2

        # Generate responses for Q3 and Q4 considering both Q1 and Q2 scores
        q3_prompt = [
            {"role": "system", "content": f"Assume you are a client of a completed consulting project, please generate a short sentence of feedbck based on scores {q1_response} for satisfaction and {q2_response} for communication."},
            {"role": "user", "content": "What did you like best about working with us?"},
        ]
        q4_prompt = [
            {"role": "system", "content": f"Assume you are a client of a completed consulting project, please generate a short sentence of feedbck based on scores {q1_response} for satisfaction and {q2_response} for communication."},
            {"role": "user", "content": "What could we improve on?"},
        ]
        q3_response = generate_feedback_response(q3_prompt)
        q4_response = generate_feedback_response(q4_prompt)

        feedback = {
            "responseID": str(random.randint(10000, 99999)),
            "projectID": project.ProjectID,
            "clientID": project.ClientID,
            "surveyDate": project.ActualEndDate.strftime("%Y-%m-%d"),
            "responses": [
                {
                    "questionID": "Q1",
                    "questionText": "How satisfied are you with the project outcome?",
                    "responseType": "scale",
                    "responseValue": str(q1_response)
                },
                {
                    "questionID": "Q2",
                    "questionText": "Please rate the communication from our team.",
                    "responseType": "scale",
                    "responseValue": str(q2_response)
                },
                {
                    "questionID": "Q3",
                    "questionText": "What did you like best about working with us?",
                    "responseType": "text",
                    "responseValue": q3_response
                },
                {
                    "questionID": "Q4",
                    "questionText": "What could we improve on?",
                    "responseType": "text",
                    "responseValue": q4_response
                }
            ],
            "overallSatisfaction": str(round(overall_satisfaction, 1))
        }
        feedback_data.append(feedback)

    with open(json_path, 'w') as json_file:
        json.dump(feedback_data, json_file, indent=4)

    print(f"Client feedback JSON file has been generated successfully at {json_path}.")

    session.close()

def main():
    generate_client_feedback()

if __name__ == "__main__":
    main()
