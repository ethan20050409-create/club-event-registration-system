import os
import tempfile
import unittest
from datetime import datetime

from event_manager import EventManager
from registration_manager import RegistrationManager
from room_manager import RoomManager
from storage import Storage


NOW = datetime(2030, 1, 1, 9, 0)


def make_room(room_id, name, capacity=20, status="available"):
    return {
        "room_id": room_id,
        "name": name,
        "capacity": capacity,
        "status": status,
    }


def make_event(
    event_id,
    title,
    room_id,
    room_name,
    start_hour,
    end_hour,
    capacity=1,
    deadline_hour=10,
    organizer_id="ORG",
):
    return {
        "event_id": event_id,
        "organizer_id": organizer_id,
        "title": title,
        "start_time": datetime(2030, 1, 2, start_hour, 0),
        "end_time": datetime(2030, 1, 2, end_hour, 0),
        "room_id": room_id,
        "room_name": room_name,
        "capacity": capacity,
        "deadline": datetime(2030, 1, 2, deadline_hour, 0),
        "description": "",
    }


def make_data():
    return {
        "rooms": [
            make_room("R001", "A101"),
            make_room("R002", "A102"),
            make_room("R003", "B201"),
        ],
        "events": [],
        "registrations": [],
        "waitlist": [],
        "notifications": [],
    }


class EventTests(unittest.TestCase):
    def test_same_room_overlap_is_rejected_but_touching_time_is_allowed(self):
        data = make_data()
        data["events"].append(
            make_event("E001", "First", "R001", "A101", 14, 15, capacity=10)
        )
        manager = EventManager(data)

        success, message, event, conflicts = manager.create_event(
            "ORG",
            "Overlap",
            "02-01-2030 14:30",
            "02-01-2030 15:30",
            "R001",
            "10",
            "02-01-2030 10:00",
            "",
            NOW,
        )
        self.assertFalse(success)
        self.assertEqual(1, len(conflicts))

        success, message, event, conflicts = manager.create_event(
            "ORG",
            "Next",
            "02-01-2030 15:00",
            "02-01-2030 16:00",
            "R001",
            "10",
            "02-01-2030 10:00",
            "",
            NOW,
        )
        self.assertTrue(success)
        self.assertEqual("E002", event["event_id"])

    def test_organizer_cannot_create_overlapping_events_in_different_rooms(self):
        data = make_data()
        data["events"].append(
            make_event("E001", "First", "R001", "A101", 14, 16)
        )
        manager = EventManager(data)

        success, message, event, conflicts = manager.create_event(
            "ORG",
            "Second",
            "02-01-2030 15:00",
            "02-01-2030 17:00",
            "R002",
            "10",
            "02-01-2030 10:00",
            "",
            NOW,
        )

        self.assertFalse(success)
        self.assertIn("already organize", message)
        self.assertEqual(["E001"], [event["event_id"] for event in conflicts])

        success, message, event, conflicts = manager.create_event(
            "OTHER",
            "Different organizer",
            "02-01-2030 15:00",
            "02-01-2030 17:00",
            "R002",
            "10",
            "02-01-2030 10:00",
            "",
            NOW,
        )

        self.assertTrue(success)

    def test_organizer_cannot_edit_an_event_to_overlap_another_event(self):
        data = make_data()
        data["events"] = [
            make_event("E001", "First", "R001", "A101", 14, 15),
            make_event("E002", "Second", "R002", "A102", 16, 17),
        ]
        manager = EventManager(data)

        success, message, conflicts = manager.change_schedule(
            "E002",
            "ORG",
            "02-01-2030 14:30",
            "02-01-2030 15:30",
            "R003",
            NOW,
        )

        self.assertFalse(success)
        self.assertIn("already organize", message)
        self.assertEqual(["E001"], [event["event_id"] for event in conflicts])

    def test_capacity_cannot_be_smaller_than_confirmed_count(self):
        data = make_data()
        data["events"].append(
            make_event("E001", "Workshop", "R001", "A101", 14, 15, capacity=3)
        )
        data["registrations"] = [
            {"event_id": "E001", "user_id": "U1", "status": "confirmed"},
            {"event_id": "E001", "user_id": "U2", "status": "confirmed"},
        ]
        manager = EventManager(data)

        success, message, should_promote = manager.change_capacity(
            "E001", "ORG", "1", NOW
        )
        self.assertFalse(success)
        self.assertEqual(3, data["events"][0]["capacity"])


