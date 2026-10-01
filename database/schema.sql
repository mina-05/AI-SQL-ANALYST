CREATE DATABASE IF NOT EXISTS company;
USE company;

DROP TABLE IF EXISTS employees;

CREATE TABLE employees (
    id           INT PRIMARY KEY AUTO_INCREMENT,
    name         VARCHAR(100) NOT NULL,
    department   VARCHAR(50)  NOT NULL,
    salary       DECIMAL(10,2) NOT NULL,
    joining_date DATE NOT NULL
);

INSERT INTO employees (name, department, salary, joining_date) VALUES
('Aarav Sharma',   'IT',      95000, '2019-03-12'),
('Diya Reddy',     'IT',     120000, '2017-07-01'),
('Kabir Singh',    'IT',      88000, '2021-01-18'),
('Ananya Iyer',    'IT',     105000, '2018-11-05'),
('Rohan Mehta',    'HR',      62000, '2020-02-10'),
('Priya Nair',     'HR',      68000, '2019-09-23'),
('Isha Kapoor',    'HR',      59000, '2022-04-04'),
('Vikram Rao',     'Finance', 82000, '2016-05-30'),
('Sneha Patel',    'Finance', 91000, '2018-08-14'),
('Arjun Das',      'Finance', 76000, '2021-06-21'),
('Meera Joshi',    'Finance', 85000, '2020-10-09'),
('Karthik Menon',  'Sales',   70000, '2019-12-02'),
('Neha Verma',     'Sales',   64000, '2022-01-17'),
('Siddharth Bose', 'Sales',   78000, '2017-03-27'),
('Tanvi Desai',    'Sales',   66000, '2023-02-13'),
('Rahul Gupta',    'Marketing', 72000, '2018-05-08'),
('Pooja Chawla',   'Marketing', 69000, '2021-09-15'),
('Aditya Kulkarni','Marketing', 75000, '2020-07-29');
