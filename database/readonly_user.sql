-- Local setup only. Run as a MySQL admin AFTER schema.sql, and change the password.
CREATE USER IF NOT EXISTS 'analyst_ro'@'localhost' IDENTIFIED BY 'change_me';
GRANT SELECT ON company.* TO 'analyst_ro'@'localhost';
FLUSH PRIVILEGES;
