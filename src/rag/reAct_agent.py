"""
ReAct agent setup for document retrieval and question answering.
"""

from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate

from src.config.settings import Config
from src.llms.openai import llm
from src.rag.retriever_setup import get_retriever

config = Config()


def build_agent_executor(user_id: str, description: str = None) -> AgentExecutor:
    """
    Build a fresh ReAct agent executor scoped to one user's documents.

    The retriever tool is constructed at call time (not import time) and is
    filtered to the given user, so the agent only ever searches that user's
    uploaded documents in Qdrant.

    Args:
        user_id: The user whose documents the agent may retrieve.
        description: Optional description of the user's documents for the tool.

    Returns:
        An AgentExecutor wired to the user-scoped retriever tool.
    """
    # Build the retriever tool scoped to this user's documents.
    tools = [get_retriever(user_id, description)]

    prompt = ChatPromptTemplate.from_messages([
        ("system", config.prompt("system_prompt")),
        ("human", "{input}"),
        ("ai", "{agent_scratchpad}")
    ])

    react_agent = create_react_agent(llm, tools, prompt)
    return AgentExecutor(
        agent=react_agent,
        tools=tools,
        handle_parsing_errors=True,
        max_iterations=2,
        verbose=True,
        return_intermediate_steps=True
    )
