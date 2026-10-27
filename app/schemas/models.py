from pydantic import BaseModel
from typing import Dict, Any

class SourceDocument(BaseModel):
    content: str
    metadata: Dict[str, Any]

class AnswerResponse(BaseModel):
    status: bool
    query: str
    answer: str

class AskRequest(BaseModel):
    chat_id: str
    query: str
    is_premium: bool = False