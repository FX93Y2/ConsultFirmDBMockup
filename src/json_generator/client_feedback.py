import random
import json
from datetime import datetime,timedelta
from sqlalchemy.orm import sessionmaker
from collections import defaultdict
from decimal import Decimal
from ..db_model import Project, engine
from config.path_config import json_path

def generate_client_feedback():
    Session = sessionmaker(bind=engine)
    session = Session()

    completed_projects = session.query(Project).filter(Project.Status == "Completed").all()
    feedback_data = []

    def get_scaled_response():
        """ Returns a scaled response with 1 and 2 being less common. """
        return random.choices([1, 2, 3, 4, 5], [0.05, 0.05, 0.2, 0.4, 0.3])[0]

    for project in completed_projects:
        q1_response = get_scaled_response()
        q2_response = get_scaled_response()
        overall_satisfaction = (q1_response + q2_response) / 2

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
                    "responseValue": ""
                },
                {
                    "questionID": "Q4",
                    "questionText": "What could we improve on?",
                    "responseType": "text",
                    "responseValue": ""
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
