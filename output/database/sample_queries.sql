-- Q3: Consultant Project Hours
WITH tb AS (
    SELECT
        ConsultantID, DeliverableID,
        SUM(Hours) AS Hours
    FROM
        Consultant_Deliverable
    GROUP BY 
        ConsultantID, DeliverableID
)

SELECT
    tb.ConsultantID, 
    d.ProjectID,
    SUM(Hours) AS Hours
FROM tb 
LEFT JOIN Deliverable AS d ON tb.DeliverableID = d.DeliverableID
GROUP BY tb.ConsultantID, d.ProjectID


-- Q4: Business Unit Revenue
WITH exp AS (
    SELECT ProjectID, STRFTIME('%Y-%m', Date) AS Year_Month,
        SUM(Amount) as TotalExpenses
    FROM ProjectExpense
    GROUP BY ProjectID, STRFTIME('%Y-%m', Date)
),

billable_exp AS (
    SELECT ProjectID, STRFTIME('%Y-%m', Date) AS Year_Month,
        SUM(Amount) as TotalBillableExpenses
    FROM ProjectExpense
    WHERE IsBillable = 1
    GROUP BY ProjectID, STRFTIME('%Y-%m', Date)
),

tb_tm AS (
    -- Time and Material projects charges by month
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
    GROUP BY Deliverable.ProjectID, STRFTIME('%Y-%m', Consultant_Deliverable.Date)
),

tb_fixed AS (
    -- Fixed projects charges by month using InvoicedDate
    SELECT Deliverable.ProjectID, 
        STRFTIME('%Y-%m', Deliverable.InvoicedDate) AS Year_Month,
        SUM(Deliverable.Price) as Amount
    FROM Deliverable
    LEFT JOIN Project 
        ON Deliverable.ProjectID = Project.ProjectID
    WHERE Project.Type = 'Fixed' and Deliverable.Status = 'Completed'
    GROUP BY Deliverable.ProjectID, STRFTIME('%Y-%m', Deliverable.InvoicedDate)
),

tb_combined AS (
    SELECT * FROM tb_tm
    UNION ALL
    SELECT * FROM tb_fixed
),

tb1 AS (
    SELECT 
        COALESCE(tb_combined.ProjectID, exp.ProjectID) AS ProjectID,
        COALESCE(tb_combined.Year_Month, exp.Year_Month) AS Year_Month,
        IFNULL(exp.TotalExpenses, 0) AS TotalExpenses,
        IFNULL(tb_combined.Amount, 0) AS TotalAmount
    FROM tb_combined
    LEFT JOIN exp
        ON tb_combined.ProjectID = exp.ProjectID
        AND tb_combined.Year_Month = exp.Year_Month

    UNION

    SELECT 
        COALESCE(tb_combined.ProjectID, exp.ProjectID) AS ProjectID,
        COALESCE(tb_combined.Year_Month, exp.Year_Month) AS Year_Month,
        IFNULL(exp.TotalExpenses, 0) AS TotalExpenses,
        IFNULL(tb_combined.Amount, 0) AS TotalAmount
    FROM exp
    LEFT JOIN tb_combined
        ON tb_combined.ProjectID = exp.ProjectID
        AND tb_combined.Year_Month = exp.Year_Month
),

tb2 AS (
    SELECT tb1.ProjectID, tb1.Year_Month, 
        IFNULL(tb1.TotalExpenses, 0) as TotalExpenses, 
        IFNULL(tb1.TotalAmount, 0) as TotalAmount,
        IFNULL(billable_exp.TotalBillableExpenses, 0) as TotalBillableExpenses,
        IFNULL(tb1.TotalAmount, 0) + 
            IFNULL(billable_exp.TotalBillableExpenses, 0) AS Revenue
    FROM tb1
    LEFT JOIN billable_exp
        ON tb1.ProjectID = billable_exp.ProjectID
        AND tb1.Year_Month = billable_exp.Year_Month
),

