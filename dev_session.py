"""In-process pending Developer Mode patch session."""

_pending = None


def set_pending(plan):
    global _pending
    _pending = plan


def get_pending():
    return _pending


def clear_pending():
    global _pending
    _pending = None
