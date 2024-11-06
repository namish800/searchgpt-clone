from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class Message(BaseModel):
    content: str
    role: MessageRole


class ChatRequest(BaseModel):
    query: str
    history: List[Message] = []
    llm_model_name: Optional[str] = None


class QueryPlanStep(BaseModel):
    id: int = Field(..., description="Unique id of the step")
    step: str
    dependencies: list[int] = Field(
        ...,
        description="List of step ids that this step depends on information from",
        default_factory=list,
    )


class QueryPlan(BaseModel):
    steps: list[QueryPlanStep] = Field(
        ..., description="The steps to complete the query", max_length=4
    )


class StepContext(BaseModel):
    step: str
    context: str


class QueryStepExecution(BaseModel):
    search_queries: list[str] = Field(
        ...,
        description="The search queries to complete the step",
        min_length=1,
        max_length=3,
    )


class SearchResult(BaseModel):
    url: str
    content: str

    def __str__(self):
        return f"URL: {self.url}\n Summary: {self.content}"


class SingleStepResults(BaseModel):
    step: str
    results: List[SearchResult]


class StepSearchResultsTracker(BaseModel):
    results: List[SingleStepResults]

