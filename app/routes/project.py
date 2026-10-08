from fastapi import APIRouter

from app.models.project import ProjectRequest
from app.services.container import project_service


router = APIRouter()

@router.post("/project")
async def set_project(
    request: ProjectRequest
):

    return project_service.set_project(
        request.path
    )


@router.get("/project")
async def get_project():

    return project_service.get_project()


@router.get("/project/tree")
async def project_tree():

    return project_service.get_tree()


@router.get("/project/file")
async def read_project_file(path: str):

    if project_service.project_root is None:
        return {
            "success": False,
            "error": "No project selected"
        }

    content = project_service.read_file(path)

    if content is None:
        return {
            "success": False,
            "error": "Unable to read file"
        }

    return {
        "success": True,
        "path": path,
        "content": content
    }


@router.get("/project/search")
async def search_project(query: str):

    if project_service.project_root is None:
        return {
            "success": False,
            "error": "No project selected"
        }

    results = project_service.search(query)

    return {
        "success": True,
        "query": query,
        "results": results,
        "count": len(results)
    }