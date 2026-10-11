from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

REQUEST_COUNTER = Counter("scam_detector_requests_total", "Total API requests")
REQUEST_LATENCY = Histogram("scam_detector_request_latency_seconds", "Request latency")
RETRIEVAL_REQUESTS = Counter("scam_detector_retrieval_requests_total", "Total retrieval requests")
RETRIEVAL_HITS = Counter("scam_detector_retrieval_hits_total", "Total retrieval hits with matched context")
RETRIEVAL_FALLBACKS = Counter("scam_detector_retrieval_fallbacks_total", "Total retrieval fallbacks to direct LLM")
DATASET_INGESTION_CHUNKS = Counter("scam_detector_dataset_ingestion_chunks_total", "Total chunks ingested from datasets")
DATASET_INGESTION_RECORDS = Counter("scam_detector_dataset_ingestion_records_total", "Total records ingested from datasets")


def metrics_payload() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST


def track_retrieval_request(match_count: int) -> None:
    RETRIEVAL_REQUESTS.inc()
    if match_count > 0:
        RETRIEVAL_HITS.inc()
    else:
        RETRIEVAL_FALLBACKS.inc()


def track_dataset_ingestion(records: int, chunks: int) -> None:
    if records > 0:
        DATASET_INGESTION_RECORDS.inc(records)
    if chunks > 0:
        DATASET_INGESTION_CHUNKS.inc(chunks)
