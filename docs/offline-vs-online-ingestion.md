# Offline vs Online Ingestion

This project has two distinct data pipelines.

## 1. Offline ingestion

This is the batch pipeline used to prepare and index the knowledge base before the app can answer live questions well.

### Responsibilities
- load raw dataset
- clean the text
- split into chunks
- generate embeddings
- store vectors in the database
- build retrieval knowledge

### Current implementation
- [backend/services/dataset_ingestion.py](../backend/services/dataset_ingestion.py)
- [backend/services/chunking_service.py](../backend/services/chunking_service.py)
- [backend/services/embedding_service.py](../backend/services/embedding_service.py)
- [backend/services/vector_store.py](../backend/services/vector_store.py)
- [backend/services/retrieval_service.py](../backend/services/retrieval_service.py)
- [backend/api/routes/retrieval.py](../backend/api/routes/retrieval.py)

### In Spring terms
This is the data preparation / indexing layer.

## 2. Online ingestion

This is the live request pipeline used when a user submits a message in the app.

### Responsibilities
- accept incoming user message
- validate request
- query matched knowledge from vector DB
- run scam classification
- format response
- return answer to UI
- optionally queue background jobs

### Current implementation
- [backend/api/routes/analyze.py](../backend/api/routes/analyze.py)
- [backend/services/rag_classifier.py](../backend/services/rag_classifier.py)
- [backend/tasks/classify_task.py](../backend/tasks/classify_task.py)
- [scam_detector/classifier.py](../scam_detector/classifier.py)
- [scam_detector/graph_rag.py](../scam_detector/graph_rag.py)

### In Spring terms
This is the online request-processing / inference layer.

## Simple definition

- Offline ingestion = build knowledge before runtime
- Online ingestion = process live user requests at runtime

## Recommended final architecture

```text
project/
├── backend/
│   ├── api/
│   ├── core/
│   ├── db/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   │   ├── offline_ingestion/
│   │   │   ├── dataset_ingestion.py
│   │   │   ├── chunking_service.py
│   │   │   ├── embedding_service.py
│   │   │   └── vector_indexer.py
│   │   └── online_ingestion/
│   │       ├── message_ingestion_service.py
│   │       ├── retrieval_service.py
│   │       └── classify_request_service.py
│   └── tasks/
│       └── classify_task.py
│
├── scam_detector/
│   ├── classifier.py
│   ├── graph_rag.py
│   ├── response_parser.py
│   ├── schemas.py
│   └── ...
│
├── ui/
│   └── streamlit_app.py
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── predictions/
└── ...
```

This split is the most natural way to explain the project.
