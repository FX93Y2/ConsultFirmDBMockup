-- SQLite
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
),

tb1 AS (
    SELECT tb.ProjectID, tb.Year_Month, 
        IFNULL(TotalExpenses, 0) as TotalExpenses, 
        IFNULL(Amount, 0) as TotalAmount,
        IFNULL(Amount, 0) + IFNULL(TotalExpenses, 0) as Revenue
    FROM tb
    LEFT JOIN exp
        ON tb.ProjectID = exp.ProjectID
        AND tb.Year_Month = exp.Year_Month
),

unit_rev AS (
    SELECT Project.UnitID, tb1.Year_Month, SUM(tb1.Revenue) as Revenue
    FROM tb1
    LEFT JOIN Project
        ON tb1.ProjectID = Project.ProjectID
    GROUP BY Project.UnitID, tb1.Year_Month
),

cons_pay AS (
    SELECT Consultant.BusinessUnitID, 
        STRFTIME('%Y-%m', Payroll.EffectiveDate) AS Year_Month,
        SUM(Payroll.Amount) as Payroll
    FROM Payroll
    LEFT JOIN Consultant
        ON Payroll.ConsultantID = Consultant.ConsultantID
    GROUP BY Consultant.BusinessUnitID, STRFTIME('%Y-%m', Payroll.EffectiveDate)
)

SELECT unit_rev.UnitID, unit_rev.Year_Month, 
    IFNULL(Revenue, 0) as Revenue, 
    IFNULL(Payroll, 0) as Payroll,
    IFNULL(Revenue, 0) - IFNULL(Payroll, 0) as NetIncome
FROM unit_rev
LEFT JOIN cons_pay
    ON unit_rev.Year_Month = cons_pay.Year_Month
    AND unit_rev.UnitID = cons_pay.BusinessUnitID

-- check payroll data in business unit
SELECT *
FROM Payroll
WHERE ConsultantID IN (
    SELECT ConsultantID
    FROM Consultant
    WHERE BusinessUnitID = 2
)