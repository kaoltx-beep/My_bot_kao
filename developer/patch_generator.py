"""Jarvis safe patch generator layer."""


class PatchGenerator:
    def generate(self, issue, changes=None):
        return {
            "issue": issue,
            "changes": changes or [],
            "requires_approval": True,
            "status": "PATCH_PLAN_READY"
        }


patch_generator = PatchGenerator()
