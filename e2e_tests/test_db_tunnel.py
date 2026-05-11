"""E2E tests: verify SSH tunnels to real database containers."""

import pytest
from sshtunnel import SSHTunnelForwarder

from .conftest import PG_USER, PG_PASSWORD, PG_DB, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB, MONGO_USER, MONGO_PASSWORD

pytestmark = pytest.mark.timeout(120)


def _make_tunnel(infra, remote_bind_addresses):
    """Create (but don't start) an SSHTunnelForwarder from the fixture data."""
    return SSHTunnelForwarder(
        (infra["ssh_host"], infra["ssh_port"]),
        ssh_username=infra["ssh_username"],
        ssh_pkey=infra["ssh_pkey"],
        remote_bind_addresses=remote_bind_addresses,
    )


class TestPostgresTunnel:
    def test_query_via_tunnel(self, e2e_infrastructure):
        import psycopg2

        infra = e2e_infrastructure
        pg = infra["pg"]

        with _make_tunnel(infra, [(pg["host"], pg["port"])]) as tunnel:
            conn = psycopg2.connect(
                host="127.0.0.1",
                port=tunnel.local_bind_port,
                database=PG_DB,
                user=PG_USER,
                password=PG_PASSWORD,
            )
            cur = conn.cursor()
            cur.execute("SELECT version()")
            result = cur.fetchone()[0]
            conn.close()

        assert "PostgreSQL" in result


class TestMySQLTunnel:
    def test_query_via_tunnel(self, e2e_infrastructure):
        import pymysql

        infra = e2e_infrastructure
        mysql = infra["mysql"]

        with _make_tunnel(infra, [(mysql["host"], mysql["port"])]) as tunnel:
            conn = pymysql.connect(
                host="127.0.0.1",
                port=tunnel.local_bind_port,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                database=MYSQL_DB,
                connect_timeout=10,
                read_timeout=10,
            )
            cursor = conn.cursor()
            cursor.execute("SELECT version()")
            result = cursor.fetchone()[0]
            conn.close()

        assert result  # non-empty version string


class TestMongoTunnel:
    def test_query_via_tunnel(self, e2e_infrastructure):
        import pymongo

        infra = e2e_infrastructure
        mongo = infra["mongo"]

        with _make_tunnel(infra, [(mongo["host"], mongo["port"])]) as tunnel:
            client = pymongo.MongoClient(
                "127.0.0.1",
                tunnel.local_bind_port,
                username=MONGO_USER,
                password=MONGO_PASSWORD,
            )
            info = client.server_info()
            client.close()

        assert "version" in info


class TestMultiTunnel:
    def test_all_databases_via_single_tunnel(self, e2e_infrastructure):
        """Open a single SSH tunnel forwarding to all three databases at once."""
        import psycopg2
        import pymysql
        import pymongo

        infra = e2e_infrastructure
        pg = infra["pg"]
        mysql = infra["mysql"]
        mongo = infra["mongo"]

        remote_binds = [
            (pg["host"], pg["port"]),
            (mysql["host"], mysql["port"]),
            (mongo["host"], mongo["port"]),
        ]

        with _make_tunnel(infra, remote_binds) as tunnel:
            pg_port, mysql_port, mongo_port = tunnel.local_bind_ports

            # Postgres
            pg_conn = psycopg2.connect(
                host="127.0.0.1",
                port=pg_port,
                database=PG_DB,
                user=PG_USER,
                password=PG_PASSWORD,
            )
            pg_cur = pg_conn.cursor()
            pg_cur.execute("SELECT 1")
            assert pg_cur.fetchone() == (1,)
            pg_conn.close()

            # MySQL
            mysql_conn = pymysql.connect(
                host="127.0.0.1",
                port=mysql_port,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                database=MYSQL_DB,
                connect_timeout=10,
            )
            mysql_cur = mysql_conn.cursor()
            mysql_cur.execute("SELECT 1")
            assert mysql_cur.fetchone() == (1,)
            mysql_conn.close()

            # MongoDB
            mongo_client = pymongo.MongoClient(
                "127.0.0.1",
                mongo_port,
                username=MONGO_USER,
                password=MONGO_PASSWORD,
            )
            assert mongo_client.server_info()["ok"] == 1.0
            mongo_client.close()
