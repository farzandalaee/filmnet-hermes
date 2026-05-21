import json
import tempfile
import unittest
from pathlib import Path

from state import task_store


class TaskStoreTests(unittest.TestCase):
    def test_split_legacy_tasks_normalizes_read_file_line_prefixes(self):
        text = """     1|# Active Tasks
     2|
     3|## FN-2026-0521-001
     4|- Title: First task
     5|- Status: Active
     6|
     7|## FN-2026-0521-002
     8|- Title: Second task
     9|- Status: Completed
"""

        tasks = task_store.split_legacy_tasks(text)

        self.assertEqual([task_store.task_id(t) for t in tasks], ["FN-2026-0521-001", "FN-2026-0521-002"])
        self.assertIn("## FN-2026-0521-001", tasks[0])
        self.assertIn("- Title: First task", tasks[0])

    def test_write_index_contains_only_task_ids_and_titles(self):
        tasks = [
            "## FN-2026-0521-001\n- Title: First task\n- Status: Active\n- Next step: Secret details\n",
            "## FN-2026-0521-002\n- Title: Second task\n- Status: Waiting\n- Draft summary: Long text\n",
        ]

        with tempfile.TemporaryDirectory() as tmp:
            index = Path(tmp) / "active-tasks.md"
            task_store.write_index(index, "Active Tasks", tasks)

            text = index.read_text(encoding="utf-8")

        self.assertEqual(text, "# Active Tasks\n\n- FN-2026-0521-001 — First task\n- FN-2026-0521-002 — Second task\n")
        self.assertNotIn("Secret details", text)
        self.assertNotIn("Draft summary", text)

    def test_write_task_file_upserts_one_jsonl_line_per_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp) / "state" / "active-tasks"
            task_store.write_task_file(task_dir, "## FN-2026-0521-001\n- Title: First task\n- Status: Active\n")
            task_store.write_task_file(task_dir, "## FN-2026-0521-002\n- Title: Second task\n- Status: Waiting\n")

            jsonl_path = Path(tmp) / "state" / "active-tasks.jsonl"
            lines = jsonl_path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(len(lines), 2)
        self.assertEqual([json.loads(line)["task_id"] for line in lines], ["FN-2026-0521-001", "FN-2026-0521-002"])
        self.assertIn('"task_id":"FN-2026-0521-001"', lines[0])

    def test_archive_completed_moves_task_rows_and_rebuilds_indexes(self):
        active_task = "## FN-2026-0521-001\n- Title: Keep active\n- Status: Waiting\n"
        completed_task = "## FN-2026-0521-002\n- Title: Archive me\n- Status: Completed\n"

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            active_dir = root / "state" / "active-tasks"
            history_dir = root / "state" / "history-task"
            active_index = root / "state" / "active-tasks.md"
            history_index = root / "state" / "history-task.md"
            task_store.write_task_file(active_dir, active_task)
            task_store.write_task_file(active_dir, completed_task)

            archived, remaining, skipped = task_store.archive_completed(active_dir, history_dir, active_index, history_index)

            active_rows = (root / "state" / "active-tasks.jsonl").read_text(encoding="utf-8").splitlines()
            history_rows = (root / "state" / "history-task.jsonl").read_text(encoding="utf-8").splitlines()
            active_index_text = active_index.read_text(encoding="utf-8")
            history_index_text = history_index.read_text(encoding="utf-8")

        self.assertEqual((archived, remaining, skipped), (1, 1, 0))
        self.assertEqual(len(active_rows), 1)
        self.assertEqual(json.loads(active_rows[0])["task_id"], "FN-2026-0521-001")
        self.assertEqual(len(history_rows), 1)
        self.assertEqual(json.loads(history_rows[0])["task_id"], "FN-2026-0521-002")
        self.assertEqual(active_index_text, "# Active Tasks\n\n- FN-2026-0521-001 — Keep active\n")
        self.assertEqual(history_index_text, "# History Tasks\n\n- FN-2026-0521-002 — Archive me\n")

    def test_migrate_legacy_file_is_idempotent_after_index_is_compact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            task_dir = root / "state" / "active-tasks"
            index = root / "state" / "active-tasks.md"
            task_store.write_task_file(
                task_dir,
                "## FN-2026-0521-001\n- Title: Existing task\n- Status: Waiting\n",
            )
            index.write_text("# Active Tasks\n\n- FN-2026-0521-001 — Existing task\n", encoding="utf-8")

            count = task_store.migrate_legacy_file(index, task_dir, index, "Active Tasks")

            rows = (root / "state" / "active-tasks.jsonl").read_text(encoding="utf-8").splitlines()
            index_text = index.read_text(encoding="utf-8")

        self.assertEqual(count, 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(index_text, "# Active Tasks\n\n- FN-2026-0521-001 — Existing task\n")


if __name__ == "__main__":
    unittest.main()
