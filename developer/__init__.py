from . import dev_agent
from . import dev_patcher
from . import dev_logger
from . import dev_git
from . import dev_sessions
from . import dev_router


class DeveloperMode:
    def __init__(self, allowed_dirs=None):
        self.router = dev_router
        self.agent = dev_agent
        self.patcher = dev_patcher
        self.git = dev_git
        self.sessions = dev_sessions
        self.logger = dev_logger


def create_developer_mode(allowed_dirs=None):
    return DeveloperMode(allowed_dirs)


__all__ = [
    "create_developer_mode",
    "DeveloperMode",
]
