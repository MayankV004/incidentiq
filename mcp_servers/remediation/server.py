import os
from typing import Any

from mcp.server.mcpserver import MCPServer

from incidentiq.security.tokens import get_approval_secret, verify_capability_token
from mcp_servers.validation import ALLOWED_SERVICES, validate_service

server = MCPServer("remediation_server")

APPROVAL_TOKEN_SECRET = os.getenv("APPROVAL_TOKEN_SECRET", get_approval_secret())


def verify_approval_token(
    token: str,
    expected_action: str | None = None,
    expected_target: str | None = None,
    expected_incident_id: str | None = None,
    consume: bool = True,
) -> tuple[bool, str]:
    """Verifies that an action token is cryptographically authorized by a human."""
    return verify_capability_token(
        token=token,
        expected_action=expected_action,
        expected_target=expected_target,
        expected_incident_id=expected_incident_id,
        consume=consume,
    )


@server.tool()
def restart_service(service: str, token: str, incident_id: str = "") -> dict[str, Any]:
    """Restarts a failing microservice container.

    MANDATORY REQUIREMENT: Requires an approved single-use token from the on-call engineer.
    Executes in safe dry-run mode.
    """
    if not validate_service(service):
        return {
            "success": False,
            "error": f"INVALID_SERVICE: Service '{service}' is not allowed. Allowed services: {sorted(ALLOWED_SERVICES)}",
        }
    valid, reason = verify_approval_token(
        token=token,
        expected_action="restart_service",
        expected_target=service,
        expected_incident_id=incident_id or None,
    )
    if not valid:
        return {
            "success": False,
            "error": f"UNAUTHORIZED_ACTION: {reason}",
        }

    return {
        "success": True,
        "action": "restart_service",
        "service": service,
        "status": "dry_run_success",
        "message": f"[DRY RUN] Simulated restart command issued for service '{service}'. Zero real infrastructure altered.",
    }


@server.tool()
def rollback_deploy(service: str, target_version: str, token: str, incident_id: str = "") -> dict[str, Any]:
    """Rolls back a deployment to a prior git commit / image tag. Requires approved token."""
    if not validate_service(service):
        return {
            "success": False,
            "error": f"INVALID_SERVICE: Service '{service}' is not allowed. Allowed services: {sorted(ALLOWED_SERVICES)}",
        }
    valid, reason = verify_approval_token(
        token=token,
        expected_action="rollback_deploy",
        expected_target=service,
        expected_incident_id=incident_id or None,
    )
    if not valid:
        return {
            "success": False,
            "error": f"UNAUTHORIZED_ACTION: {reason}",
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
def scale_up(service: str, replicas: int, token: str, incident_id: str = "") -> dict[str, Any]:
    """Scales up the replica count of a service. Requires approved token."""
    if not validate_service(service):
        return {
            "success": False,
            "error": f"INVALID_SERVICE: Service '{service}' is not allowed. Allowed services: {sorted(ALLOWED_SERVICES)}",
        }
    valid, reason = verify_approval_token(
        token=token,
        expected_action="scale_up",
        expected_target=service,
        expected_incident_id=incident_id or None,
    )
    if not valid:
        return {
            "success": False,
            "error": f"UNAUTHORIZED_ACTION: {reason}",
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
def review_config(
    service: str, parameter: str, proposed_value: str, token: str, incident_id: str = ""
) -> dict[str, Any]:
    """Prepares and validates a configuration change recommendation. Requires approved token."""
    if not validate_service(service):
        return {
            "success": False,
            "error": f"INVALID_SERVICE: Service '{service}' is not allowed. Allowed services: {sorted(ALLOWED_SERVICES)}",
        }
    valid, reason = verify_approval_token(
        token=token,
        expected_action="review_config",
        expected_target=service,
        expected_incident_id=incident_id or None,
    )
    if not valid:
        return {
            "success": False,
            "error": f"UNAUTHORIZED_ACTION: {reason}",
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
