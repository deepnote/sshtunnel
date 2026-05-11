|CI| |pyversions| |version| |license|

``deepnote-sshtunnel`` -- Pure python SSH tunnels
==================================================

This is a `Deepnote <https://deepnote.com>`_ fork of `pahaz/sshtunnel`_ with
the following changes:

- **Python 3.10+** only (dropped Python 2 and older 3.x support)
- **paramiko 3, 4, and 5** compatibility (removed deprecated DSA/DSSKey support)
- Modern packaging with ``pyproject.toml``, ``hatchling``, and ``uv``
- GitHub Actions CI and trusted PyPI publishing

**Original author**: `Pahaz`_

**Upstream repo**: https://github.com/pahaz/sshtunnel/

Requirements
------------

* `paramiko`_ >= 3.4
* Python >= 3.10

Installation
============

``deepnote-sshtunnel`` is on PyPI, so simply run::

    pip install deepnote-sshtunnel

or::

    uv add deepnote-sshtunnel

The import name remains ``sshtunnel`` for drop-in compatibility::

    from sshtunnel import SSHTunnelForwarder

Usage scenarios
===============

One of the typical scenarios where ``sshtunnel`` is helpful is depicted in the
figure below. User may need to connect a port of a remote server (i.e. 8080)
where only SSH port (usually port 22) is reachable. ::

    ----------------------------------------------------------------------

                                |
    -------------+              |    +----------+
        LOCAL    |              |    |  REMOTE  | :22 SSH
        CLIENT   | <== SSH ========> |  SERVER  | :8080 web service
    -------------+              |    +----------+
                                |
                             FIREWALL (only port 22 is open)

    ----------------------------------------------------------------------

**Fig1**: How to connect to a service blocked by a firewall through SSH tunnel.


If allowed by the SSH server, it is also possible to reach a private server
(from the perspective of ``REMOTE SERVER``) not directly visible from the
outside (``LOCAL CLIENT``'s perspective). ::

    ----------------------------------------------------------------------

                                |
    -------------+              |    +----------+               +---------
        LOCAL    |              |    |  REMOTE  |               | PRIVATE
        CLIENT   | <== SSH ========> |  SERVER  | <== local ==> | SERVER
    -------------+              |    +----------+               +---------
                                |
                             FIREWALL (only port 443 is open)

    ----------------------------------------------------------------------

**Fig2**: How to connect to ``PRIVATE SERVER`` through SSH tunnel.


Usage examples
==============

API allows either initializing the tunnel and starting it or using a ``with``
context, which will take care of starting **and stopping** the tunnel:

Example 1
---------

Code corresponding to **Fig1** above follows, given remote server's address is
``pahaz.urfuclub.ru``, password authentication and randomly assigned local bind
port.

.. code-block:: python

    from sshtunnel import SSHTunnelForwarder

    server = SSHTunnelForwarder(
        'alfa.8iq.dev',
        ssh_username="pahaz",
        ssh_password="secret",
        remote_bind_address=('127.0.0.1', 8080)
    )

    server.start()

    print(server.local_bind_port)  # show assigned local port
    # work with `SECRET SERVICE` through `server.local_bind_port`.

    server.stop()

Example 2
---------

Example of a port forwarding to a private server not directly reachable,
assuming password protected pkey authentication, remote server's SSH service is
listening on port 443 and that port is open in the firewall (**Fig2**):

.. code-block:: python

    import paramiko
    import sshtunnel

    with sshtunnel.open_tunnel(
        (REMOTE_SERVER_IP, 443),
        ssh_username="",
        ssh_pkey="/var/ssh/rsa_key",
        ssh_private_key_password="secret",
        remote_bind_address=(PRIVATE_SERVER_IP, 22),
        local_bind_address=('0.0.0.0', 10022)
    ) as tunnel:
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect('127.0.0.1', 10022)
        # do some operations with client session
        client.close()

    print('FINISH!')

Example 3
---------

Example of a port forwarding for the Vagrant MySQL local port:

.. code-block:: python

    from sshtunnel import open_tunnel
    from time import sleep

    with open_tunnel(
        ('localhost', 2222),
        ssh_username="vagrant",
        ssh_password="vagrant",
        remote_bind_address=('127.0.0.1', 3306)
    ) as server:

        print(server.local_bind_port)
        while True:
            # press Ctrl-C for stopping
            sleep(1)

    print('FINISH!')

Or simply using the CLI:

.. code-block:: console

    (bash)$ python -m sshtunnel -U vagrant -P vagrant -L :3306 -R 127.0.0.1:3306 -p 2222 localhost

Example 4
---------

Opening an SSH session jumping over two tunnels. SSH transport and tunnels
will be daemonised, which will not wait for the connections to stop at close
time.

.. code-block:: python

    import sshtunnel
    from paramiko import SSHClient


    with sshtunnel.open_tunnel(
        ssh_address_or_host=('GW1_ip', 20022),
        remote_bind_address=('GW2_ip', 22),
    ) as tunnel1:
        print('Connection to tunnel1 (GW1_ip:GW1_port) OK...')
        with sshtunnel.open_tunnel(
            ssh_address_or_host=('localhost', tunnel1.local_bind_port),
            remote_bind_address=('target_ip', 22),
            ssh_username='GW2_user',
            ssh_password='GW2_pwd',
        ) as tunnel2:
            print('Connection to tunnel2 (GW2_ip:GW2_port) OK...')
            with SSHClient() as ssh:
                ssh.connect('localhost',
                    port=tunnel2.local_bind_port,
                    username='target_user',
                    password='target_pwd',
                )
                ssh.exec_command(...)


.. _Pahaz: https://github.com/pahaz
.. _pahaz/sshtunnel: https://github.com/pahaz/sshtunnel
.. _paramiko: http://www.paramiko.org/
.. |CI| image:: https://github.com/deepnote/sshtunnel/actions/workflows/ci.yml/badge.svg
   :target: https://github.com/deepnote/sshtunnel/actions/workflows/ci.yml
.. |pyversions| image:: https://img.shields.io/pypi/pyversions/deepnote-sshtunnel.svg
.. |version| image:: https://img.shields.io/pypi/v/deepnote-sshtunnel.svg
   :target: https://pypi.org/project/deepnote-sshtunnel/
.. |license| image::  https://img.shields.io/pypi/l/deepnote-sshtunnel.svg
   :target: https://github.com/deepnote/sshtunnel/blob/main/LICENSE
