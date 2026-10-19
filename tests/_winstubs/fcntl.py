"""Lege fcntl-stub, alleen voor lokaal testen op Windows (via PYTHONPATH).

Home Assistant gebruikt fcntl alleen voor de lock-file van de runner, die in tests niet
draait. Op Linux/CI wordt deze map NIET op het pad gezet.
"""

LOCK_EX = 2
LOCK_NB = 4


def flock(fd, operation):  # noqa: D103
    return None