unit_rev AS (
    SELECT Project.UnitID, tb2.Year_Month, 
            SUM(TotalExpenses) as TotalExpenses,
            --SUM(TotalAmount) as TotalAmount,
            --SUM(TotalBillableExpenses) as TotalBillableExpenses,
            SUM(tb2.Revenue) as Revenue
    FROM tb2
    LEFT JOIN Project
        ON tb2.ProjectID = Project.ProjectID
    GROUP BY Project.UnitID, tb2.Year_Month
),

cons_pay AS (
    SELECT Consultant.BusinessUnitID, 
        STRFTIME('%Y-%m', Payroll.EffectiveDate) AS Year_Month,
        SUM(Payroll.Amount) as Payroll
    FROM Payroll
    LEFT JOIN Consultant
        ON Payroll.ConsultantID = Consultant.ConsultantID
    GROUP BY Consultant.BusinessUnitID, STRFTIME('%Y-%m', Payroll.EffectiveDate)
),

unit1 AS (
    SELECT unit_rev.UnitID, unit_rev.Year_Month, 
        IFNULL(Revenue, 0) as Revenue, 
        IFNULL(TotalExpenses, 0) as TotalExpenses,
        IFNULL(Payroll, 0) as Payroll,
        IFNULL(Revenue, 0) - IFNULL(Payroll, 0) - IFNULL(TotalExpenses, 0) as NetIncome
    FROM unit_rev
    LEFT JOIN cons_pay
        ON unit_rev.Year_Month = cons_pay.Year_Month
        AND unit_rev.UnitID = cons_pay.BusinessUnitID
)

-- SELECT UnitID, SUBSTRING(Year_Month, 1, 4) AS Year, 
--     SUM(Revenue) as Revenue
-- FROM unit1
-- GROUP BY UnitID, SUBSTRING(Year_Month, 1, 4)
-- ORDER BY UnitID, Year_Month

SELECT UnitID, Year_Month, Revenue, TotalExpenses, Payroll, NetIncome,
    SUM(Revenue) 
        OVER (PARTITION BY UnitID,
            SUBSTRING(Year_Month, 1, 4) ORDER BY Year_Month) AS CumulativeRevenue
    
FROM unit1 
-- WHERE SUBSTRING(Year_Month, 1, 4) = (
--     SELECT SUBSTRING(MAX(Year_Month)-1, 1, 4)
--     FROM unit1
-- )
ORDER BY UnitID, Year_Month

-- tb_tm1 AS (
--     SELECT ProjectID, SUBSTRING(DueDate, 1, 4) AS Year,
--         SUM(Hours * Rate) as Amount
--     FROM Deliverable
--     GROUP BY ProjectID, SUBSTRING(DueDate, 1, 4)
-- ),


------------------------------
-- PROJECT MANAGEMENT DATAMART
-- Project Status Fact Table
WITH exp AS (
    SELECT ProjectID, STRFTIME('%Y-%m', Date) AS Year_Month,
        SUM(Amount) as TotalExpenses
    FROM ProjectExpense
    GROUP BY ProjectID, STRFTIME('%Y-%m', Date)
),

billable_exp AS (
    SELECT ProjectID, STRFTIME('%Y-%m', Date) AS Year_Month,
        SUM(Amount) as TotalBillableExpenses
    FROM ProjectExpense
    WHERE IsBillable = 1
    GROUP BY ProjectID, STRFTIME('%Y-%m', Date)
),

tb_tm AS (
    -- Time and Material projects charges by month
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
    GROUP BY Deliverable.ProjectID, STRFTIME('%Y-%m', Consultant_Deliverable.Date)
),

tb_fixed AS (
    -- Fixed projects charges by month using InvoicedDate
    SELECT Deliverable.ProjectID, 
        STRFTIME('%Y-%m', Deliverable.InvoicedDate) AS Year_Month,
        SUM(Deliverable.Price) as Amount
    FROM Deliverable
    LEFT JOIN Project 
        ON Deliverable.ProjectID = Project.ProjectID
    WHERE Project.Type = 'Fixed' and Deliverable.Status = 'Completed'
    GROUP BY Deliverable.ProjectID, STRFTIME('%Y-%m', Deliverable.InvoicedDate)
),

