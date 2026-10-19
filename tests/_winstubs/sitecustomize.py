"""Alleen voor lokaal testen op Windows (via PYTHONPATH).

De asyncio-eventloop op Windows maakt intern een socketpair over loopback; de
socket-blokkade van pytest-homeassistant-custom-component zou dat breken. Hier wordt die
blokkade uitgeschakeld. Op Linux/CI blijft de blokkade actief (deze map staat daar niet
op het pad). De tests zelf mocken alle HTTP via aioclient_mock.
"""

import pytest_socket

pytest_socket.disable_socket = lambda *args, **kwargs: None
