# Company data guide (sample - replace with your own business rules)

## Salary
Every value in employees.salary is a monthly gross salary in Indian rupees (INR).
When a user says "pay", "compensation" or "earnings" they mean the salary column.

## Departments
The company has five departments: IT, HR, Finance, Sales and Marketing.
The department column stores the department name exactly as written here.

## Seniority
An employee who joined before 2019-01-01 is considered senior.
Tenure is the time between joining_date and today.

## Reporting rules
Averages and totals should be reported per department unless the user asks for something else.
Do not report individual salaries unless the user asks for a specific list of employees.
