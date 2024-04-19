CREATE TABLE `Client` (
  `ClientID` int PRIMARY KEY AUTO_INCREMENT,
  `FirstName` varchar(255) NOT NULL,
  `LastName` varchar(255) NOT NULL,
  `CompanyName` varchar(255),
  `PhoneNumber` varchar(50),
  `Email` varchar(255) NOT NULL,
  `Address` varchar(255) NOT NULL
);

CREATE TABLE `Project` (
  `ProjectID` int PRIMARY KEY AUTO_INCREMENT,
  `ClientID` int NOT NULL,
  `Name` varchar(255) NOT NULL,
  `Type` varchar(100) NOT NULL,
  `Status` varchar(100) NOT NULL DEFAULT 'Active',
  `Price` decimal(10,2),
  `PlanHour` decimal(10,2),
  `CreatedAt` timestamp DEFAULT (now())
);

CREATE TABLE `Title` (
  `TitleID` int PRIMARY KEY AUTO_INCREMENT,
  `RoleTitle` varchar(255) NOT NULL
);

CREATE TABLE `Project_Actual_Hour` (
  `ActualTimeID` int PRIMARY KEY AUTO_INCREMENT,
  `ProjectID` int NOT NULL,
  `StartTime` timestamp NOT NULL,
  `EndTime` timestamp NOT NULL
);

CREATE TABLE `Project_Billing_Rate` (
  `BillingRateID` int PRIMARY KEY AUTO_INCREMENT,
  `ProjectID` int NOT NULL,
  `TitleID` int NOT NULL,
  `Rate` decimal(10,2) NOT NULL
);

CREATE TABLE `Deliverable` (
  `DeliverableID` int PRIMARY KEY AUTO_INCREMENT,
  `ProjectID` int NOT NULL,
  `Title` varchar(255) NOT NULL,
  `StartDate` timestamp,
  `DueDate` timestamp NOT NULL,
  `Status` varchar(100) NOT NULL DEFAULT 'Pending',
  `Price` decimal(10,2),
  `SubmissionDate` date
);

CREATE TABLE `DeliverablePlan` (
  `PlanID` int PRIMARY KEY AUTO_INCREMENT,
  `DeliverableID` int NOT NULL,
  `StartDatePlan` timestamp NOT NULL,
  `EndDatePlan` timestamp NOT NULL
);

CREATE TABLE `Consultant` (
  `ConsultantID` int PRIMARY KEY AUTO_INCREMENT,
  `EntryTitleID` int NOT NULL,
  `FirstName` varchar(255) NOT NULL,
  `LastName` varchar(255),
  `Contact` varchar(255)
);

CREATE TABLE `Consultant_Working_Session` (
  `ID` int PRIMARY KEY AUTO_INCREMENT,
  `ConsultantID` int NOT NULL,
  `ProjectID` int NOT NULL,
  `Time` int
);

CREATE TABLE `Consultant_Title_History` (
  `ID` int PRIMARY KEY AUTO_INCREMENT,
  `ConsultantID` int NOT NULL,
  `TitleID` int NOT NULL,
  `StartDate` timestamp NOT NULL,
  `EndDate` timestamp
);

CREATE TABLE `Payroll` (
  `PayRollID` int PRIMARY KEY AUTO_INCREMENT,
  `ConsultantID` int NOT NULL,
  `Amount` decimal(10,2),
  `EffectiveDate` timestamp
);

CREATE TABLE `Consultant_Expense` (
  `ExpenseID` int PRIMARY KEY AUTO_INCREMENT,
  `ConsultantID` int NOT NULL,
  `ProjectID` int NOT NULL,
  `Date` timestamp NOT NULL,
  `Amount` decimal(10,2) NOT NULL,
  `Description` text NOT NULL
);

CREATE TABLE `Project_Expense` (
  `ProjectExpenseID` int PRIMARY KEY AUTO_INCREMENT,
  `ProjectID` int NOT NULL,
  `Date` timestamp NOT NULL,
  `Amount` decimal(10,2) NOT NULL,
  `Description` text NOT NULL,
  `Category` varchar(255)
);

ALTER TABLE `Project` ADD FOREIGN KEY (`ClientID`) REFERENCES `Client` (`ClientID`);

ALTER TABLE `Project_Actual_Hour` ADD FOREIGN KEY (`ProjectID`) REFERENCES `Project` (`ProjectID`);

ALTER TABLE `Project_Billing_Rate` ADD FOREIGN KEY (`ProjectID`) REFERENCES `Project` (`ProjectID`);

ALTER TABLE `Project_Billing_Rate` ADD FOREIGN KEY (`TitleID`) REFERENCES `Title` (`TitleID`);

ALTER TABLE `Deliverable` ADD FOREIGN KEY (`ProjectID`) REFERENCES `Project` (`ProjectID`);

ALTER TABLE `DeliverablePlan` ADD FOREIGN KEY (`DeliverableID`) REFERENCES `Deliverable` (`DeliverableID`);

ALTER TABLE `Consultant` ADD FOREIGN KEY (`EntryTitleID`) REFERENCES `Title` (`TitleID`);

ALTER TABLE `Consultant_Working_Session` ADD FOREIGN KEY (`ConsultantID`) REFERENCES `Consultant` (`ConsultantID`);

ALTER TABLE `Consultant_Working_Session` ADD FOREIGN KEY (`ProjectID`) REFERENCES `Project` (`ProjectID`);

ALTER TABLE `Consultant_Title_History` ADD FOREIGN KEY (`ConsultantID`) REFERENCES `Consultant` (`ConsultantID`);

ALTER TABLE `Consultant_Title_History` ADD FOREIGN KEY (`TitleID`) REFERENCES `Title` (`TitleID`);

ALTER TABLE `Payroll` ADD FOREIGN KEY (`ConsultantID`) REFERENCES `Consultant` (`ConsultantID`);

ALTER TABLE `Consultant_Expense` ADD FOREIGN KEY (`ConsultantID`) REFERENCES `Consultant` (`ConsultantID`);

ALTER TABLE `Consultant_Expense` ADD FOREIGN KEY (`ProjectID`) REFERENCES `Project` (`ProjectID`);

ALTER TABLE `Project_Expense` ADD FOREIGN KEY (`ProjectID`) REFERENCES `Project` (`ProjectID`);
