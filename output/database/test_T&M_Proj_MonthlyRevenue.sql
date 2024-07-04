WITH exp AS (
    SELECT ProjectID, STRFTIME('%Y-%m', Date) AS Year_Month,
        SUM(CASE WHEN IsBillable = 1 THEN Amount
                ELSE -Amount
            END) as TotalExpenses
    FROM ProjectExpense
    GROUP BY ProjectID, STRFTIME('%Y-%m', Date)
),

tb AS (
    -- T&M projects charges by month
    SELECT Deliverable.ProjectID, 
        STRFTIME('%Y-%m', Consultant_Deliverable.Date) AS Year_Month,
        SUM(Consultant_Deliverable.Hours * ProjectBillingRate.Rate) as Amount

    FROM Consultant_Deliverable

    LEFT JOIN Deliverable 
        ON Deliverable.DeliverableID = Consultant_Deliverable.DeliverableID
    LEFT JOIN Project 
        ON Deliverable.ProjectID = Project.ProjectID

    LEFT JOIN Consultant_Title_History
        ON Consultant_Deliverable.ConsultantID = Consultant_Title_History.ConsultantID
        AND (Consultant_Deliverable.Date BETWEEN Consultant_Title_History.StartDate 
                AND IFNULL(Consultant_Title_History.EndDate, '9999-12-31'))
    LEFT JOIN ProjectBillingRate
        ON Consultant_Title_History.TitleID = ProjectBillingRate.TitleID
        AND ProjectBillingRate.ProjectID = Deliverable.ProjectID

    WHERE Project.Type = 'Time and Material'

    Group BY Deliverable.ProjectID, STRFTIME('%Y-%m', Consultant_Deliverable.Date)
)

SELECT tb.ProjectID, tb.Year_Month, 
    IFNULL(TotalExpenses, 0) as TotalExpenses, 
    IFNULL(Amount, 0) as TotalAmount,
    IFNULL(Amount, 0) + IFNULL(TotalExpenses, 0) as Revenue
FROM tb
LEFT JOIN exp
    ON tb.ProjectID = exp.ProjectID
    AND tb.Year_Month = exp.Year_Month
