from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def speed_up_convert_service(monkeypatch):
    """Avoid small blocking sleeps inside ConvertService during tests.

    This keeps production behavior unchanged while making service tests faster.
    """
    try:
        import markdownall.services.convert_service as cs

        monkeypatch.setattr(cs.time, "sleep", lambda *_args, **_kwargs: None)
    except Exception:
        # If module path changes, do not fail tests due to this optimization
        pass



