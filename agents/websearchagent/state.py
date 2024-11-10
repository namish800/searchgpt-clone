import operator
from typing import TypedDict, Annotated, List

from langchain_core.messages import HumanMessage, BaseMessage
from langgraph.graph import add_messages
from pydantic import BaseModel, Field

from schemas import ChatRequest, QueryPlan, StepSearchResultsTracker, SingleStepResults, Message


class WebSearchState(BaseModel):
    messages: Annotated[List[BaseMessage], add_messages] = []
    plan: QueryPlan = None
    query: str = None
    search_result: str = None
    current_step_idx: int = 0
    search_result_tracker: List[SingleStepResults] = []
