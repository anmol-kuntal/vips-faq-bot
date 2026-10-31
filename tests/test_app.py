from unittest.mock import patch

from fastapi.testclient import TestClient
from google.genai import errors

from app import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_home_page_served():
    r = client.get("/")
    assert r.status_code == 200
    assert "VIPS" in r.text


def test_valid_question_returns_answer():
    with patch("app.answer", return_value="Fees are due on the 1st.") as mock_answer:
        r = client.post("/ask", json={"question": "  When are fees due?  "})
    assert r.status_code == 200
    assert r.json() == {"answer": "Fees are due on the 1st."}
    mock_answer.assert_called_once_with("When are fees due?")  # input is stripped


def test_empty_question_rejected():
    assert client.post("/ask", json={"question": ""}).status_code == 422


def test_whitespace_only_question_rejected():
    assert client.post("/ask", json={"question": "   "}).status_code == 422


def test_too_long_question_rejected():
    assert client.post("/ask", json={"question": "a" * 501}).status_code == 422


def test_missing_question_field_rejected():
    assert client.post("/ask", json={}).status_code == 422


def test_api_error_returns_503():
    err = errors.ServerError(503, {"error": {"message": "overloaded", "status": "UNAVAILABLE"}})
    with patch("app.answer", side_effect=err):
        r = client.post("/ask", json={"question": "Hello"})
    assert r.status_code == 503
    assert "busy" in r.json()["detail"].lower()