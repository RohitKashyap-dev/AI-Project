from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    message: str = Field(min_length=1)
    model_name: str | None = None
    user_id: int | None = None
    session_id: str | None = None


class AnalyzeResponse(BaseModel):
    task_id: str
    status: str = "queued"
    message: str
    result: dict | None = None

    def __getitem__(self, item):
        return self.model_dump().get(item)

    def get(self, item, default=None):
        return self.model_dump().get(item, default)
