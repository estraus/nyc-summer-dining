from fastapi.testclient import TestClient


def test_root_serves_index_html(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<title>" in response.text.lower()


def test_css_served(client: TestClient) -> None:
    response = client.get("/css/app.css")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")
