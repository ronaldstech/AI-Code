from app.services.project import ProjectService
from app.services.ollama import OllamaService
from app.services.agent import AgentService


project_service = ProjectService()

ollama_service = OllamaService()

agent_service = AgentService(
    project_service,
    ollama_service
)