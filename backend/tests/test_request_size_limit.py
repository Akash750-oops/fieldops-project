
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.middleware.tenant import RequestSizeLimitMiddleware

def test_request_size_limit_class_exists():
    from app.middleware.tenant import RequestSizeLimitMiddleware

    assert RequestSizeLimitMiddleware.MAX_BODY_SIZE == 1024 * 1024

def test_oversized_request_is_rejected():
    app = FastAPI()
    app.add_middleware(RequestSizeLimitMiddleware)

    @app.post("/test")
    async def test_endpoint():
        return {"message": "accepted"}

    client = TestClient(app)

    large_body = "x" * (1024 * 1024 + 1)

    response = client.post(
        "/test",
        content=large_body,
        headers={"Content-Type": "text/plain"},
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "Request body too large."
    
def test_request_within_size_limit_is_allowed():
    app = FastAPI()
    app.add_middleware(RequestSizeLimitMiddleware)

    @app.post("/test")
    async def test_endpoint():
        return {"message": "accepted"}

    client = TestClient(app)

    small_body = "x" * 100

    response = client.post(
        "/test",
        content=small_body,
        headers={"Content-Type": "text/plain"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "accepted"
    
def test_request_exactly_at_size_limit_is_allowed():
    app = FastAPI()
    app.add_middleware(RequestSizeLimitMiddleware)

    @app.post("/test")
    async def test_endpoint():
        return {"message": "accepted"}

    client = TestClient(app)

    body = "x" * (1024 * 1024)

    response = client.post(
        "/test",
        content=body,
        headers={"Content-Type": "text/plain"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "accepted"
    
def test_invalid_content_length_is_rejected():
    app = FastAPI()
    app.add_middleware(RequestSizeLimitMiddleware)

    @app.post("/test")
    async def test_endpoint():
        return {"message": "accepted"}

    client = TestClient(app)

    response = client.post(
        "/test",
        content="hello",
        headers={
            "Content-Type": "text/plain",
            "Content-Length": "invalid",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid Content-Length header."
    
def test_request_without_content_length_is_allowed():
    app = FastAPI()
    app.add_middleware(RequestSizeLimitMiddleware)

    @app.post("/test")
    async def test_endpoint():
        return {"message": "accepted"}

    client = TestClient(app)

    response = client.post(
        "/test",
        content="hello",
        headers={
            "Content-Type": "text/plain",
        },
    )

    assert response.status_code == 200
    assert response.json()["message"] == "accepted"
    
def test_missing_content_length_is_allowed():
    app = FastAPI()
    app.add_middleware(RequestSizeLimitMiddleware)

    @app.post("/test")
    async def test_endpoint():
        return {"message": "accepted"}

    client = TestClient(app)

    response = client.post(
        "/test",
        content="hello",
        headers={"Content-Type": "text/plain"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "accepted"
    
def test_request_without_content_length_is_allowed():
    app = FastAPI()
    app.add_middleware(RequestSizeLimitMiddleware)

    @app.post("/test")
    async def test_endpoint():
        return {"message": "accepted"}

    client = TestClient(app)

    response = client.post(
        "/test",
        content="hello",
        headers={"Content-Type": "text/plain"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "accepted"
    
def test_request_without_content_length_is_allowed():
    app = FastAPI()
    app.add_middleware(RequestSizeLimitMiddleware)

    @app.post("/test")
    async def test_endpoint():
        return {"message": "accepted"}

    client = TestClient(app)

    response = client.post(
        "/test",
        content="hello",
        headers={"Content-Type": "text/plain"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "accepted"
def test_request_without_content_length_is_allowed():
    app = FastAPI()
    app.add_middleware(RequestSizeLimitMiddleware)

    @app.post("/test")
    async def test_endpoint():
        return {"message": "accepted"}

    client = TestClient(app)

    response = client.post(
        "/test",
        content="hello",
        headers={"Content-Type": "text/plain"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "accepted"
    
