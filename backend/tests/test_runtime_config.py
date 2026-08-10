import pytest

from chan_quant.runtime_config import RuntimeConfigError, load_runtime_config


def test_development_defaults_preserve_local_behavior() -> None:
    config = load_runtime_config({})

    assert config.environment == "development"
    assert config.data_mode == "synthetic"
    assert config.remote_network_enabled is True
    assert config.force_refresh_enabled is False
    assert config.docs_enabled is True
    assert config.allowed_hosts == ("localhost", "127.0.0.1", "testserver")
    assert config.release_sha == "development"


def test_explicit_production_offline_configuration_is_valid() -> None:
    config = load_runtime_config(
        {
            "CHAN_QUANT_ENVIRONMENT": "production",
            "CHAN_QUANT_DATA_SOURCE": "synthetic",
            "CHAN_QUANT_REMOTE_NETWORK_ENABLED": "false",
            "CHAN_QUANT_ALLOW_FORCE_REFRESH": "false",
            "CHAN_QUANT_DOCS_ENABLED": "false",
            "CHAN_QUANT_ALLOWED_HOSTS": "localhost,127.0.0.1",
            "CHAN_QUANT_RELEASE_SHA": "b0a628054e08bd4d975d7ab8b2ea8e55a64eabe4",
        }
    )

    assert config.environment == "production"
    assert config.data_mode == "synthetic"
    assert config.remote_network_enabled is False
    assert config.force_refresh_enabled is False
    assert config.docs_enabled is False
    assert config.allowed_hosts == ("localhost", "127.0.0.1")


@pytest.mark.parametrize(
    "name",
    [
        "CHAN_QUANT_REMOTE_NETWORK_ENABLED",
        "CHAN_QUANT_ALLOW_FORCE_REFRESH",
        "CHAN_QUANT_DOCS_ENABLED",
    ],
)
def test_boolean_configuration_rejects_ambiguous_values(name: str) -> None:
    with pytest.raises(RuntimeConfigError, match=name):
        load_runtime_config({name: "sometimes"})


def test_production_requires_explicit_deployment_contract() -> None:
    with pytest.raises(RuntimeConfigError, match="production requires explicit"):
        load_runtime_config({"CHAN_QUANT_ENVIRONMENT": "production"})


def test_production_requires_a_git_release_sha() -> None:
    with pytest.raises(RuntimeConfigError, match="hexadecimal Git SHA"):
        load_runtime_config(
            {
                "CHAN_QUANT_ENVIRONMENT": "production",
                "CHAN_QUANT_DATA_SOURCE": "synthetic",
                "CHAN_QUANT_REMOTE_NETWORK_ENABLED": "false",
                "CHAN_QUANT_ALLOW_FORCE_REFRESH": "false",
                "CHAN_QUANT_DOCS_ENABLED": "false",
                "CHAN_QUANT_ALLOWED_HOSTS": "localhost,127.0.0.1",
                "CHAN_QUANT_RELEASE_SHA": "development",
            }
        )


@pytest.mark.parametrize(
    "hosts",
    ["", "https://example.com", "example.com/path", "example.com:8080", "*"],
)
def test_allowed_hosts_reject_empty_or_unsafe_entries(hosts: str) -> None:
    with pytest.raises(RuntimeConfigError, match="CHAN_QUANT_ALLOWED_HOSTS"):
        load_runtime_config({"CHAN_QUANT_ALLOWED_HOSTS": hosts})
