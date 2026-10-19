"""Minimale resource-stub, alleen voor lokaal testen op Windows (via PYTHONPATH)."""

RLIMIT_NOFILE = 7
error = OSError


def getrlimit(resource):  # noqa: D103
    return (2048, 2048)


def setrlimit(resource, limits):  # noqa: D103
    return None
