import os
import requests
from typing import Annotated, TypedDict, List, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph.message import add_messages
from langchain_core.tools import tool
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

brain_llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", temperature=0.7)
coder_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vector_db = FAISS.load_local("blender_docs_index", embeddings, allow_dangerous_deserialization=True)


@tool
def ask_user(question: str):
    """Ask the user a specific question and wait for manual input."""
    print(f"\n[TOOL CALLED] ask_user | Q: {question}")
    user_resp = input(f"\n[JARVIS QUESTION]: {question}\nUser Response > ")
    return user_resp

@tool
def query_database(query: str):
    """Query the database for blender api documentation"""
    print(f"\n[TOOL CALLED] query_database | ARG: {query}")
    docs = vector_db.similarity_search(query, k=5)
    return "\n".join([d.page_content for d in docs])

@tool
def send_to_blender(code: str):
    """Sends code to Blender and RETURNS the result of the 'result' variable."""
    print(f"\n[TOOL CALLED] send_to_blender | CODE: {code[:50]}...")
    try:
        # We expect the server to run the code and send back whatever is in 'result'
        response = requests.post("http://localhost:8000/internal/add_task", json={"code": code}, timeout=10)
        
        # Capture the actual data returned by Blender
        data = response.json().get("result_data") 
        if data:
            return f"Success. Blender returned: {data}"
        return "Success. Code executed, but no data was assigned to 'result'."
    except Exception as e:
        return f"Connection Error: {e}"

@tool
def get_blender_data():
    """Get data from the current blender scene"""
    print(f"\n[TOOL CALLED] get_blender_data | ACTION: Fetching scene state")
    try:
        # Ask server for the result Blender posted
        response = requests.get("http://localhost:8000/internal/get_result")
        return response.json().get("response")
    except:
        return "No data returned from Blender yet."

@tool
def terminal_msg(text: str):
    """Output a message to the  terminal"""
    print(f"\n[JARVIS]: {text}")
    return "Message displayed to user."

tools = [query_database, get_blender_data, terminal_msg, ask_user, send_to_blender]
brain_with_tools = brain_llm.bind_tools(tools)
coder_llm.bind_tools([query_database])


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages] 
    blender_response: str

# --- NODES ---

def brain_node(state: AgentState):
    # Add a instruction to stop looping
    system_message = SystemMessage(content=(
        "You are Jarvis. Check the history: \n"
        "1. If 'get_blender_data' results are already in the messages, DO NOT call it again.\n"
        "2. If you know what's in the scene, give instructions to the 'coder' node immediately.\n"
        "3. Only use 'ask_user' if the user's request is totally unclear."
    ))
    
    # Send the WHOLE history so it can see previous tool results
    response = brain_with_tools.invoke([system_message] + state["messages"])
    return {"messages": [response]}

def coder_node(state: AgentState):
    """Generates the code based on Brain's instructions."""
    last_brain_msg = state["messages"][-1].content
    
    system_prompt = (
        "You are a Blender Python Expert. Write ONLY raw Python code. You are FORBIDDEN from writing code until you look at the api documentation first\n"
        "CRITICAL: If you are asked to GET information, you MUST assign it to a "
        "variable named 'result' at the end of your script.\n"
        "Example: result = [obj.name for obj in bpy.data.objects]"
    )

    code_response = coder_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Instruction: {last_brain_msg}")
    ])
    
    # Automatically trigger tool call after code generation
    status = send_to_blender.invoke(code_response.content)
    return {"blender_response": status, "messages": [AIMessage(content=f"Executed Code. Result: {status}")]}

def router(state: AgentState) -> Literal["tools", "coder", "__end__"]:
    messages = state["messages"]
    last_msg = messages[-1]
    
    # 1. Check for Tool Calls first (highest priority)
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        return "tools"
    
    # 2. Safety check for content type
    content = ""
    if isinstance(last_msg.content, str):
        content = last_msg.content.lower()
    elif isinstance(last_msg.content, list):
        # Handle cases where content is a list of dicts (common in multimodal/2026 models)
        content = " ".join([str(c.get("text", "")) for c in last_msg.content if isinstance(c, dict)]).lower()

    # 3. Logic to determine if we should go to coder
    if "coder" in content or "write code" in content or "python" in content:
        return "coder"
    
    # 4. If JARVIS is just talking to the user (terminal_msg), we end.
    return "__end__"

# --- BUILD GRAPH ---

builder = StateGraph(AgentState)

builder.add_node("brain", brain_node)
builder.add_node("tools", ToolNode(tools))
builder.add_node("coder", coder_node)

builder.add_edge(START, "brain")
builder.add_conditional_edges("brain", router)
builder.add_edge("tools", "brain")
builder.add_edge("coder", END)

graph = builder.compile()

# --- EXECUTION ---

if __name__ == "__main__":
    print("--- JARVIS BLENDER AGENT STARTING (NO MEMORY) ---")
    while True:
        user_input = input("\nUser > ")
        if user_input.lower() in ["exit", "quit"]:
            break
            
        # Passing fresh state every time (No Memory persistence)
        for event in graph.stream({"messages": [HumanMessage(content=user_input)]}):
            pass