class RegistrationTests(unittest.TestCase):
    def test_personal_time_conflict_is_rejected(self):
        data = make_data()
        data["events"] = [
            make_event("E001", "One", "R001", "A101", 14, 16),
            make_event("E002", "Two", "R002", "A102", 15, 17),
        ]
        data["registrations"].append(
            {"event_id": "E001", "user_id": "U1", "status": "confirmed"}
        )
        manager = RegistrationManager(data)

        result, message, promotions = manager.register("E002", "U1", NOW)
        self.assertEqual("error", result)
        self.assertIn("conflicts", message)

    def test_first_conflicting_waiter_is_skipped_and_second_is_promoted(self):
        data = make_data()
        data["events"] = [
            make_event("E001", "Existing", "R001", "A101", 14, 16),
            make_event("E002", "Wanted", "R002", "A102", 15, 17),
        ]
        data["registrations"].append(
            {"event_id": "E001", "user_id": "U1", "status": "confirmed"}
        )
        data["waitlist"] = [
            {"sequence": 1, "event_id": "E002", "user_id": "U1", "status": "waiting"},
            {"sequence": 2, "event_id": "E002", "user_id": "U2", "status": "waiting"},
        ]
        manager = RegistrationManager(data)

        promotions = manager.promote_waitlists(NOW)

        self.assertEqual(1, len(promotions))
        self.assertEqual("U2", promotions[0]["user_id"])
        self.assertEqual("waiting", data["waitlist"][0]["status"])
        self.assertEqual("promoted", data["waitlist"][1]["status"])

    def test_global_sequence_controls_overlapping_promotions(self):
        data = make_data()
        data["events"] = [
            make_event("E002", "Later in list", "R002", "A102", 14, 16),
            make_event("E001", "Earlier wait", "R001", "A101", 14, 16),
        ]
        data["waitlist"] = [
            {"sequence": 2, "event_id": "E002", "user_id": "U1", "status": "waiting"},
            {"sequence": 1, "event_id": "E001", "user_id": "U1", "status": "waiting"},
        ]
        manager = RegistrationManager(data)

        promotions = manager.promote_waitlists(NOW)

        self.assertEqual(1, len(promotions))
        self.assertEqual("E001", promotions[0]["event_id"])
        self.assertEqual("promoted", data["waitlist"][1]["status"])
        self.assertEqual("waiting", data["waitlist"][0]["status"])

    def test_withdraw_and_rejoin_gets_a_new_sequence(self):
        data = make_data()
        data["events"].append(
            make_event("E001", "Full", "R001", "A101", 14, 15)
        )
        data["registrations"].append(
            {"event_id": "E001", "user_id": "FULL", "status": "confirmed"}
        )
        manager = RegistrationManager(data)

        success, message, first_record = manager.join_waitlist("E001", "U1", NOW)
        self.assertTrue(success)
        success, message = manager.withdraw_waitlist("E001", "U1", NOW)
        self.assertTrue(success)
        success, message, second_record = manager.join_waitlist("E001", "U1", NOW)
        self.assertTrue(success)
        self.assertGreater(second_record["sequence"], first_record["sequence"])

    def test_exact_deadline_does_not_promote(self):
        data = make_data()
        event = make_event("E001", "Deadline", "R001", "A101", 14, 15)
        data["events"].append(event)
        data["waitlist"].append(
            {"sequence": 1, "event_id": "E001", "user_id": "U1", "status": "waiting"}
        )
        manager = RegistrationManager(data)

        promotions = manager.promote_waitlists(event["deadline"])
        self.assertEqual([], promotions)
        self.assertEqual("waiting", data["waitlist"][0]["status"])

    def test_cancelling_one_event_can_promote_user_to_another_event(self):
        data = make_data()
        data["events"] = [
            make_event("E001", "Old booking", "R001", "A101", 14, 16),
            make_event("E002", "Waiting event", "R002", "A102", 15, 17),
        ]
        data["registrations"].append(
            {"event_id": "E001", "user_id": "U1", "status": "confirmed"}
        )
        data["waitlist"].append(
            {"sequence": 1, "event_id": "E002", "user_id": "U1", "status": "waiting"}
        )
        manager = RegistrationManager(data)

        success, message, promotions = manager.cancel_registration("E001", "U1", NOW)
        self.assertTrue(success)
        self.assertEqual("E002", promotions[0]["event_id"])

    def test_promotion_notification_can_remove_other_waitlists(self):
        data = make_data()
        data["events"] = [
            make_event("E001", "Promoted event", "R001", "A101", 14, 15),
            make_event("E002", "Full event", "R002", "A102", 16, 17),
        ]
        data["registrations"].append(
            {"event_id": "E002", "user_id": "FULL", "status": "confirmed"}
        )
        data["waitlist"] = [
            {"sequence": 1, "event_id": "E001", "user_id": "U1", "status": "waiting"},
            {"sequence": 2, "event_id": "E002", "user_id": "U1", "status": "waiting"},
        ]
        manager = RegistrationManager(data)

        promotions = manager.promote_waitlists(NOW)
        notifications = manager.get_promotion_notifications("U1")

        self.assertEqual("E001", promotions[0]["event_id"])
        self.assertEqual("E001", notifications[0]["event_id"])
        self.assertEqual("waiting", data["waitlist"][1]["status"])

        withdrawn = manager.withdraw_all_other_waitlists("U1", NOW)
        manager.acknowledge_promotion_notifications("U1")

        self.assertEqual(["E002"], withdrawn)
        self.assertEqual("withdrawn", data["waitlist"][1]["status"])
        self.assertEqual([], manager.get_promotion_notifications("U1"))


