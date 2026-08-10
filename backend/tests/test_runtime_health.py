from fastapi.testclient import TestClient

from chan_quant.api.app import create_app


def _set_production_environment(monkeypatch, **overrides: str) -> None:
    values = {
        "CHAN_QUANT_ENVIRONMENT": "production",
        "CHAN_QUANT_DATA_SOURCE": "synthetic",
        "CHAN_QUANT_REMOTE_NETWORK_ENABLED": "false",
        "CHAN_QUANT_ALLOW_FORCE_REFRESH": "false",
        "CHAN_QUANT_DOCS_ENABLED": "false",
        "CHAN_QUANT_ALLOWED_HOSTS": "testserver,localhost,127.0.0.1",
        "CHAN_QUANT_RELEASE_SHA": "b0a628054e08bd4d975d7ab8b2ea8e55a64eabe4",
    }
    values.update(overrides)
    for name, value in values.items():
        monkeypatch.setenv(name, value)


def test_liveness_is_fixed_and_readiness_accepts_offline_production(monkeypatch) -> None:
    _set_production_environment(monkeypatch)
    client = TestClient(create_app())

    assert client.get("/healthz").json() == {
        "status": "alive",
        "service": "chan-quant-api",
    }
    ready = client.get("/readyz")
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready", "service": "chan-quant-api"}


def test_readiness_rejects_invalid_configuration_without_echoing_values(monkeypatch) -> None:
    _set_production_environment(
        monkeypatch,
        CHAN_QUANT_REMOTE_NETWORK_ENABLED="secret-invalid-value",
    )
    client = TestClient(create_app())

    response = client.get("/readyz")

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "RUNTIME_CONFIGURATION_INVALID"
    assert "secret-invalid-value" not in response.text


def test_readiness_rejects_missing_csv_without_leaking_absolute_path(
    monkeypatch,
    tmp_path,
) -> None:
    missing_path = tmp_path / "private" / "bars.csv"
    _set_production_environment(
        monkeypatch,
        CHAN_QUANT_DATA_SOURCE="csv",
        CHAN_QUANT_CSV_PATH=str(missing_path),
    )
    client = TestClient(create_app())

    response = client.get("/readyz")

    assert response.status_code == 503
    assert response.json()["detail"] == {
        "code": "RUNTIME_DATA_PATH_UNAVAILABLE",
        "message": "configured csv data path is not a readable file",
    }
    assert str(missing_path) not in response.text


def test_version_and_capabilities_return_deployment_contract(monkeypatch) -> None:
    _set_production_environment(monkeypatch)
    client = TestClient(create_app())

    assert client.get("/version").json() == {
        "application_version": "0.1.0",
        "strategy_version": "independent-v0.1.0",
        "environment": "production",
        "release_sha": "b0a628054e08bd4d975d7ab8b2ea8e55a64eabe4",
    }
    assert client.get("/api/v1/runtime-capabilities").json() == {
        "data_mode": "synthetic",
        "remote_network_enabled": False,
        "force_refresh_enabled": False,
        "research_preview": True,
        "release_sha": "b0a628054e08bd4d975d7ab8b2ea8e55a64eabe4",
    }


def test_production_disables_api_documentation(monkeypatch) -> None:
    _set_production_environment(monkeypatch)
    production_client = TestClient(create_app())

    assert production_client.get("/docs").status_code == 404
    assert production_client.get("/openapi.json").status_code == 404

    monkeypatch.setenv("CHAN_QUANT_ENVIRONMENT", "development")
    monkeypatch.setenv("CHAN_QUANT_DOCS_ENABLED", "true")
    development_client = TestClient(create_app())
    assert development_client.get("/docs").status_code == 200
    assert development_client.get("/openapi.json").status_code == 200


def test_allowed_host_middleware_rejects_unknown_host(monkeypatch) -> None:
    _set_production_environment(monkeypatch)
    client = TestClient(create_app())

    response = client.get("/healthz", headers={"Host": "attacker.example"})

    assert response.status_code == 400
