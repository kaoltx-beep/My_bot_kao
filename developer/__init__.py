from .dev_agent import analyze
from .dev_patcher import apply_plan


def create_developer_mode():
    class DeveloperMode:
        def __init__(self):
            self.analyze = analyze
            self.apply_plan = apply_plan

    return DeveloperMode()


def test_developer():
    return True
