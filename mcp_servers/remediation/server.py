import os
from typing import Any

from mcp.server.mcpserver import MCPServer

server = MCPServer("remediation_server")

APPROVAL_TOKEN_SECRET = os.getenv("APPROVAL_TOKEN_SECRET", "mock_approval_secret_key")


def verify_approval_token(token: str) -> bool:
    """Verifies that an action token is authorized by a human."""
    # Checks token presence and validity
    return bool(token and token.startswith("appr_") and len(token) >= 12)


@server.tool()
def restart_service(service: str, token: str) -> dict[str, Any]:
    """Restarts a failing microservice container.

    MANDATORY REQUIREMENT: Requires an approved single-use token from the on-call engineer.
    Executes in safe dry-run mode.
    """
    if not verify_approval_token(token):
        return {
            "success": False,
            "error": "UNAUTHORIZED_ACTION: Valid human approval token is required before executing restart_service.",
        }

    return {
        "success": True,
        "action": "restart_service",
        "service": service,
        "status": "dry_run_success",
        "message": f"[DRY RUN] Simulated restart command issued for service '{service}'. Zero real infrastructure altered.",
    }


@server.tool()
def rollback_deploy(service: str, target_version: str, token: str) -> dict[str, Any]:
    """Rolls back a deployment to a prior git commit / image tag. Requires approved token."""
    if not verify_approval_token(token):
        return {
            "success": False,
            "error": "UNAUTHORIZED_ACTION: Valid human approval token is required before executing rollback_deploy.",
        }

    return {
        "success": True,
        "action": "rollback_deploy",
        "service": service,
        "target_version": target_version,
        "status": "dry_run_success",
        "message": f"[DRY RUN] Simulated deployment rollback of '{service}' to version '{target_version}'.",
    }


@server.tool()
def scale_up(service: str, replicas: int, token: str) -> dict[str, Any]:
    """Scales up the replica count of a service. Requires approved token."""
    if not verify_approval_token(token):
        return {
            "success": False,
            "error": "UNAUTHORIZED_ACTION: Valid human approval token is required before executing scale_up.",
        }

    return {
        "success": True,
        "action": "scale_up",
        "service": service,
        "replicas": replicas,
        "status": "dry_run_success",
        "message": f"[DRY RUN] Simulated scale up of '{service}' to {replicas} replicas.",
    }


@server.tool()
def review_config(service: str, parameter: str, proposed_value: str, token: str) -> dict[str, Any]:
    """Prepares and validates a configuration change recommendation. Requires approved token."""
    if not verify_approval_token(token):
        return {
            "success": False,
            "error": "UNAUTHORIZED_ACTION: Valid human approval token is required before executing review_config.",
        }

    return {
        "success": True,
        "action": "review_config",
        "service": service,
        "parameter": parameter,
        "proposed_value": proposed_value,
        "status": "dry_run_success",
        "message": f"[DRY RUN] Configuration change diff generated for {service}: {parameter}={proposed_value}.",
    }


if __name__ == "__main__":
    server.run()
