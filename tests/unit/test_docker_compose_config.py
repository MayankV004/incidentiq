import shutil
import subprocess
from pathlib import Path

import yaml


def test_compose_yaml_files_structure():
    compose_path = Path(__file__).parents[2] / "deploy" / "docker-compose.yml"
    override_path = Path(__file__).parents[2] / "deploy" / "docker-compose.override.yml"

    assert compose_path.exists(), "docker-compose.yml must exist"
    assert override_path.exists(), "docker-compose.override.yml must exist"

    with open(compose_path) as f:
        prod_data = yaml.safe_load(f)

    services = prod_data.get("services", {})
    assert "caddy" in services, "caddy reverse proxy must be in prod compose"

    # Verify only caddy has host published ports in prod config
    caddy_ports = services["caddy"].get("ports", [])
    assert any("80:80" in str(p) for p in caddy_ports), "caddy must expose port 80"
    assert any("443:443" in str(p) for p in caddy_ports), "caddy must expose port 443"

    # All internal microservices must not have public host port mappings in prod
    internal_services = [
        "fake-external",
        "payments",
        "orders",
        "gateway",
        "mcp-metrics",
        "mcp-logs",
        "mcp-remediation",
        "incidentiq-api",
        "ui",
    ]
    for s_name in internal_services:
        s_config = services.get(s_name, {})
        assert "ports" not in s_config, (
            f"Internal service '{s_name}' must not have host ports in prod compose"
        )
        assert "expose" in s_config, (
            f"Internal service '{s_name}' should use 'expose' in prod compose"
        )

    # Verify override binds strictly to 127.0.0.1
    with open(override_path) as f:
        override_data = yaml.safe_load(f)

    override_services = override_data.get("services", {})
    for s_name in internal_services:
        assert s_name in override_services, f"Override must declare ports for {s_name}"
        ports = override_services[s_name].get("ports", [])
        for p in ports:
            assert str(p).startswith("127.0.0.1:"), (
                f"Port mapping for {s_name} ({p}) must bind strictly to 127.0.0.1"
            )


def test_prod_compose_uses_real_dockerfiles_and_hardening():
    """BLOCKER-1: Prod compose must use multi-stage Dockerfiles, healthchecks, restarts, and limits."""
    repo_root = Path(__file__).parents[2]
    compose_path = repo_root / "deploy" / "docker-compose.yml"
    with open(compose_path) as f:
        prod_data = yaml.safe_load(f)

    services = prod_data.get("services", {})
    assert len(services) > 0

    py_df = repo_root / "deploy" / "Dockerfile.python"
    ui_df = repo_root / "deploy" / "Dockerfile.ui"
    assert py_df.exists(), "deploy/Dockerfile.python must exist"
    assert ui_df.exists(), "deploy/Dockerfile.ui must exist"
    assert "uv sync --frozen --no-dev" in py_df.read_text()
    ui_df_text = ui_df.read_text()
    assert "pnpm install --frozen-lockfile" in ui_df_text
    assert "CI=true" in ui_df_text

    for s_name, s_cfg in services.items():
        if "build" in s_cfg:
            assert "dockerfile_inline" not in s_cfg["build"], (
                f"{s_name} must not use dockerfile_inline"
            )
            assert "dockerfile" in s_cfg["build"], (
                f"{s_name} must reference a real Dockerfile"
            )
        assert "healthcheck" in s_cfg, f"{s_name} must define a healthcheck"
        assert s_cfg.get("restart") in ("unless-stopped", "always"), (
            f"{s_name} must define restart policy"
        )
        assert "mem_limit" in s_cfg and "cpus" in s_cfg, (
            f"{s_name} must define mem_limit and cpus resource limits"
        )


def test_docker_compose_cli_validation():
    docker_compose = shutil.which("docker")
    if not docker_compose:
        return

    repo_root = Path(__file__).parents[2]
    cmd = [
        "docker",
        "compose",
        "-f",
        str(repo_root / "deploy" / "docker-compose.yml"),
        "-f",
        str(repo_root / "deploy" / "docker-compose.override.yml"),
        "config",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert result.returncode == 0, f"docker compose config failed: {result.stderr}"
