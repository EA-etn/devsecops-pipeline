"""Errores provocados para chaos engineering (CHAOS_ERROR_RATE)."""

import pytest
from fastapi.testclient import TestClient

import app.main
from app.main import chaos_rate

client = TestClient(app.main.app)


@pytest.fixture
def rate(monkeypatch):
    """Fija la fracción de errores solo durante el test."""
    return lambda value: monkeypatch.setattr(app.main, "CHAOS_ERROR_RATE", value)


def test_desactivado_por_defecto():
    assert app.main.CHAOS_ERROR_RATE == 0
    assert all(client.get("/info").status_code == 200 for _ in range(20))


def test_todas_fallan_con_1(rate):
    rate(1.0)
    r = client.get("/info")
    assert r.status_code == 500
    assert r.json()["detail"].startswith("chaos")


def test_health_y_metrics_nunca_fallan(rate):
    rate(1.0)
    assert client.get("/health").status_code == 200
    assert client.get("/metrics").status_code == 200


def test_los_500_se_cuentan_en_las_metricas(rate):
    rate(1.0)
    client.get("/info")
    assert 'handler="/info",method="GET",status="5xx"' in client.get("/metrics").text


@pytest.mark.parametrize(("value", "expected"), [("0", 0.0), ("0.2", 0.2), ("7", 1.0), ("-1", 0.0)])
def test_la_fraccion_se_limita_entre_0_y_1(value, expected):
    assert chaos_rate(value) == expected
