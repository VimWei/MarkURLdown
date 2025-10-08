from __future__ import annotations


class StopRequested(Exception):
    """Raised to indicate a user-requested early stop during a conversion task.

    Handlers should raise this to unwind quickly without logging errors.
    The service layer should catch this and emit a 'stopped' event instead
    of treating it as a failure.
    """

    pass
