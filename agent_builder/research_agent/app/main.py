from dotenv import load_dotenv

from agent_sdk import create_agent_app_from_logic
from app.agent import ResearchAgentLogic

load_dotenv()

app = create_agent_app_from_logic(
    ResearchAgentLogic(),
    root_message="Research agent API is running",
)
