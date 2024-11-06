from langchain_core.runnables import RunnableConfig

from agents.websearchagent.prompts import QUERY_PLAN_PROMPT
from agents.websearchagent.state import WebSearchState
from llm.llm import LLMFactory
from schemas import QueryPlan


def generate_plan(state: WebSearchState, config: RunnableConfig):
    model_name = config["configurable"].get("model", "gpt-4o")
    llm = LLMFactory().get_llm_by_name(model_name)

    llm = llm.with_structured_output(QueryPlan)
    query_plan_prompt = QUERY_PLAN_PROMPT.format(query=state.query)
    plan: QueryPlan = llm.invoke(query_plan_prompt)

    return {"steps": plan}



