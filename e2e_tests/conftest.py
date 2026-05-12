import shutil
import tempfile
import time
from pathlib import Path
from textwrap import dedent

import paramiko
import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.core.network import Network
from testcontainers.core.wait_strategies import LogMessageWaitStrategy
from testcontainers.core.waiting_utils import wait_for_logs

PG_USER = "postgres"
PG_PASSWORD = "postgres"
PG_DB = "main"

MYSQL_USER = "mysql"
MYSQL_PASSWORD = "mysql"
MYSQL_DB = "main"

MONGO_USER = "mongo"
MONGO_PASSWORD = "mongo"
MONGO_DB = "main"

OPENSSH_SERVER_IMAGE = (
    "linuxserver/openssh-server:10.2_p1-r0-ls225"
    "@sha256:29d4e3f887596c4c2fc609f4e07040b08890a238178da400ffa2a602b55245bc"
)


def _generate_ssh_keypair(directory: Path) -> Path:
    """Generate an ephemeral RSA keypair for the test run."""
    key = paramiko.RSAKey.generate(bits=2048)

    private_key_path = directory / "ssh_host_rsa_key"
    key.write_private_key_file(str(private_key_path))
    private_key_path.chmod(0o600)

    public_key_path = directory / "ssh_host_rsa_key.pub"
    public_key_path.write_text(f"{key.get_name()} {key.get_base64()}")
    public_key_path.chmod(0o600)

    return private_key_path


def _generate_sshd_config(directory: Path) -> Path:
    """Generate an sshd_config that permits TCP forwarding."""
    config_path = directory / "sshd_config"
    config_path.write_text(dedent("""\
        Port 2222
        PermitRootLogin no
        PasswordAuthentication no
        PubkeyAuthentication yes
        AllowTcpForwarding yes
        GatewayPorts no
        X11Forwarding no
        PrintMotd no
        AcceptEnv LANG LC_*
        Subsystem sftp /usr/lib/ssh/sftp-server
        AuthorizedKeysFile .ssh/authorized_keys
    """))
    return config_path


@pytest.fixture(scope="session")
def e2e_infrastructure():
    """Spin up SSH + database containers on a shared Docker network."""
    tmp_key_dir = Path(tempfile.mkdtemp(prefix="sshtunnel-e2e-keys-"))
    private_key_path = _generate_ssh_keypair(tmp_key_dir)
    sshd_config_path = _generate_sshd_config(tmp_key_dir)

    with Network() as network:
        postgres = (
            DockerContainer("postgres:17")
            .with_env("POSTGRES_USER", PG_USER)
            .with_env("POSTGRES_PASSWORD", PG_PASSWORD)
            .with_env("POSTGRES_DB", PG_DB)
            .with_network(network)
            .with_network_aliases("postgres-db")
        )

        mysql = (
            DockerContainer("mysql:8.4")
            .with_env("MYSQL_DATABASE", MYSQL_DB)
            .with_env("MYSQL_USER", MYSQL_USER)
            .with_env("MYSQL_PASSWORD", MYSQL_PASSWORD)
            .with_env("MYSQL_ROOT_PASSWORD", "rootpw")
            .with_network(network)
            .with_network_aliases("mysql-db")
        )

        mongo = (
            DockerContainer("mongo:8")
            .with_env("MONGO_INITDB_ROOT_USERNAME", MONGO_USER)
            .with_env("MONGO_INITDB_ROOT_PASSWORD", MONGO_PASSWORD)
            .with_env("MONGO_INITDB_DATABASE", MONGO_DB)
            .with_network(network)
            .with_network_aliases("mongo-db")
        )

        ssh = (
            DockerContainer(OPENSSH_SERVER_IMAGE)
            .with_env("PUID", "1000")
            .with_env("PGID", "1000")
            .with_env("TZ", "UTC")
            .with_env("PUBLIC_KEY_FILE", "/config/ssh_host_keys/ssh_host_rsa_key.pub")
            .with_env("SUDO_ACCESS", "false")
            .with_env("PASSWORD_ACCESS", "false")
            .with_env("USER_NAME", "linuxserver")
            .with_env("LISTEN_PORT", "2222")
            .with_volume_mapping(str(tmp_key_dir), "/config/ssh_host_keys", "ro")
            .with_volume_mapping(str(sshd_config_path), "/config/sshd_config", "ro")
            .with_exposed_ports(2222)
            .with_network(network)
            .with_network_aliases("ssh-server")
        )

        with postgres, mysql, mongo, ssh:
            wait_for_logs(postgres, LogMessageWaitStrategy("database system is ready to accept connections"), timeout=60)
            wait_for_logs(mysql, LogMessageWaitStrategy("port: 3306"), timeout=90)
            wait_for_logs(mongo, LogMessageWaitStrategy("Waiting for connections"), timeout=60)
            wait_for_logs(ssh, LogMessageWaitStrategy("done."), timeout=60)

            time.sleep(2)

            yield {
                "ssh_host": ssh.get_container_host_ip(),
                "ssh_port": int(ssh.get_exposed_port(2222)),
                "ssh_username": "linuxserver",
                "ssh_pkey": str(private_key_path),
                "pg": {"host": "postgres-db", "port": 5432},
                "mysql": {"host": "mysql-db", "port": 3306},
                "mongo": {"host": "mongo-db", "port": 27017},
            }

    shutil.rmtree(tmp_key_dir, ignore_errors=True)
