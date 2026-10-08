from pydantic import BaseModel


class ProjectRequest(BaseModel):
    path: str