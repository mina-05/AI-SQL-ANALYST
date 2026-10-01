#!/bin/bash
# Runs once, inside the MySQL container, after schema.sql (see docker-compose.yml).
set -e
mysql -uroot -p"$MYSQL_ROOT_PASSWORD" <<SQL
CREATE USER IF NOT EXISTS 'analyst_ro'@'%' IDENTIFIED BY '${ANALYST_PASSWORD}';
GRANT SELECT ON company.* TO 'analyst_ro'@'%';
FLUSH PRIVILEGES;
SQL
