"""
agents/
=======
Spidy multi-agent forex trading system.

Public API
----------
  from agents import Orchestrator                   # run the whole system
  from agents import MessageBus, Topic, AgentMessage # use the bus standalone
  from agents import (                              # use individual agents
      DataEngineerAgent,
      ResearcherAgent,
      RiskManagerAgent,
      ExecutorAgent,
  )

Quick start
-----------
  # From project root:
  python -m agents.orchestrator
  python -m agents.orchestrator --config path/to/settings.yaml
"""

from .message_bus    import MessageBus, Topic, AgentMessage
from .base_agent     import BaseAgent
from .data_engineer  import DataEngineerAgent
from .researcher     import ResearcherAgent
from .risk_manager   import RiskManagerAgent
from .executor       import ExecutorAgent
from .orchestrator   import Orchestrator

__all__ = [
    "MessageBus",
    "Topic",
    "AgentMessage",
    "BaseAgent",
    "DataEngineerAgent",
    "ResearcherAgent",
    "RiskManagerAgent",
    "ExecutorAgent",
    "Orchestrator",
]
