from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.admin_tools import router


app = FastAPI()
app.include_router(router)

client = TestClient(app)


def test_list_admin_tools():
    response = client.get("/admin/tools")

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 3
    assert data[0]["version"] == "v1"


def test_get_admin_tool():
    response = client.get("/admin/tools/get_eta")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == "get_eta"
    assert data["version"] == "v1"
    assert data["health"] == "healthy"


def test_get_unknown_admin_tool():
    response = client.get("/admin/tools/unknown_tool")

    assert response.status_code == 404