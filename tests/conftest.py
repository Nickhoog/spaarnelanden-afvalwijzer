"""Gedeelde fixtures voor de Spaarnelanden-tests."""

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Laat Home Assistant custom_components laden in alle tests."""
    yield
