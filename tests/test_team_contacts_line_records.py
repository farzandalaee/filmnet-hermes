import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import messenger_event_assistant, messenger_telegram_intake


LINE_RECORDS = """# FilmNet Team Directory

One contact per line. Grep by English name, alias, Persian name, Telegram username, Telegram ID, role, organization, or ownership keyword.

CONTACT | name=Farzan Dalaee | name-fa=فرزان | family-fa=دالایی | role=CTO/CPO | organization=CTO/CPO | email=farzan.dalaee@gmail.com | mobile=+989****8710 | telegram=@farzandalaee | telegram_id=88227782
CONTACT | name=Mohammad Ziaee | name-fa=محمد | family-fa=ضیایی | aliases=Mohammad DevOps | role=Full-stack / DevOps | organization=DevOps | domain_ownership=Payment integration, CDN configuration, DevOps infrastructure | tech_stack_areas=Payments, CDN, CI/CD pipelines | email=[to be filled] | mobile=+989****2227 | telegram=@mzDAN | telegram_id=179982076
"""


class TeamContactsLineRecordTests(unittest.TestCase):
    def test_parse_team_contacts_reads_one_line_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "team-contacts.md"
            path.write_text(LINE_RECORDS, encoding="utf-8")

            contacts = messenger_telegram_intake.parse_team_contacts(path)

        self.assertEqual(contacts["179982076"]["name"], "Mohammad Ziaee")
        self.assertEqual(contacts["179982076"]["telegram_username"], "@mzDAN")
        self.assertEqual(contacts["179982076"]["name_fa"], "محمد")
        self.assertEqual(contacts["179982076"]["role"], "Full-stack / DevOps")

    def test_load_farzan_chat_id_reads_one_line_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "team-contacts.md"
            path.write_text(LINE_RECORDS, encoding="utf-8")

            with mock.patch.object(messenger_event_assistant, "TEAM_CONTACTS", path), mock.patch.object(
                messenger_event_assistant, "load_env", return_value={}
            ):
                chat_id = messenger_event_assistant.load_farzan_chat_id()

        self.assertEqual(chat_id, "88227782")


if __name__ == "__main__":
    unittest.main()
