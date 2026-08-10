from fastapi.testclient import TestClient

from chan_quant.api.app import app

client = TestClient(app)


def test_health_reports_remote_network_enabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("CHAN_QUANT_REMOTE_NETWORK_ENABLED", raising=False)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["remote_network"] == "enabled"


def test_health_rejects_invalid_remote_network_configuration(monkeypatch) -> None:
    monkeypatch.setenv("CHAN_QUANT_REMOTE_NETWORK_ENABLED", "sometimes")

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "configuration_error",
        "data_mode": "synthetic",
        "remote_network": "invalid",
        "strategy": "independent-v0.1.0-draft",
    }


def test_health_keeps_remote_state_distinct_from_invalid_data_mode(monkeypatch) -> None:
    monkeypatch.setenv("CHAN_QUANT_DATA_SOURCE", "invalid")
    monkeypatch.setenv("CHAN_QUANT_REMOTE_NETWORK_ENABLED", "true")

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "configuration_error",
        "data_mode": "invalid",
        "remote_network": "enabled",
        "strategy": "independent-v0.1.0-draft",
    }


def test_remote_only_endpoints_fail_closed_when_network_is_disabled(monkeypatch) -> None:
    monkeypatch.setenv("CHAN_QUANT_REMOTE_NETWORK_ENABLED", "false")

    responses = [
        client.get("/api/v1/instruments/search", params={"q": "600519"}),
        client.get("/api/v1/instruments/600519.SH"),
        client.get("/api/v1/instruments/600519.SH/quote"),
        client.get(
            "/api/v1/quotes",
            params=[("symbols", "600519.SH"), ("symbols", "000001.SZ")],
        ),
        client.get("/api/v1/market-breadth"),
        client.get(
            "/api/v1/market-comparison",
            params=[("symbols", "600519.SH"), ("symbols", "000001.SZ")],
        ),
    ]

    for response in responses:
        assert response.status_code == 503
        assert response.json()["detail"] == {
            "code": "REMOTE_NETWORK_DISABLED",
            "message": (
                "remote market access is disabled by "
                "CHAN_QUANT_REMOTE_NETWORK_ENABLED"
            ),
        }


def test_market_breadth_force_refresh_is_rejected_before_remote_access(monkeypatch) -> None:
    monkeypatch.setenv("CHAN_QUANT_REMOTE_NETWORK_ENABLED", "false")
    monkeypatch.setenv("CHAN_QUANT_ALLOW_FORCE_REFRESH", "false")

    response = client.get(
        "/api/v1/market-breadth",
        params={"market": "CN_A_SH_SZ_V1", "refresh": "true"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == {
        "code": "FORCE_REFRESH_DISABLED",
        "message": "forced market breadth refresh is disabled by runtime policy",
    }


def test_synthetic_dashboard_remains_available_when_network_is_disabled(monkeypatch) -> None:
    monkeypatch.setenv("CHAN_QUANT_REMOTE_NETWORK_ENABLED", "false")
    monkeypatch.setenv("CHAN_QUANT_DATA_SOURCE", "synthetic")

    response = client.get("/api/v1/instruments/600519.SH/dashboard")

    assert response.status_code == 200
    assert response.json()["is_mock"] is True
    assert response.json()["instrument"]["data_source"] == "deterministic-synthetic"


def test_sina_dashboard_fails_closed_when_network_is_disabled(monkeypatch) -> None:
    monkeypatch.setenv("CHAN_QUANT_REMOTE_NETWORK_ENABLED", "off")
    monkeypatch.setenv("CHAN_QUANT_DATA_SOURCE", "sina")

    response = client.get("/api/v1/instruments/600519.SH/dashboard")

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "REMOTE_NETWORK_DISABLED"
