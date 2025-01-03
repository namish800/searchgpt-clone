import asyncio
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import AIMessageChunk, HumanMessage

from sse_starlette.sse import EventSourceResponse, ServerSentEvent

from agents.master import Master
from agents.websearchagent.websearchagent import WebSearchAgent
from schemas import ChatRequest
from pydantic import BaseModel

from dotenv import load_dotenv
import json

_ = load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust based on your needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def convert_pydantic_to_dict(obj):
    if isinstance(obj, BaseModel):
        return obj.dict()
    elif isinstance(obj, dict):
        return {k: convert_pydantic_to_dict(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_pydantic_to_dict(i) for i in obj]
    else:
        return obj


async def event_stream(query: str, request: Request, session_id=None):
    agent = Master().get_agent()

    if not session_id:
        session_id = uuid.uuid4().__str__()
        data = {"session_id": session_id}
        yield ServerSentEvent(event="start_session", data=json.dumps(data))

    messages = [HumanMessage(content=query)]
    agent_config = {"configurable": {"thread_id": session_id}}
    async for event in agent.astream_events({"messages": messages}, config=agent_config,
                                            version="v2"):
        if await request.is_disconnected():
            break
        is_on_chain_end = event["event"] == "on_chain_end"
        is_graph_step = any(t.startswith("graph:step:") for t in event.get("tags", []))
        is_on_chain_start = event["event"] == "on_chain_start"
        is_chat_model_stream = event["event"] == "on_chat_model_stream"
        is_on_chat_model_start = event["event"] == "on_chat_model_start"

        data = None

        if is_on_chain_end and is_graph_step and event["name"] == "summarize_query":
            data = {"message": "Understanding query", "session_id": session_id}
            yield ServerSentEvent(event="thoughts", data=json.dumps(data))

        elif is_on_chain_start and is_graph_step and event["name"] == "generate_plan":
            data = {"message": "Generating plan", "session_id": session_id}
            yield ServerSentEvent(event="thoughts", data=json.dumps(data))

        elif is_on_chain_end and is_graph_step and event["name"] == "generate_plan":
            plan = convert_pydantic_to_dict(event["data"]["output"]["plan"])
            data = {"message": "Generated plan", "plan": plan, "session_id": session_id}
            yield ServerSentEvent(event="thoughts", data=json.dumps(data))

        elif is_on_chain_start and is_graph_step and event["name"] == "step_executor":
            data = {"message": "Searching the Internet", "session_id": session_id}
            yield ServerSentEvent(event="thoughts", data=json.dumps(data))

        # elif is_on_chain_end and is_graph_step and event["name"] == "chat_response":
        #     search_result = convert_pydantic_to_dict(event["data"]["output"]["response"])
        #     data = {"message": "Received response", "search_result": search_result, "session_id": session_id}
        #     yield ServerSentEvent(event="assistant", data=json.dumps(data))
        elif is_on_chat_model_start and event["metadata"]["langgraph_node"] == "chat_response":
            yield ServerSentEvent(event="assistant_msg_start", data="")

        elif is_on_chat_model_start and event["metadata"]["langgraph_node"] == "converstationagent":
            yield ServerSentEvent(event="assistant_msg_start", data="")

        elif is_chat_model_stream and event["metadata"]["langgraph_node"] == "chat_response":
            # search_result = convert_pydantic_to_dict(event["data"]["output"]["response"])
            search_result_chunk: AIMessageChunk = event["data"]["chunk"]
            # In case of tool call content will be blank
            if search_result_chunk.content != "":
                data = {"message": "Received response", "search_result": search_result_chunk.content,
                        "session_id": session_id}
                yield ServerSentEvent(event="assistant", data=json.dumps(data))

        elif is_chat_model_stream and event["metadata"]["langgraph_node"] == "converstationagent":
            # search_result = convert_pydantic_to_dict(event["data"]["output"]["response"])
            search_result_chunk: AIMessageChunk = event["data"]["chunk"]
            # In case of tool call content will be blank
            if search_result_chunk.content != "":
                data = {"message": "Received response", "search_result": search_result_chunk.content,
                        "session_id": session_id}
                yield ServerSentEvent(event="assistant", data=json.dumps(data))

    yield ServerSentEvent(event="end", data=f"{json.dumps({'message': 'Stream ended'})}")


@app.get("/stream")
async def stream(query: str, session_id: str, request: Request):
    print(session_id)
    return EventSourceResponse(event_stream(query, request, session_id))
