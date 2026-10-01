# AI SQL Analyst

An AI-powered database assistant that converts natural-language questions into safe SQL queries, executes them against MySQL, and presents the results with explanations and visualizations.

## Overview

**AI SQL Analyst** allows users to interact with a MySQL database using plain English instead of manually writing SQL.

The application uses a local **Ollama LLM** to generate SQL, validates the generated query against read-only security rules, executes it through a restricted MySQL account, and presents the results in an interactive web interface.

For complex questions, **Deep Analysis** uses an agent workflow that can inspect the database schema, search business documentation, execute multiple queries, and produce a final evidence-based response.

### Architecture

```text
                         ┌── Quick Query ──► LLM ──► SQL Validator ──► MySQL
                         │                                      │
User ──► Authentication ┤                                      ▼
                         │                              Results + Chart
                         │                                      │
                         │                                      ▼
                         │                                  Explanation
                         │
                         └── Deep Analysis ──► Agent
                                               │
                                               ├── Inspect Schema
                                               ├── Search Documents
                                               ├── Execute SQL
                                               └── Generate Final Answer
```

---

## Key Features

### Natural Language to SQL

* Ask database questions using plain English.
* Local LLM generates SQL using Ollama.
* Automatically uses the connected database schema.
* Displays generated SQL alongside the results.

### SQL Safety & Validation

* Allows only read-only `SELECT` queries.
* Blocks destructive SQL operations.
* Prevents dangerous functions such as `SLEEP` and `LOAD_FILE`.
* Uses a dedicated MySQL user with `SELECT`-only permissions.
* Limits the maximum number of returned rows.

### Automatic SQL Repair

If generated SQL fails:

```text
Question
   ↓
Generate SQL
   ↓
Validate
   ↓
Execute
   ↓
SQL Error?
   ↓
LLM analyzes the error
   ↓
Generate corrected SQL
   ↓
Validate + Execute again
```

### Query Analysis

The application supports:

* Query explanations
* Query optimization suggestions
* MySQL `EXPLAIN` plans
* Automatic chart recommendations
* Result summaries and insights

### Deep Analysis Agent

For questions that require multiple steps, the agent can:

* Inspect database schema
* Search business documents
* Execute multiple SQL queries
* Analyze intermediate results
* Maintain a visible execution trace
* Generate a final answer based on query results

Example:

> **Why is the IT department's average salary higher than HR?**

The agent can investigate the relevant departments and compare the underlying data instead of relying on a single query.

### RAG — Business Knowledge

Business documentation can be placed inside the `knowledge/` directory.

The application supports:

* Keyword-based retrieval
* Embedding-based retrieval
* Ollama embedding models
* Automatic inclusion of relevant documentation in LLM prompts

### Authentication & Memory

* User registration and login
* JWT-based authentication
* Password hashing using PBKDF2
* Expiring authentication tokens
* Per-user query history
* Conversation memory
* Separate conversations for different analysis sessions

### Testing & CI

* **55 automated tests**
* Pytest test suite
* GitHub Actions CI
* API, authentication, RAG, SQL validation, repair, charts, and agent testing

---

# Technology Stack

| Layer            | Technology                    |
| ---------------- | ----------------------------- |
| Backend          | Python, FastAPI               |
| Database         | MySQL                         |
| ORM / DB Access  | SQLAlchemy, PyMySQL           |
| AI / LLM         | Ollama, Qwen2.5-Coder         |
| RAG              | Keyword / Embedding Retrieval |
| Authentication   | JWT, PBKDF2                   |
| Data Processing  | Pandas                        |
| Frontend         | HTML, CSS, JavaScript         |
| Testing          | Pytest                        |
| Containerization | Docker, Docker Compose        |
| CI/CD            | GitHub Actions                |

---

# Project Architecture

```text
ai-sql-analyst/
│
├── app/
│   ├── main.py
│   ├── agent.py
│   ├── auth.py
│   ├── chart.py
│   ├── config.py
│   ├── db.py
│   ├── llm.py
│   ├── rag.py
│   ├── repair.py
│   ├── store.py
│   └── validator.py
│
├── database/
│   ├── docker/
│   ├── readonly_user.sql
│   └── schema.sql
│
├── frontend/
│   └── index.html
│
├── knowledge/
│   └── business_rules.md
│
├── tests/
│   ├── test_agent.py
│   ├── test_api.py
│   ├── test_auth.py
│   ├── test_chart.py
│   ├── test_rag.py
│   ├── test_repair.py
│   └── test_validator.py
│
├── .github/
│   └── workflows/
│       └── tests.yml
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── requirements-dev.txt
├── .env.example
└── README.md
```

---

# How It Works

## 1. Quick Query

```text
User Question
      ↓
Authentication
      ↓
Database Schema
      ↓
RAG Context
      ↓
Ollama LLM
      ↓
SQL Generation
      ↓
SQL Validator
      ↓
MySQL
      ↓
DataFrame
      ↓
Chart + Insight
```

Example:

> Show the average salary by department.

The application generates a SQL query, validates it, executes it, and displays the resulting data and visualization.

---

## 2. Deep Analysis

Deep Analysis is designed for questions that require multiple database operations.

