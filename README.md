LifeSecure Insurance — Claims Processing PoC

Project Overview

LifeSecure Insurance is a Proof of Concept (PoC) for an insurance claims processing system. It demonstrates how API integration and polyglot persistence can support claim processing, data storage, and the identification of related insurance claims for review.

Objectives

- Demonstrate API integration using FastAPI.
- Store structured insurance records in PostgreSQL.
- Use Neo4j to represent relationships between customers, policies, and claims.
- Identify related claims that may require further review.

Technologies Used

- Python
- FastAPI
- PostgreSQL 16
- Neo4j 5
- Docker Compose
- Postman

Architecture

The application uses FastAPI to receive and process claim requests. PostgreSQL stores structured claim records and their statuses, while Neo4j stores relationships between customers, policies, and claims.

When related claims are identified within the configured 30-day period, the system flags the claim for human review. A flagged claim is not automatically considered fraudulent.

Main Features

- API-based claim submission
- Policy validation
- PostgreSQL claim storage
- Neo4j relationship mapping
- Related-claim detection
- Claim flagging for review

Prerequisites

Install the following before running the project:

- Python
- Docker Desktop
- Git

Setup Instructions

1. Clone or download this repository.

2. Create a ".env" file using the required database configuration.

3. Start the databases using Docker Compose:
   
   docker compose up -d

4. Create and activate a Python virtual environment.

5. Install the dependencies:
   
   pip install -r requirements.txt

6. Start the FastAPI application:
   
   python -m uvicorn app.main:app --reload

7. Open the API documentation in your browser:
   
   http://127.0.0.1:8000/docs

Testing

Use Postman or the FastAPI interactive documentation to submit claim requests and test the API endpoints.

Project Limitations

This project is a Proof of Concept for academic purposes. Related-claim detection is intended to support human review and does not establish fraud. The system does not represent a complete production insurance platform.

Academic Project

Developed as part of an academic project demonstrating API integration and polyglot persistence in insurance claim processing.