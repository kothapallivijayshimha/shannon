from agents import get_agent

async def ask_agent(task: str):
    """Route *task* to the right agent and return its result."""
    from agents.base import BaseAgent
    agent: BaseAgent = get_agent(task)
    return await agent.run(task)
