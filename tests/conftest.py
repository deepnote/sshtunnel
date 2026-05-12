from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent

import paramiko
import pytest

PKEY_PASSWORD = "sshtunnel"


@dataclass(frozen=True)
class SSHKeyFixture:
    """Ephemeral SSH key material generated for a test session.

    Paths are stored as str because sshtunnel's API uses isinstance(pkey, str)
    checks internally. Use Path objects only for file I/O within the fixture.
    """

    dir: Path
    plain_key_path: str
    encrypted_key_path: str
    config_path: str
    rsa_key: paramiko.RSAKey
    fingerprint: bytes

    @property
    def fingerprints(self) -> dict[str, bytes]:
        return {"ssh-rsa": self.fingerprint}


@pytest.fixture(scope="session")
def ssh_keys(tmp_path_factory: pytest.TempPathFactory) -> SSHKeyFixture:
    """Generate ephemeral RSA keys, an encrypted variant, and an SSH config."""
    tmp_dir = tmp_path_factory.mktemp("sshtunnel-keys")
    key = paramiko.RSAKey.generate(bits=2048)

    plain_path = tmp_dir / "testrsa.key"
    key.write_private_key_file(str(plain_path))
    plain_path.chmod(0o600)

    encrypted_path = tmp_dir / "testrsa_encrypted.key"
    key.write_private_key_file(str(encrypted_path), password=PKEY_PASSWORD)
    encrypted_path.chmod(0o600)

    config_path = tmp_dir / "testconfig"
    config_path.write_text(
        dedent(f"""\
        Host *
          User test
          Compression yes
          IdentityFile {plain_path}
        Host test
          ProxyCommand ssh -q -W %h:%p sshproxy
        Host other
          Port 222
          Hostname 10.0.0.1
    """)
    )

    return SSHKeyFixture(
        dir=tmp_dir,
        plain_key_path=str(plain_path),
        encrypted_key_path=str(encrypted_path),
        config_path=str(config_path),
        rsa_key=key,
        fingerprint=key.get_fingerprint(),
    )


@pytest.fixture(autouse=True)
def _inject_ssh_keys(request, ssh_keys):
    """Make ssh_keys available to unittest.TestCase classes as cls.ssh_keys."""
    if request.cls is not None:
        request.cls.ssh_keys = ssh_keys
