"""LangGraph Workflow：知识库问答智能体。

图结构（ReAct 循环）：

    START → agent（LLM 决策：直接回答 或 发起 tool calls）
              ↙ 条件边 route_after_agent
        tools（Function Calling 执行）→ agent（带着工具结果继续）
              ↘ END（无 tool calls，产出最终回答）

通过 thread_id（会话 ID）+ MemorySaver 实现多轮对话记忆。
"""
import logging
from datetime import date
from typing import Annotated

from langchain_core.messages import AIMessage, AnyMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import TypedDict

from app.agent.llm import get_llm
from app.agent.tools import ALL_TOOLS
from app.prompts import SYSTEM_PROMPT

logger = logging.getLogger("app.agent")


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def _build_system_message() -> SystemMessage:
    return SystemMessage(content=SYSTEM_PROMPT.format(today=date.today().isoformat()))


def agent_node(state: AgentState):
    messages = state["messages"]
    # 主系统提示词（角色/日期/防幻觉规则）必须始终存在；
    # 检索上下文块也是 SystemMessage，不能作为"已有系统提示"的判断依据
    if not messages or not (isinstance(messages[0], SystemMessage) and messages[0].content.startswith("你是公司智能知识库助手")):
        messages = [_build_system_message()] + messages
    response = get_llm().bind_tools(ALL_TOOLS).invoke(messages)
    return {"messages": [response]}


def route_after_agent(state: AgentState) -> str:
    last: AIMessage = state["messages"][-1]
    if getattr(last, "tool_calls", None):
        return "tools"
    return END


def build_graph() -> CompiledStateGraph:
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(ALL_TOOLS))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", route_after_agent, ["tools", END])
    graph.add_edge("tools", "agent")
    return graph.compile(checkpointer=MemorySaver())


kb_graph = build_graph()
