import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy.orm import sessionmaker
from ..db_model import Consultant, ConsultantDeliverable, Payroll, engine
from config.path_config import non_billable_time_path

def generate_non_billable_time_report(working_hours_per_month=160):

    Session = sessionmaker(bind=engine)
    session = Session()

    # Query consultants
    consultants = session.query(Consultant).all()
    consultants_df = pd.DataFrame([(c.ConsultantID, c.FirstName, c.LastName) for c in consultants],
                                  columns=['ConsultantID', 'FirstName', 'LastName'])
    
    # Query deliverables
    deliverables = session.query(ConsultantDeliverable).all()
    deliverables_df = pd.DataFrame([(d.ConsultantID, d.Date, d.Hours) for d in deliverables],
                                   columns=['ConsultantID', 'Date', 'Hours'])
    
    # Query Payroll
    payrolls = session.query(Payroll).all()
    payrolls_df = pd.DataFrame([(p.ConsultantID, p.EffectiveDate) for p in payrolls],
                                   columns=['ConsultantID', 'Date'])
    
    # Ensure 'Date' column is datetime type
    deliverables_df['Date'] = pd.to_datetime(deliverables_df['Date'])
    payrolls_df['Date'] = pd.to_datetime(payrolls_df['Date'])
    
    # Calculate year-month for each deliverable and payroll
    deliverables_df['YearMonth'] = deliverables_df['Date'].dt.to_period('M')
    payrolls_df['YearMonth'] = payrolls_df['Date'].dt.to_period('M')
    
    # Summarize project hours per year-month for each consultant
    billable_consultant = deliverables_df.groupby(['ConsultantID', 'YearMonth']).agg({'Hours': 'sum'}).reset_index()
    project_hours_df = payrolls_df.merge(billable_consultant, on=['ConsultantID', 'YearMonth'], how='left')
    project_hours_df['Hours'] = project_hours_df['Hours'].fillna(0)
    
    # Calculate non-billable hours
    project_hours_df['NonBillableHours'] = project_hours_df.apply(
        lambda row: working_hours_per_month - row['Hours'] if row['Hours'] < working_hours_per_month else 0,
        axis=1
    )
    
    # Merge with consultant names
    project_hours_df = project_hours_df.merge(consultants_df, on='ConsultantID')
    project_hours_df['YearMonth'] = project_hours_df['YearMonth'].dt.strftime('%Y-%m')
    

    # Save DataFrame to Excel
    project_hours_df.to_excel(non_billable_time_path, index=False)
    print(f"Data saved to {non_billable_time_path}")

    session.close()

def main():
    generate_non_billable_time_report()

if __name__ == "__main__":
    main()