tb_combined AS (
    SELECT * FROM tb_tm
    UNION ALL
    SELECT * FROM tb_fixed
),

tb1 AS (
    SELECT 
        COALESCE(tb_combined.ProjectID, exp.ProjectID) AS ProjectID,
        COALESCE(tb_combined.Year_Month, exp.Year_Month) AS Year_Month,
        IFNULL(exp.TotalExpenses, 0) AS TotalExpenses,
        IFNULL(tb_combined.Amount, 0) AS TotalAmount
    FROM tb_combined
    LEFT JOIN exp
        ON tb_combined.ProjectID = exp.ProjectID
        AND tb_combined.Year_Month = exp.Year_Month

    UNION

    SELECT 
        COALESCE(tb_combined.ProjectID, exp.ProjectID) AS ProjectID,
        COALESCE(tb_combined.Year_Month, exp.Year_Month) AS Year_Month,
        IFNULL(exp.TotalExpenses, 0) AS TotalExpenses,
        IFNULL(tb_combined.Amount, 0) AS TotalAmount
    FROM exp
    LEFT JOIN tb_combined
        ON tb_combined.ProjectID = exp.ProjectID
        AND tb_combined.Year_Month = exp.Year_Month
),

tb2 AS (
    SELECT tb1.ProjectID, tb1.Year_Month, 
        IFNULL(tb1.TotalExpenses, 0) as TotalExpenses, 
        IFNULL(tb1.TotalAmount, 0) as TotalAmount,
        IFNULL(billable_exp.TotalBillableExpenses, 0) as TotalBillableExpenses,
        IFNULL(tb1.TotalAmount, 0) + 
            IFNULL(billable_exp.TotalBillableExpenses, 0) AS Revenue
    FROM tb1
    LEFT JOIN billable_exp
        ON tb1.ProjectID = billable_exp.ProjectID
        AND tb1.Year_Month = billable_exp.Year_Month
),

payrollnew AS (
    SELECT c.ConsultantID, c.ProjectID, Year_Month,
        --SUM(c.Hours) OVER (PARTITION BY c.ConsultantID, Year_Month) AS TotalHours,
        --Hours / SUM(c.Hours) OVER (PARTITION BY c.ConsultantID, Year_Month) AS Percentage,
        p.Amount * Hours / SUM(c.Hours) OVER (PARTITION BY c.ConsultantID, Year_Month) AS Payroll
    FROM (SELECT c.ConsultantID, d.ProjectID, STRFTIME('%Y-%m', Date) AS Year_Month,
            SUM(c.Hours) AS Hours
        FROM Consultant_Deliverable c
        LEFT JOIN Deliverable d
            ON c.DeliverableID = d.DeliverableID
        GROUP BY c.ConsultantID, d.ProjectID, STRFTIME('%Y-%m', Date)) AS c
    LEFT JOIN Payroll p
        ON c.ConsultantID = p.ConsultantID
        AND STRFTIME('%Y-%m', p.EffectiveDate) = Year_Month
),

gp AS (
    SELECT ProjectID, Year_Month, SUM(Payroll) AS Payroll
    FROM payrollnew
    GROUP BY ProjectID, Year_Month)

SELECT tb2.ProjectID, 
        tb2.Year_Month, 
        p.ClientID,
        p.UnitID,
        p.Type,
        p.PlannedEndDate,
        p.Progress,
        tb2.Revenue, 
        tb2.TotalExpenses + gp.Payroll AS TotalCosts, 
        tb2.Revenue - tb2.TotalExpenses - gp.Payroll AS NetIncome
FROM tb2
LEFT JOIN gp
    ON tb2.ProjectID = gp.ProjectID
    AND tb2.Year_Month = gp.Year_Month
LEFT JOIN Project p 
    ON tb2.ProjectID = p.ProjectID
