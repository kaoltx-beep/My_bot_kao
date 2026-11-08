import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core import approval


class ApprovalSecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store_patch = patch.object(approval, "STORE", Path(self.temp_dir.name) / "approvals.json")
        self.store_patch.start()

    def tearDown(self):
        self.store_patch.stop()
        self.temp_dir.cleanup()

    def make_request(self, **kwargs):
        return approval.create(
            "mcp:read_status",
            {"detail": "brief"},
            chat_id=-100123,
            user_id=456,
            now=1000,
            **kwargs,
        )

    def test_approval_is_bound_to_chat_and_user(self):
        approval_id = self.make_request()
        self.assertIsNone(
            approval.consume(approval_id, "approved", chat_id=-100999, user_id=456, now=1001)
        )
        self.assertIsNone(
            approval.consume(approval_id, "approved", chat_id=-100123, user_id=999, now=1001)
        )
        item = approval.consume(
            approval_id, "approved", chat_id=-100123, user_id=456, now=1001
        )
        self.assertEqual(item["status"], "approved")
        self.assertEqual(item["tool"], "mcp:read_status")

    def test_expired_approval_cannot_be_consumed(self):
        approval_id = self.make_request(ttl_seconds=30)
        self.assertIsNone(
            approval.consume(approval_id, "approved", chat_id=-100123, user_id=456, now=1030)
        )
        self.assertEqual(approval.get(approval_id)["status"], "expired")

    def test_approval_is_one_time_only(self):
        approval_id = self.make_request()
        first = approval.consume(
            approval_id, "approved", chat_id=-100123, user_id=456, now=1001
        )
        second = approval.consume(
            approval_id, "approved", chat_id=-100123, user_id=456, now=1002
        )
        self.assertIsNotNone(first)
        self.assertIsNone(second)

    def test_invalid_status_is_rejected(self):
        approval_id = self.make_request()
        with self.assertRaises(ValueError):
            approval.consume(
                approval_id, "executed", chat_id=-100123, user_id=456, now=1001
            )

    def test_legacy_record_without_expiry_fails_closed(self):
        approval_id = "legacy-id"
        approval.STORE.write_text(
            '{"legacy-id": {"tool": "mcp:read_status", "params": {}, '
            '"chat_id": -100123, "user_id": 456, "status": "pending"}}',
            encoding="utf-8",
        )
        self.assertIsNone(
            approval.consume(
                approval_id, "approved", chat_id=-100123, user_id=456, now=1001
            )
        )
        self.assertEqual(approval.get(approval_id)["status"], "expired")

    def test_ttl_is_bounded(self):
        with self.assertRaises(ValueError):
            self.make_request(ttl_seconds=3600)


if __name__ == "__main__":
    unittest.main()
