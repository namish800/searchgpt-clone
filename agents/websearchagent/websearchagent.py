import aiosqlite

from typing import List

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langgraph.constants import END
from langgraph.graph import StateGraph
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from agents.websearchagent.prompts import SUMMARIZE_CHAT_PROMPT, QUERY_PLAN_PROMPT, SEARCH_QUERY_PROMPT, CHAT_PROMPT
from agents.websearchagent.state import WebSearchState
from llm.llm import LLMFactory
from schemas import ChatRequest, QueryPlan, StepContext, QueryPlanStep, QueryStepExecution, SingleStepResults, \
    SearchResult, MessageRole, Message

from tavily import TavilyClient
from datetime import datetime


class WebSearchAgent:
    def __init__(self):
        conn = aiosqlite.connect("checkpoints.sqlite", check_same_thread=False)
        self.memory = AsyncSqliteSaver(conn)

        workflow = StateGraph(WebSearchState)
        workflow.add_node("summarize_query", rephrase_query_with_history_v0)
        workflow.add_node("generate_plan", generate_plan_v0)
        workflow.add_node("step_executor", step_executor)
        workflow.add_node("chat_response", summarize_results)

        workflow.add_edge("summarize_query", "generate_plan")
        workflow.add_edge("generate_plan", "step_executor")
        workflow.add_conditional_edges("step_executor", check_if_summarize)
        workflow.add_edge("chat_response", END)

        workflow.set_entry_point("summarize_query")

        self.graph = workflow.compile(checkpointer=self.memory)

    def get_agent(self):
        return self.graph


def create_message(role: MessageRole, content: str):
    return Message(role=role, content=content)


async def rephrase_query_with_history_v0(
        state: WebSearchState,
        config: RunnableConfig
):
    if not state.messages:
        return {"query": state.request.query, "messages": [Message(role=MessageRole.USER, content=state.request.query)]}

    history_str = "\n".join(f"{msg.role}: {msg.content}" for msg in state.messages)
    model_name = config["configurable"].get("model", "gpt-4o")
    llm_factory = LLMFactory()
    llm = llm_factory.get_llm_by_name(model_name)
    parser = StrOutputParser()
    prompt_template = ChatPromptTemplate.from_messages(
        [("user", SUMMARIZE_CHAT_PROMPT)]
    )
    chain = prompt_template | llm | parser
    question = await chain.ainvoke({
        'chat_history': history_str,
        'question': state.request.query
    })
    return {"query": question, "messages": [Message(role=MessageRole.USER, content=question)]}


async def generate_plan_v0(state: WebSearchState, config: RunnableConfig):
    model_name = config["configurable"].get("model", "gpt-4o")
    llm = LLMFactory().get_llm_by_name(model_name)

    llm = llm.with_structured_output(QueryPlan)
    query_plan_prompt = QUERY_PLAN_PROMPT.format(query=state.query)
    plan: QueryPlan = await llm.ainvoke(query_plan_prompt)

    return {"plan": plan}


async def step_executor(state: WebSearchState, config: RunnableConfig):
    model_name = config["configurable"].get("model", "gpt-4o")
    llm = LLMFactory().get_llm_by_name(model_name)
    search_query_llm = llm.with_structured_output(QueryStepExecution)

    step: QueryPlanStep = state.plan.steps[state.current_step_idx]

    # get the context from dependencies. context is the search result
    relevant_context_list = [build_context(state.search_result_tracker[dep]) for dep in step.dependencies]
    relevant_context_str = "\n".join(relevant_context_list)

    # returns current date and time
    now = datetime.now()
    search_prompt = SEARCH_QUERY_PROMPT.format(
        user_query=state.query,
        current_step=step.step,
        prev_steps_context=relevant_context_str,
        date=str(now)
    )

    query_step_execution: QueryStepExecution = await search_query_llm.ainvoke(search_prompt)

    search_queries = query_step_execution.search_queries

    search_results = ranked_search_results_and_images_from_queries(step.step, search_queries)

    single_step_result = SingleStepResults(step=step.step, results=search_results)

    return_tracker = state.search_result_tracker + [single_step_result]

    return {"search_result_tracker": return_tracker, "current_step_idx": state.current_step_idx + 1}


def check_if_summarize(state: WebSearchState):
    if state.current_step_idx == len(state.plan.steps):
        return "chat_response"
    return "step_executor"


async def summarize_results(state: WebSearchState, config: RunnableConfig):
    model_name = config["configurable"].get("model", "gpt-4o")
    llm = LLMFactory().get_llm_by_name(model_name)

    relevant_context_list = [build_context(x) for x in state.search_result_tracker]
    relevant_context_str = "\n".join(relevant_context_list)

    prompt = CHAT_PROMPT.format(
        my_query=state.query,
        my_context=relevant_context_str
    )

    chain = llm | StrOutputParser()

    # need to pass this config so that it streams the llm token from this node
    resp = await chain.ainvoke(prompt, config)

    return {"response": resp, "messages": [Message(role=MessageRole.ASSISTANT, content=resp)]}


def ranked_search_results_and_images_from_queries(step: str,
                                                  queries: list[str],
                                                  ) -> List[SearchResult]:
    client = TavilyClient()

    search_results = []
    for query in queries:
        result = []
        tavily_resp = client.search(query)
        result = [SearchResult(url=x['url'], content=x['content']) for x in tavily_resp['results']]
        search_results = search_results + result

    return search_results


def build_context(step_result: SingleStepResults):
    step = step_result.step
    context = "\n".join([str(x) for x in step_result.results])

    return f"Step: {step}\n Context: {context}"


def format_step_context(context: List[StepContext]):
    return "\n".join(
        [f"Step: {step.step}\nContext: {step.context}" for step in context]
    )


# def single_task_executor(state: WebSearchState, config: RunnableConfig):
#

if __name__ == "__main__":
    from dotenv import load_dotenv

    _ = load_dotenv()
    agent = WebSearchAgent().get_agent()
    # agent.run()

    query = "News about war between Russia and ukraine"
    request = ChatRequest(query=query)

    for msg, metadata in agent.stream({"request": request}, stream_mode="messages"):
        print(metadata, end="|", flush=True)
