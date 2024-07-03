-- check business unit Net Income by year and month --
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
        --IFNULL(billable_exp.TotalBillableExpenses, 0) AS TotalBillableExpenses,
        IFNULL(exp.TotalExpenses, 0) AS TotalExpenses,
        IFNULL(tb_combined.Amount, 0) AS TotalAmount
        --IFNULL(tb_combined.Amount, 0) + 
            --IFNULL(billable_exp.TotalBillableExpenses, 0) AS Revenue
    FROM tb_combined
    LEFT JOIN exp
        ON tb_combined.ProjectID = exp.ProjectID
        AND tb_combined.Year_Month = exp.Year_Month
    --LEFT JOIN billable_exp
        --ON tb_combined.ProjectID = billable_exp.ProjectID
        --AND tb_combined.Year_Month = billable_exp.Year_Month

    UNION

    SELECT 
        COALESCE(tb_combined.ProjectID, exp.ProjectID) AS ProjectID,
        COALESCE(tb_combined.Year_Month, exp.Year_Month) AS Year_Month,
        --IFNULL(billable_exp.TotalBillableExpenses, 0) AS TotalBillableExpenses,
        IFNULL(exp.TotalExpenses, 0) AS TotalExpenses,
        IFNULL(tb_combined.Amount, 0) AS TotalAmount
        --IFNULL(tb_combined.Amount, 0) + 
            --IFNULL(billable_exp.TotalBillableExpenses, 0) AS Revenue
    FROM exp
    LEFT JOIN tb_combined
        ON tb_combined.ProjectID = exp.ProjectID
        AND tb_combined.Year_Month = exp.Year_Month
    --LEFT JOIN billable_exp
        --ON tb_combined.ProjectID = billable_exp.ProjectID
        --AND tb_combined.Year_Month = billable_exp.Year_Month
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
)

SELECT unit_rev.UnitID, unit_rev.Year_Month, 
    IFNULL(Revenue, 0) as Revenue, 
    IFNULL(TotalExpenses, 0) as TotalExpenses,
    IFNULL(Payroll, 0) as Payroll,
    IFNULL(Revenue, 0) - IFNULL(Payroll, 0) - IFNULL(TotalExpenses, 0) as NetIncome
FROM unit_rev
LEFT JOIN cons_pay
    ON unit_rev.Year_Month = cons_pay.Year_Month
    AND unit_rev.UnitID = cons_pay.BusinessUnitID


---- Test Consultant Working Hours ----
SELECT ConsultantID, Date, SUM(Hours) AS TotalHours
from Consultant_Deliverable
GROUP BY ConsultantID, Date
HAVING TotalHours > 24


--------------------------------------------------------------

------------ Below are old queries, use the above ------------

--------------------------------------------------------------



-- check payroll data in business unit
SELECT *
FROM Payroll
WHERE ConsultantID IN (
    SELECT ConsultantID
    FROM Consultant
    WHERE BusinessUnitID = 2
)

--Check conmpleted fixed deliverables
SELECT STRFTIME('%Y-%m', InvoicedDate) as Year_Month, SUM(Price) as Revenue
from Deliverable
where Status = 'Completed'
GROUP BY STRFTIME('%Y-%m', InvoicedDate)

-- check billable
select *
from ProjectExpense
where IsBillable = 1

--check project
select *
from Deliverable
left join Project
where Project.UnitID = 3

--------------------------------------------------------------

-- check unit Net Income
WITH exp AS (
    SELECT ProjectID, STRFTIME('%Y-%m', Date) AS Year_Month,
        SUM(CASE WHEN IsBillable = 1 THEN Amount
                ELSE -Amount
            END) as TotalExpenses
    FROM ProjectExpense
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
        IFNULL(tb_combined.Amount, 0) AS TotalAmount,
        IFNULL(tb_combined.Amount, 0) + IFNULL(exp.TotalExpenses, 0) AS Revenue
    FROM tb_combined
    LEFT JOIN exp
        ON tb_combined.ProjectID = exp.ProjectID
        AND tb_combined.Year_Month = exp.Year_Month

    UNION

    SELECT 
        COALESCE(tb_combined.ProjectID, exp.ProjectID) AS ProjectID,
        COALESCE(tb_combined.Year_Month, exp.Year_Month) AS Year_Month,
        IFNULL(exp.TotalExpenses, 0) AS TotalExpenses,
        IFNULL(tb_combined.Amount, 0) AS TotalAmount,
        IFNULL(tb_combined.Amount, 0) + IFNULL(exp.TotalExpenses, 0) AS Revenue
    FROM exp
    LEFT JOIN tb_combined
        ON tb_combined.ProjectID = exp.ProjectID
        AND tb_combined.Year_Month = exp.Year_Month
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