"""End-to-end tests for the PDF / CSV export endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

BISECTION_INPUTS = {
    "function": "x^3 - x - 1",
    "a": 1.0,
    "b": 2.0,
    "tolerance": 1e-6,
    "max_iterations": 50,
}


class TestCsvExport:
    def test_returns_iteration_table_as_csv(self, client: TestClient) -> None:
        response = client.post("/api/export/bisection?format=csv", json=BISECTION_INPUTS)
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        disposition = response.headers["content-disposition"]
        assert "attachment" in disposition
        assert ".csv" in disposition
        assert "Bisection Method" in response.text
        assert "Iteration" in response.text
        assert "converged" in response.text

    def test_csv_has_header_and_data_rows(self, client: TestClient) -> None:
        response = client.post("/api/export/bisection?format=csv", json=BISECTION_INPUTS)
        lines = [line for line in response.text.splitlines() if line.strip()]
        assert lines
        # The iteration table header row is present somewhere in the file.
        assert any(line.startswith("Iteration,") for line in lines)


class TestPdfExport:
    def test_returns_pdf_bytes(self, client: TestClient) -> None:
        response = client.post("/api/export/bisection?format=pdf", json=BISECTION_INPUTS)
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "attachment" in response.headers["content-disposition"]
        assert ".pdf" in response.headers["content-disposition"]
        assert response.content.startswith(b"%PDF")
        assert len(response.content) > 1000

    def test_default_format_is_pdf(self, client: TestClient) -> None:
        response = client.post("/api/export/bisection", json=BISECTION_INPUTS)
        assert response.status_code == 200
        assert response.content.startswith(b"%PDF")


class TestExportErrors:
    def test_unknown_method_is_404(self, client: TestClient) -> None:
        response = client.post("/api/export/does_not_exist?format=pdf", json={})
        assert response.status_code == 404
        assert response.json()["code"] == "method_not_found"

    def test_stub_method_is_409(self, client: TestClient) -> None:
        response = client.post("/api/export/romberg?format=pdf", json={})
        assert response.status_code == 409
        assert response.json()["code"] == "method_unavailable"

    def test_invalid_input_is_400(self, client: TestClient) -> None:
        response = client.post(
            "/api/export/bisection?format=pdf",
            json={**BISECTION_INPUTS, "a": "banana"},
        )
        assert response.status_code == 400
        assert response.json()["code"] == "invalid_input"

    def test_invalid_format_is_422(self, client: TestClient) -> None:
        response = client.post("/api/export/bisection?format=xml", json=BISECTION_INPUTS)
        assert response.status_code == 422
