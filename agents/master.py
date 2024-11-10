import aiosqlite
from dotenv import load_dotenv
import json

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, ToolMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.constants import END

from agents.websearchagent.websearchagent import WebSearchAgent

import operator
from typing import TypedDict, Annotated, List

from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from typing import Annotated
from typing_extensions import TypedDict
from langchain_core.prompts import ChatPromptTemplate


class ChatState(BaseModel):
    messages: Annotated[List[BaseMessage], add_messages] = []


@tool
def websearchtool():
    """Call to pass the request to web search agent"""
    return "websearchagent"


def get_route(state: ChatState):
    messages_list = state.messages
    last_msg = messages_list[-1]
    if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
        print(last_msg.tool_calls)
        return "websearcheagent"
    #     if master agent wants to reply to user directly from here last message in list would be of assistant's
    return END


async def call_websearchagent(state: ChatState, config: RunnableConfig):
    websearchagent = WebSearchAgent().get_agent()
    print("Calling websearch agent")
    resp = await websearchagent.ainvoke({"messages": state.messages}, config)
    print(resp)
    return {"messages": [AIMessage(content=resp['search_result'])]}


async def converse(state: ChatState, config: RunnableConfig):
    sys_prompt = """
    You are Ross, an AI agent.
    
    Your primary goal is to help user search the internet. Your tone is friendly and helpful, and you should adapt to the context to make the user feel comfortable.
    """

    prompt = """
        Go through the conversation carefully and respond while keeping the below rules in mind:

        1. If user is engaging in smalltalk then engage in a new topic to keep the conversation flowing or conclude it politely. 
           - Example: “It’s always nice chatting with you! Is there anything else you’d like to discuss?” 

        2. For all the other messages invoke the correct tool.

        ### Conversation:
        {conversation}
        
        Your response:
        """

    prompt_template = ChatPromptTemplate.from_messages(
        [("system", sys_prompt), ("user", prompt)]
    )

    parser = StrOutputParser()

    model = ChatOpenAI(
        model="gpt-4o",
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
    ).bind_tools([websearchtool])

    chain = prompt_template | model

    conversation = "\n".join(f"{msg.type}: {msg.content}" for msg in state.messages)

    conv_resp = await chain.ainvoke({"conversation": conversation}, config)
    print("resp", conv_resp)

    return {"messages": [conv_resp]}


_ = load_dotenv()


class Master:
    def __init__(self):
        conn = aiosqlite.connect("master_checkpoints.sqlite", check_same_thread=False)
        self.memory = AsyncSqliteSaver(conn)

        master = StateGraph(ChatState)
        master.add_node("converstationagent", converse)
        master.add_node("websearcheagent", call_websearchagent)

        master.add_conditional_edges("converstationagent", get_route, ["websearcheagent", END])
        master.add_edge("websearcheagent", END)
        # master.add_edge("converstationagent", END)
        master.set_entry_point("converstationagent")

        self.master_agent = master.compile(checkpointer=self.memory)

    def get_agent(self):
        return self.master_agent
