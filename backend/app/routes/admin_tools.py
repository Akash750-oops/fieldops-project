from fastapi import APIRouter, HTTPException

from app.tools.registry import create_default_registry

router = APIRouter(
    prefix="/admin/tools",
    tags=["Admin Tools"],
)

registry = create_default_registry()


@router.get("")
def list_admin_tools() -> list[dict]:
    tools = registry.search_tools()

    return [
        {
            "id": tool.schema.contract.name,
            "name": tool.schema.contract.name,
            "description": tool.schema.contract.description,
            "version": tool.schema.contract.version,
            "category": tool.category,
            "capabilities": sorted(tool.capabilities),
            "dependencies": sorted(tool.dependencies),
            "permissions": sorted(tool.permissions),
            "health": tool.health,
        }
        for tool in tools
    ]


@router.get("/{tool_id}")
def get_admin_tool(tool_id: str) -> dict:
    tool = registry.get_tool(tool_id)

    if tool is None:
        raise HTTPException(
            status_code=404,
            detail=f"Tool '{tool_id}' not found",
        )

    return {
        "id": tool.schema.contract.name,
        "name": tool.schema.contract.name,
        "description": tool.schema.contract.description,
        "version": tool.schema.contract.version,
        "category": tool.category,
        "capabilities": sorted(tool.capabilities),
        "dependencies": sorted(tool.dependencies),
        "permissions": sorted(tool.permissions),
        "health": tool.health,
    }