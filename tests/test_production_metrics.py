from backend.core import monitoring


def test_tracking_retrieval_and_ingestion_metrics():
    before = monitoring.RETRIEVAL_REQUESTS._value.get()
    monitoring.track_retrieval_request(2)
    assert monitoring.RETRIEVAL_REQUESTS._value.get() == before + 1
    assert monitoring.RETRIEVAL_HITS._value.get() >= 1

    before_records = monitoring.DATASET_INGESTION_RECORDS._value.get()
    before_chunks = monitoring.DATASET_INGESTION_CHUNKS._value.get()
    monitoring.track_dataset_ingestion(7, 12)
    assert monitoring.DATASET_INGESTION_RECORDS._value.get() == before_records + 7
    assert monitoring.DATASET_INGESTION_CHUNKS._value.get() == before_chunks + 12
