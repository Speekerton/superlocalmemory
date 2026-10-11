"""Explicit feature opt-ins for media behavior tests."""

import pytest


@pytest.fixture
def media_enabled(_block_live_slm_home_writes):
    """Persist the real switch in this test's isolated root, without installing."""
    from superlocalmemory.runtimes import features

    status = features.enable_media(source="api", start_install=False)
    assert status["enabled"], status
    assert features.media_enabled()
