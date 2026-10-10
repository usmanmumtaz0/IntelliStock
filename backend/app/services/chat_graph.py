"""User-message-triggered, bounded LangGraph: interpret -> read -> finish."""
from typing import TypedDict
import os
from app.services.chat_planner import interpret
from app.services.chat_tools import execute_read


class ChatState(TypedDict):
    question: str
    previous_plan: dict | None
    plan: dict
    mode: str
    notice: str
    answer: str
    sources: list


def run_chat(db, question, previous_plan=None):
    # Legacy LangChain honors tracing env switches even with callbacks=[].
    # Fail closed rather than export private questions through ambient tracing.
    if any(os.environ.get(key, "") not in ("", "false", "False", "0") for key in
           ("LANGCHAIN_TRACING", "LANGCHAIN_TRACING_V2", "LANGSMITH_TRACING", "LANGSMITH_TRACING_V2")):
        raise RuntimeError("External tracing must be disabled for private chat")
    from langgraph.graph import StateGraph, END
    from langchain_core.tracers.context import tracing_v2_callback_var
    from langsmith.run_helpers import get_run_tree_context
    if tracing_v2_callback_var.get() is not None or get_run_tree_context() is not None:
        raise RuntimeError("Inherited tracing is not allowed for private chat")
    graph = StateGraph(ChatState)
    graph.add_node("interpret_question", lambda state: interpret(state["question"], state["previous_plan"]))
    graph.add_node("read_records", lambda state: execute_read(db, state["plan"]))
    graph.set_entry_point("interpret_question")
    graph.add_edge("interpret_question", "read_records")
    graph.add_edge("read_records", END)
    return graph.compile().invoke({"question":question, "previous_plan":previous_plan,
        "plan":{}, "mode":"local", "notice":"", "answer":"", "sources":[]},
        config={"recursion_limit":6, "callbacks":[]})