class RoomTests(unittest.TestCase):
    def test_room_with_future_event_cannot_be_disabled_or_deleted(self):
        data = make_data()
        data["events"].append(
            make_event("E001", "Future", "R001", "A101", 14, 15)
        )
        manager = RoomManager(data)

        success, message, events = manager.change_room_status(
            "R001", "unavailable", NOW
        )
        self.assertFalse(success)
        self.assertEqual(1, len(events))

        success, message, events, room = manager.delete_room("R001", NOW)
        self.assertFalse(success)
        self.assertEqual("available", room["status"])

    def test_deleted_room_id_is_not_reused(self):
        data = make_data()
        data["rooms"][2]["status"] = "deleted"
        manager = RoomManager(data)

        success, message, room = manager.add_room("New Room", "10")
        self.assertTrue(success)
        self.assertEqual("R004", room["room_id"])


class StorageTests(unittest.TestCase):
    def test_first_run_initializes_and_saved_data_can_be_loaded(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            storage = Storage(temporary_directory)
            data = storage.load_data(now=NOW)
            self.assertEqual(3, len(data["rooms"]))
            self.assertEqual([], data["notifications"])
            self.assertTrue(
                os.path.exists(os.path.join(temporary_directory, "notifications.txt"))
            )

            data["rooms"].append(make_room("R004", "C301", 40))
            storage.save_data(data)
            loaded_again = storage.load_data(now=NOW)
            self.assertEqual(4, len(loaded_again["rooms"]))

    def test_promotion_notification_is_saved_and_loaded(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            storage = Storage(temporary_directory)
            data = storage.load_data(now=NOW)
            data["events"].append(
                make_event("E001", "Saved promotion", "R001", "A101", 14, 15)
            )
            data["waitlist"].append(
                {
                    "sequence": 1,
                    "event_id": "E001",
                    "user_id": "U1",
                    "status": "waiting",
                }
            )
            manager = RegistrationManager(data)
            manager.promote_waitlists(NOW)

            storage.save_data(data)
            loaded_again = storage.load_data(now=NOW)

            self.assertEqual(
                [{"event_id": "E001", "user_id": "U1"}],
                loaded_again["notifications"],
            )

    def test_partial_data_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = os.path.join(temporary_directory, "classrooms.txt")
            with open(path, "w", encoding="utf-8") as file:
                file.write("R001|A101|20|available\n")

            storage = Storage(temporary_directory)
            with self.assertRaises(FileNotFoundError):
                storage.load_data(now=NOW)

    def test_old_date_format_is_loaded_and_saved_in_the_new_format(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            storage = Storage(temporary_directory)
            storage.load_data(now=NOW)

            events_path = os.path.join(temporary_directory, "events.txt")
            with open(events_path, "w", encoding="utf-8") as file:
                file.write(
                    "E001|ORG|Old event|2030-01-02 14:00|2030-01-02 15:00|"
                    + "R001|A101|10|2030-01-02 10:00|\n"
                )

            data = storage.load_data(now=NOW)
            self.assertEqual(datetime(2030, 1, 2, 14, 0), data["events"][0]["start_time"])

            storage.save_data(data)
            with open(events_path, "r", encoding="utf-8") as file:
                saved_text = file.read()

            self.assertIn("02-01-2030 14:00", saved_text)


if __name__ == "__main__":
    unittest.main()

