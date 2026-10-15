# Spring Boot Style Mapping

The project is best understood as three main modules:

```text
backend/ = app
scam_detector/ = AI engine
ui/ = frontend
```

## Backend app

```text
backend/
├── api/
├── core/
├── db/
├── models/
├── schemas/
├── services/
├── tasks/
├── bootstrap.py
└── ...
```

This is the application backend. It handles auth, routes, DB access, and orchestration.

## AI engine

```text
scam_detector/
├── classifier.py
├── graph_rag.py
├── response_parser.py
├── schemas.py
├── llm_client.py
├── prompts.py
├── ...
```

This is the intelligence layer that classifies messages and validates AI output.

## Frontend

```text
ui/
└── streamlit_app.py

app.py
```

This is the user-facing interface.

## Spring Boot comparison

```text
Spring Boot        This project
------------------------------------
Controller         backend/api
Service            backend/services + backend/tasks
Repository         backend/db + backend/models
Security/Config   backend/core
AI Engine          scam_detector/
Frontend           ui/
```

This is the cleanest way to map the project to a Spring Boot style architecture without overcomplicating the folder structure.
