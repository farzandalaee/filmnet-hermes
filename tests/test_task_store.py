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

    def test_archive_completed_moves_task_files_and_rebuilds_indexes(self):
        active_task = "## FN-2026-0521-001\n- Title: Keep active\n- Status: Waiting\n"
        completed_task = "## FN-2026-0521-002\n- Title: Archive me\n- Status: Completed\n"

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            active_dir = root / "state" / "active-tasks"
            history_dir = root / "state" / "history-task"
            active_index = root / "state" / "active-tasks.md"
            history_index = root / "state" / "history-task.md"
            active_dir.mkdir(parents=True)
            history_dir.mkdir(parents=True)
            (active_dir / "FN-2026-0521-001.md").write_text(active_task, encoding="utf-8")
            (active_dir / "FN-2026-0521-002.md").write_text(completed_task, encoding="utf-8")

            archived, remaining, skipped = task_store.archive_completed(active_dir, history_dir, active_index, history_index)

            self.assertEqual((archived, remaining, skipped), (1, 1, 0))
            self.assertTrue((active_dir / "FN-2026-0521-001.md").exists())
            self.assertFalse((active_dir / "FN-2026-0521-002.md").exists())
            self.assertTrue((history_dir / "FN-2026-0521-002.md").exists())
            self.assertEqual(active_index.read_text(encoding="utf-8"), "# Active Tasks\n\n- FN-2026-0521-001 — Keep active\n")
            self.assertEqual(history_index.read_text(encoding="utf-8"), "# History Tasks\n\n- FN-2026-0521-002 — Archive me\n")
    def test_migrate_legacy_file_is_idempotent_after_index_is_compact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            task_dir = root / "state" / "active-tasks"
            index = root / "state" / "active-tasks.md"
            task_dir.mkdir(parents=True)
            (task_dir / "FN-2026-0521-001.md").write_text(
                "## FN-2026-0521-001\n- Title: Existing task\n- Status: Waiting\n",
                encoding="utf-8",
            )
            index.write_text("# Active Tasks\n\n- FN-2026-0521-001 — Existing task\n", encoding="utf-8")

            count = task_store.migrate_legacy_file(index, task_dir, index, "Active Tasks")

            self.assertEqual(count, 1)
            self.assertEqual(index.read_text(encoding="utf-8"), "# Active Tasks\n\n- FN-2026-0521-001 — Existing task\n")


if __name__ == "__main__":
    unittest.main()
