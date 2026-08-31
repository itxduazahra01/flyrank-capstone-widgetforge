# WidgetForge – Embeddable Widget & Lead Capture Platform

WidgetForge is a web application for creating embeddable widgets and collecting leads through customizable forms.

## Features

* User authentication
* Create and manage widgets
* Customizable form fields
* Embeddable public widgets
* Lead/submission collection
* Lead management and status tracking
* Dashboard and analytics
* PostgreSQL database
* Background worker for event processing
* API documentation with Swagger

## Tech Stack

**Backend**

* Python
* FastAPI
* SQLAlchemy
* Alembic
* PostgreSQL

**Frontend**

* React
* TypeScript
* Vite

**DevOps**

* Docker
* Docker Compose

## Running the Project

### 1. Start the application

```bash
docker compose up -d
```

### 2. Seed demo data

```bash
docker compose exec api python scripts/seed_demo.py
```

### 3. Access the API

Swagger API documentation:

```text
http://localhost:8000/docs
```

### Demo Login

```text
Email: alice@acme.test
Password: DemoPass123!
```

## Project Structure

```text
app/          Backend application
frontend/     React frontend
customer-site/ Embeddable widget demo
alembic/      Database migrations
scripts/      Database and worker scripts
tests/        Automated tests
docs/         Project documentation
```

## Author

Dua Zahra