```text
User Question
      ↓
Agent
      ↓
┌───────────────────────┐
│ Inspect Schema        │
│ Search Documents      │
│ Execute SQL           │
│ Analyze Results       │
└───────────────────────┘
      ↓
Final Answer
```

The execution trace allows users to understand how the agent reached its answer.

---

# Security Design

Security is implemented at multiple layers.

### Application Layer

The SQL validator:

* Allows only approved read-only queries
* Rejects write operations
* Rejects dangerous SQL functions
* Handles SQL comments and quoted content
* Limits query result size

### Database Layer

The application does **not** use the MySQL root account.

Instead, it connects using a dedicated read-only account:

```text
Application
     ↓
analyst_ro
     ↓
SELECT permission only
     ↓
MySQL
```

This provides an additional layer of protection if the generated SQL is incorrect.

### Application Security

* Passwords are stored as salted PBKDF2 hashes.
* JWT sessions expire after a configurable period.
* Database output is HTML-escaped before rendering.
* Secrets are loaded from environment variables rather than hard-coded in source code.

> **Never commit `.env` or production credentials to GitHub.**

---

# Local Development

## Prerequisites

Install:

* Python 3.11+
* MySQL 8+
* Ollama
* Git

---

## 1. Clone the Repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd ai-sql-analyst
```

---

## 2. Create a Virtual Environment

### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### Linux / macOS

```bash
python -m venv .venv
source .venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements-dev.txt
```

---

## 4. Configure MySQL

Create the sample database:

```bash
mysql -u root -p < database/schema.sql
```

Create the read-only application user:

```bash
mysql -u root -p < database/readonly_user.sql
```

Update the credentials in the SQL script before running it.

---

## 5. Configure Environment Variables

Copy the example environment file:

### Windows

```powershell
copy .env.example .env
```

### Linux / macOS

```bash
cp .env.example .env
```

Configure:

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=analyst_ro
DB_PASSWORD=your_database_password
DB_NAME=company

OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:7b

SECRET_KEY=your_secret_key
```

Generate a secure secret key with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

---

# Ollama Setup

Install Ollama and download the coding model:

```bash
ollama pull qwen2.5-coder:7b
```

For embedding-based RAG:

```bash
ollama pull nomic-embed-text
```

Then configure:

```env
RAG_MODE=embeddings
```

The application can fall back to keyword retrieval when embeddings are unavailable.

---

# Run the Application

Start the FastAPI server:

```bash
uvicorn app.main:app --reload
```

Open:

```text
http://localhost:8000
```

Create an account and start querying the database.

---

# Example Questions

Try questions such as:

```text
Show all employees
```

```text
What is the average salary?
```

```text
Show average salary by department
```

```text
Who are the top 5 highest paid employees?
```

```text
How many employees are in each department?
```

```text
Show employees earning more than 50000
```

```text
Which department has the highest average salary?
```

For Deep Analysis:

```text
Why is the IT average salary higher than HR?
```

---

# Running Tests

The test suite does not require MySQL or Ollama.

```bash
pytest
```

Current test suite:

```text
55 tests passed
```

---

# Docker Deployment

Create your environment file:

```bash
cp .env.example .env
```

Configure:

```env
DB_PASSWORD=your_database_password
MYSQL_ROOT_PASSWORD=your_root_password
SECRET_KEY=your_secret_key
```

Build and start:

```bash
docker compose up --build
```

The application will be available at:

```text
http://localhost:8000
```

Ollama can continue running on the host machine.

For Docker-to-host Ollama access, configure:

```env
OLLAMA_URL_DOCKER=http://host.docker.internal:11434
```

---

# Deployment Considerations

For production deployment:

* Use strong, unique credentials.
* Store secrets using environment variables or a secrets manager.
* Place the application behind HTTPS.
* Use Caddy, Nginx, or another reverse proxy.
* Do not expose MySQL directly to the public internet.
* Disable public registration after creating required accounts.
* Use a dedicated read-only database account.
* Monitor application and database logs.
* Consider rate limiting and account lockout for authentication endpoints.
* Use an appropriately sized machine for local LLM inference.

---
## Screenshots

 # login
 ![alt text](<Screenshot (470).png>)

 # Dashboard
 ![alt text](<Screenshot (471).png>) 

 # Quick Query
 ![alt text](<Screenshot (472).png>) 

 # Deep Analysis
 ![alt text](<Screenshot (473).png>) 
 ![alt text](<Screenshot (474).png>)

# Potential future enhancements include:

* Role-based access control
* Database-level row and column security
* Rate limiting
* Streaming LLM responses
* More database integrations such as PostgreSQL
* Advanced vector databases for RAG
* Model selection from the UI
* Query performance monitoring
* Production-grade observability
* Cloud deployment
* Automated evaluation of generated SQL

---

# Project Highlights

This project demonstrates practical experience with:

* **Generative AI**
* **LLM integration**
* **Natural Language to SQL**
* **RAG**
* **AI agents**
* **Prompt engineering**
* **FastAPI**
* **MySQL**
* **SQLAlchemy**
* **JWT authentication**
* **Secure password hashing**
* **Docker**
* **GitHub Actions**
* **Automated testing**
* **Data visualization**
* **Database security**

---

## Author

**Mina**

---

## License

This project is intended for learning, demonstration, and portfolio purposes.
