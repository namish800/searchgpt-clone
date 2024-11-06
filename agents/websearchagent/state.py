import operator
from typing import TypedDict, Annotated, List

from langgraph.graph import add_messages
from pydantic import BaseModel, Field

from schemas import ChatRequest, QueryPlan, StepSearchResultsTracker, SingleStepResults, Message


class WebSearchState(BaseModel):
    request: ChatRequest = None
    messages: Annotated[List[Message], operator.add]
    plan: QueryPlan = None
    query: str = None
    response: str = None
    current_step_idx: int = 0
    search_result_tracker: List[SingleStepResults] = []
