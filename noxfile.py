import nox

nox.options.default_venv_backend = "uv"
nox.options.reuse_venv = "yes"

PYTHON_VERSIONS = ["3.10", "3.11", "3.12", "3.13"]
PARAMIKO_VERSIONS = ["paramiko>=3.4,<4", "paramiko>=4,<5", "paramiko>=5,<6"]


@nox.session(python=PYTHON_VERSIONS)
@nox.parametrize("paramiko", PARAMIKO_VERSIONS)
def tests(session: nox.Session, paramiko: str) -> None:
    """Run the test suite against a specific paramiko version."""
    session.install("-e", ".[test]")
    session.install(paramiko)
    session.run(
        "pytest",
        "tests/",
        "-n4",
        "--cov=sshtunnel",
        "--cov-report=term",
        *session.posargs,
    )


@nox.session(python=["3.13"])
def e2e(session: nox.Session) -> None:
    """Run e2e tests with testcontainers (requires Docker)."""
    session.install("-e", ".[test,e2e]")
    session.run("pytest", "e2e_tests/", "-v", *session.posargs)


@nox.session
def lint(session: nox.Session) -> None:
    """Run ruff linter and formatter checks."""
    session.install("ruff")
    session.run("ruff", "check", ".")
    session.run("ruff", "format", "--check", ".")
