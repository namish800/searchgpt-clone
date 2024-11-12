# A multi agent to implement a SearchGpt clone.

This repo contains a conversational AI agent designed to assist users with internet searches and engage in friendly, context-aware interactions. Built on FastAPI, it leverages LangChain, LangGraph, and Server-Sent Events (SSE) for real-time, multi-agent conversational flows.

## Features

- **Multi-Agent Orchestration**: Ross leverages multiple specialized agents to handle complex interactions, including:
    - **Web Search Agent**: An advanced search handler capable of managing complex queries through a structured "plan and execute" approach.
    - **Conversation Agent**: Handles friendly small talk and conversational flow.
- **Plan and Execute Pattern for Web Search**: The Web Search Agent can analyze complex queries by creating a step-by-step plan, retrieving and synthesizing relevant search results before generating a response.
- **Real-Time Event Streaming**: Server-Sent Events (SSE) provide immediate, responsive feedback by streaming conversation updates.

## Agents Structure

- **Primary Agent (`Master`)**: Acts as the central controller, orchestrating interactions among the agents and routing tasks dynamically. Check `agents/master.py`
  - **Web Search Tool**: Integrated via the `@tool` decorator, allowing Ross to invoke the Web Search Agent for queries requiring external information.
  - **Event Streaming (`event_stream`)**: Uses SSE to stream updates and responses, improving interaction fluidity.

## Web Search Agent

The Web Search Agent handles complex, multi-step search tasks using a "plan and execute" approach:

1. **Summarize Query**: The agent rephrases the user’s question using conversational context to create a cohesive query.
2. **Generate Plan**: A step-by-step plan is created using LangChain’s language model integration, where each step defines an action needed to resolve the user’s query.
3. **Execute Steps**: For each step, the agent runs individual searches, builds relevant context from prior results, and ranks responses from external search results to ensure accuracy.
4. **Summarize Results**: Once all steps are complete, the agent synthesizes results into a coherent, conversational response.

The "plan and execute" structure is achieved using LangGraph's state management capabilities and allows the Web Search Agent to handle multi-step tasks by performing each action iteratively. Tavily API calls power the search process, where results are ranked, aggregated, and contextualized for enhanced response accuracy.

### Example Interactions

- **Small Talk**: Ross responds in a friendly manner, handling the interaction within the Conversation Agent.
- **Dynamic Web Search**: For multi-faceted or complex questions, Ross activates the Web Search Agent. The agent creates a plan, executes sequential steps, and presents an informative answer.

## Prerequisites

- Python 3.9+
- Install dependencies from `requirements.txt`:

  ```bash
  pip install -r requirements.txt
  ```

- **Environment Variables**: Create a `.env` file in the root directory to set necessary environment variables.
  - TAVILY_API_KEY={For searching the internet}
  - OPENAI_API_KEY
  - LANGCHAIN_API_KEY={Get from langsmith)
  - LANGCHAIN_TRACING_V2=true 
  - LANGCHAIN_PROJECT={Project name}

## Usage

### Running the Server

1. Start the FastAPI server:

   ```bash
   uvicorn server:app --host 0.0.0.0 --port 8000
   ```

2. Access the `/stream` endpoint to interact with Ross, passing queries to start a conversation.

   Example:
   ```
   /stream?query="Tell me about climate change"&session_id=unique_session_id
   ```

### Docker Setup
To run the server in a Docker container, use the following commands:

Build the Docker image:

```
docker build -t searchgpt .
```
Run the container:
```
docker run -p 80:80 --env-file .env searchgpt
```
The --env-file .env flag ensures that environment variables from your .env file are available to the container.

### Development

- **LangChain & LangGraph**: Power the multi-agent orchestration, enabling dynamic routing and flexible integration.
- **SQLite Memory Persistence**: Stores checkpoints to maintain session continuity and support more complex, multi-turn conversations.
- **Server-Sent Events (SSE)**: Using FAST API to implement the SSE protocil which provides real-time updates to enhance interaction fluidity. See the `event_stream` function in `server.py`.


## SSE Event Types and LangGraph stream_events Method
The event_stream function leverages LangGraph's stream_events method to provide real-time updates as the conversation progresses. This function yields different events based on the stage of the workflow, allowing the client to receive meaningful feedback at each step of the process.

## Event Types and LangGraph `stream_events` Method

The `event_stream` function leverages LangGraph's `astream_events` method to provide real-time updates as the conversation progresses. This function yields different events based on the stage of the workflow, allowing the client to receive meaningful feedback at each step of the process.

### Events Generated in `event_stream`

- **`start_session`**:
    - Triggered at the beginning of a conversation when no `session_id` is provided. Used by the fronend client to maintain session.
    - Generates a unique `session_id` to identify and manage the current conversation session.
    - **Example**:
      ```json
      {"event": "start_session", "data": {"session_id": "<generated_session_id>"}}
      ```

- **`thoughts`**:
    - This event is used throughout the workflow to communicate key stages in the process. It provides insights into what the agent is "thinking" or doing, enhancing transparency and user experience.
    - **Examples of `thoughts` events**:
        - **"Understanding query"**: Triggered when the agent is analyzing the user’s query (`summarize_query` stage).
        - **"Generating plan"**: Generated when the agent is constructing a multi-step plan to resolve a complex query (`generate_plan` stage).
        - **"Searching the Internet"**: Communicates that the agent is executing a search action based on the planned steps (`step_executor` stage).
        - **"Generated plan"**: Signals the completion of the planning phase, providing the structured plan as part of the response.

- **`assistant_msg_start`**:
    - Signals the beginning of a response from the agent.
    - This event is typically emitted when the agent transitions to response generation nodes, such as `chat_response` or `converstationagent`.
    - Allows the frontend to prepare for an incoming message stream, setting up a more fluid user experience.

- **`assistant`**:
    - Streams individual response chunks from the agent, providing the final answer.
    - Particularly useful when dealing with lengthy responses, as it enables real-time delivery to the frontend.
    - **Example Structure**:
      ```json
      {
        "event": "assistant",
        "data": {
          "message": "Received response",
          "search_result": "<response_chunk>",
          "session_id": "<session_id>"
        }
      }
      ```

- **`end`**:
    - Indicates that the streaming process has concluded.
    - Helps the client handle the end of a session, closing any open connections gracefully.
    - **Example**:
      ```json
      {"event": "end", "data": {"message": "Stream ended"}}
      ```

### Using LangGraph’s `astream_events` Method

LangGraph’s `astream_events` method is a powerful feature that provides asynchronous, event-based feedback during the execution of complex workflows. Here’s how it integrates with the `event_stream` function:

- The `stream_events` method iterates over each action in the agent’s workflow, yielding structured events based on LangGraph’s defined nodes and edges.
- Events like `on_chain_start`, `on_chain_end`, and `on_chat_model_stream` are captured and conditionally transformed into frontend-friendly messages.

Checkout the [langgraph documentation](https://langchain-ai.github.io/langgraph/concepts/streaming/) to learn more about different events.

By using `stream_events`, the `event_stream` function can break down complex multi-step actions (such as query planning and search execution) into manageable events, offering users a clear and interactive experience.

---