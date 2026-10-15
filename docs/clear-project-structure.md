# Final Project Structure

This is the clean structure we will use for the project.

## 1) Backend app

```text
backend/
├── api/
│   ├── app.py
│   └── routes/
│       ├── auth.py
│       ├── analyze.py
│       ├── health.py
│       ├── retrieval.py
│       ├── vector.py
│       ├── dataset.py
│       ├── bootstrap.py
│       └── metrics.py
├── core/
│   ├── config.py
│   ├── security.py
│   ├── celery_app.py
│   ├── monitoring.py
│   ├── migration_runner.py
│   ├── healthcheck.py
│   └── secrets.py
├── db/
│   ├── base.py
│   ├── session.py
│   ├── init_db.py
│   └── ...
├── models/
│   ├── user.py
│   ├── knowledge_chunk.py
│   ├── message.py
│   └── ...
├── schemas/
│   ├── auth.py
│   ├── analyze.py
│   └── ...
├── services/
│   ├── rag_classifier.py
│   ├── retrieval_service.py
│   ├── vector_store.py
│   ├── embedding_service.py
│   ├── dataset_ingestion.py
│   └── ...
├── tasks/
│   └── classify_task.py
├── bootstrap.py
└── ...
```

This is the application layer.

## 2) AI engine

```text
scam_detector/
├── __init__.py
├── classifier.py
├── graph_rag.py
├── llm_client.py
├── prompts.py
├── response_parser.py
├── schemas.py
├── utils.py
├── service.py
├── auth.py
├── config.py
├── users.py
├── evaluation.py
├── cli.py
└── ...
```

This is the AI intelligence module that decides scam vs safe classification.

## 3) Frontend UI

```text
ui/
└── streamlit_app.py

app.py
```

This is the UI client for the end-user experience.

## Final mental model

```text
backend/ = app
scam_detector/ = AI engine
ui/ = frontend
```

Everything else like data, logs, tests, notebooks, scripts, and configs sit around these main folders as support files.

This is the cleanest and easiest structure to relate with a Spring Boot backend + AI module + frontend client setup.
