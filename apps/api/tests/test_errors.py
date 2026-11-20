"""Error body shape (system PRD 4.2, API PRD section 1 "Common errors")."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.errors import AppError, register_error_handlers


def _test_app() -> FastAPI:
    test_app = FastAPI()
    register_error_handlers(test_app)

    class Body(BaseModel):
        name: str
        age: int

    @test_app.post("/items")
    def create_item(body: Body) -> Body:
        return body

    @test_app.get("/teapot")
    def teapot() -> None:
        raise AppError(418, "I_AM_A_TEAPOT", "Short and stout.")

    @test_app.get("/boom")
    def boom() -> None:
        raise RuntimeError("secret internals")

    return test_app


def test_unknown_route_returns_not_found(client: TestClient) -> None:
    """API PRD §1 common errors: unknown route → 404 NOT_FOUND with {code, message}."""
    response = client.get("/does-not-exist")

    assert response.status_code == 404
    body = response.json()
    assert set(body) == {"code", "message"}
    assert body["code"] == "NOT_FOUND"


def test_wrong_method_returns_code_and_message(client: TestClient) -> None:
    """API PRD §1: framework HTTP errors (405) also use {code, message}."""
    response = client.delete("/auth/login")

    assert response.status_code == 405
    assert set(response.json()) == {"code", "message"}
    assert response.json()["code"] == "METHOD_NOT_ALLOWED"


def test_app_error_uses_its_status_code_and_code() -> None:
    """System PRD 4.2: AppError → its status and {code, message}."""
    response = TestClient(_test_app()).get("/teapot")

    assert response.status_code == 418
    assert response.json() == {"code": "I_AM_A_TEAPOT", "message": "Short and stout."}


def test_validation_error_lists_fields() -> None:
    """API PRD §1: 422 → {code: VALIDATION_ERROR, message, fields: [{field, message}]}."""
    response = TestClient(_test_app()).post("/items", json={"age": "not-a-number"})

    assert response.status_code == 422
    body = response.json()
    assert set(body) == {"code", "message", "fields"}
    assert body["code"] == "VALIDATION_ERROR"
    assert {f["field"] for f in body["fields"]} == {"name", "age"}
    assert all(set(f) == {"field", "message"} and f["message"] for f in body["fields"])


def test_malformed_json_is_a_validation_error() -> None:
    """API PRD §1: a body that is not valid JSON → 422 VALIDATION_ERROR."""
    response = TestClient(_test_app()).post(
        "/items", content=b"{not json", headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_unhandled_exception_returns_internal_error_without_details() -> None:
    """System PRD 4.2: unexpected errors → 500 {code: INTERNAL_ERROR}, no internals leaked."""
    response = TestClient(_test_app(), raise_server_exceptions=False).get("/boom")

    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL_ERROR"
    assert "secret internals" not in response.text
