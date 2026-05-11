"""E2E test: verify an SSH tunnel starts, stays alive briefly, and stops cleanly."""

import time

import pytest
from sshtunnel import SSHTunnelForwarder

pytestmark = pytest.mark.timeout(60)


def test_tunnel_does_not_hang_on_start_stop(e2e_infrastructure):
    """Start a tunnel, verify it's alive, then stop it without hanging."""
    infra = e2e_infrastructure
    pg = infra["pg"]

    tunnel = SSHTunnelForwarder(
        (infra["ssh_host"], infra["ssh_port"]),
        ssh_username=infra["ssh_username"],
        ssh_pkey=infra["ssh_pkey"],
        remote_bind_addresses=[(pg["host"], pg["port"])],
    )

    tunnel.start()
    assert tunnel.is_alive
    assert tunnel.is_active

    time.sleep(2)

    assert tunnel.is_alive
    assert tunnel.is_active

    tunnel.stop()
    assert not tunnel.is_alive


def test_tunnel_context_manager_does_not_hang(e2e_infrastructure):
    """Verify the context manager enters and exits without hanging."""
    infra = e2e_infrastructure
    pg = infra["pg"]

    with SSHTunnelForwarder(
        (infra["ssh_host"], infra["ssh_port"]),
        ssh_username=infra["ssh_username"],
        ssh_pkey=infra["ssh_pkey"],
        remote_bind_addresses=[(pg["host"], pg["port"])],
    ) as tunnel:
        assert tunnel.is_alive
        time.sleep(1)

    assert not tunnel.is_alive
