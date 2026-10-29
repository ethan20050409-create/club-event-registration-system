from utils import (
    event_sort_key,
    get_event_status,
    times_overlap,
    waiting_event_sort_key,
    waitlist_sort_key,
)


class RegistrationManager:
    def __init__(self, data):
        self.data = data
        if "notifications" not in self.data:
            self.data["notifications"] = []

    def find_event(self, event_id):
        for event in self.data["events"]:
            if event["event_id"] == event_id:
                return event
        return None

    def find_registration(self, event_id, user_id):
        for registration in self.data["registrations"]:
            same_event = registration["event_id"] == event_id
            same_user = registration["user_id"] == user_id
            if same_event and same_user:
                return registration
        return None

    def find_waiting_record(self, event_id, user_id):
        for record in self.data["waitlist"]:
            same_event = record["event_id"] == event_id
            same_user = record["user_id"] == user_id
            if same_event and same_user and record["status"] == "waiting":
                return record
        return None

    def confirmed_count(self, event_id):
        count = 0
        for registration in self.data["registrations"]:
            if registration["event_id"] == event_id and registration["status"] == "confirmed":
                count += 1
        return count

    def remaining_places(self, event):
        return event["capacity"] - self.confirmed_count(event["event_id"])

    def check_personal_conflict(self, user_id, new_event):
        for registration in self.data["registrations"]:
            if registration["user_id"] != user_id:
                continue
            if registration["status"] != "confirmed":
                continue
            if registration["event_id"] == new_event["event_id"]:
                continue

            old_event = self.find_event(registration["event_id"])
            if old_event is not None and times_overlap(
                new_event["start_time"],
                new_event["end_time"],
                old_event["start_time"],
                old_event["end_time"],
            ):
                return old_event

        return None

    def confirm_registration(self, event_id, user_id):
        registration = self.find_registration(event_id, user_id)

        if registration is None:
            registration = {
                "event_id": event_id,
                "user_id": user_id,
                "status": "confirmed",
            }
            self.data["registrations"].append(registration)
        else:
            registration["status"] = "confirmed"

    def add_promotion_notification(self, event_id, user_id):
        for notification in self.data["notifications"]:
            same_event = notification["event_id"] == event_id
            same_user = notification["user_id"] == user_id
            if same_event and same_user:
                return

        self.data["notifications"].append(
            {
                "event_id": event_id,
                "user_id": user_id,
            }
        )

    def promote_waitlists(self, now):
        promoted_results = []
        waiting_records = []

        for record in self.data["waitlist"]:
            if record["status"] == "waiting":
                waiting_records.append(record)

        waiting_records.sort(key=waitlist_sort_key)

        for record in waiting_records:
            event = self.find_event(record["event_id"])
            if event is None:
                continue
            if get_event_status(event, now) != "Registration open":
                continue
            if self.remaining_places(event) <= 0:
                continue

            conflict = self.check_personal_conflict(record["user_id"], event)
            if conflict is not None:
                continue

            registration = self.find_registration(event["event_id"], record["user_id"])
            if registration is not None and registration["status"] == "confirmed":
                continue

            self.confirm_registration(event["event_id"], record["user_id"])
            record["status"] = "promoted"
            self.add_promotion_notification(event["event_id"], record["user_id"])
            promoted_results.append(
                {
                    "user_id": record["user_id"],
                    "event_id": event["event_id"],
                    "title": event["title"],
                }
            )

        return promoted_results

    def get_promotion_notifications(self, user_id):
        events = []

        for notification in self.data["notifications"]:
            if notification["user_id"] == user_id:
                event = self.find_event(notification["event_id"])
                if event is not None:
                    events.append(event)

        events.sort(key=event_sort_key)
        return events

    def acknowledge_promotion_notifications(self, user_id):
        remaining_notifications = []

        for notification in self.data["notifications"]:
            if notification["user_id"] != user_id:
                remaining_notifications.append(notification)

        self.data["notifications"] = remaining_notifications

    def withdraw_all_other_waitlists(self, user_id, now):
        withdrawn_event_ids = []

        for record in self.data["waitlist"]:
            if record["user_id"] != user_id:
                continue
            if record["status"] != "waiting":
                continue

            event = self.find_event(record["event_id"])
            if event is None:
                continue
            if now >= event["start_time"]:
                continue

            record["status"] = "withdrawn"
            withdrawn_event_ids.append(event["event_id"])

        return withdrawn_event_ids

    def register(self, event_id, user_id, now):
        event = self.find_event(event_id)
        if event is None:
            return "error", "The event does not exist.", []
        if get_event_status(event, now) != "Registration open":
            return "error", "Registration is not open for this event.", []

        registration = self.find_registration(event_id, user_id)
        if registration is not None and registration["status"] == "confirmed":
            return "error", "You are already registered for this event.", []
        if self.find_waiting_record(event_id, user_id) is not None:
            return "error", "You are already on the waitlist for this event.", []

        promoted_results = self.promote_waitlists(now)

        if self.remaining_places(event) <= 0:
            return "full", "The event is full.", promoted_results

        conflict = self.check_personal_conflict(user_id, event)
        if conflict is not None:
            message = (
                "Registration failed because this event conflicts with your confirmed event "
                + conflict["event_id"]
                + " "
                + conflict["title"]
                + "."
            )
            return "error", message, promoted_results

        self.confirm_registration(event_id, user_id)
        return "confirmed", "Registration confirmed successfully.", promoted_results

    def join_waitlist(self, event_id, user_id, now):
        event = self.find_event(event_id)
        if event is None:
            return False, "The event does not exist.", None
        if get_event_status(event, now) != "Registration open":
            return False, "The waitlist is not open for this event.", None

        registration = self.find_registration(event_id, user_id)
        if registration is not None and registration["status"] == "confirmed":
            return False, "You are already registered for this event.", None
        if self.find_waiting_record(event_id, user_id) is not None:
            return False, "You are already on the waitlist for this event.", None
        if self.remaining_places(event) > 0:
            return False, "The event has a place available. Please register directly.", None

        largest_sequence = 0
        for record in self.data["waitlist"]:
            if record["sequence"] > largest_sequence:
                largest_sequence = record["sequence"]

        record = {
            "sequence": largest_sequence + 1,
            "event_id": event_id,
            "user_id": user_id,
            "status": "waiting",
        }
        self.data["waitlist"].append(record)

        conflict = self.check_personal_conflict(user_id, event)
        message = "You have joined the end of the waitlist."
        if conflict is not None:
            message += (
                " Warning: this event currently conflicts with your confirmed event "
                + conflict["event_id"]
                + ", so you may be skipped when a place becomes available."
            )

        return True, message, record

    def cancel_registration(self, event_id, user_id, now):
        event = self.find_event(event_id)
        if event is None:
            return False, "The event does not exist.", []
        if now >= event["start_time"]:
            return False, "The event has started, so the registration cannot be cancelled.", []

        registration = self.find_registration(event_id, user_id)
        if registration is None or registration["status"] != "confirmed":
            return False, "You do not have a confirmed registration for this event.", []

        registration["status"] = "cancelled"
        promoted_results = self.promote_waitlists(now)
        return True, "The confirmed registration has been cancelled.", promoted_results

    def withdraw_waitlist(self, event_id, user_id, now):
        event = self.find_event(event_id)
        if event is None:
            return False, "The event does not exist."
        if now >= event["start_time"]:
            return False, "The event has started, so you cannot leave the waitlist."

        record = self.find_waiting_record(event_id, user_id)
        if record is None:
            return False, "You do not have a current waitlist record for this event."

        record["status"] = "withdrawn"
        return True, "You have left the waitlist."

    def waitlist_position(self, event_id, user_id, now):
        event = self.find_event(event_id)
        if event is None or get_event_status(event, now) != "Registration open":
            return None

        records = []
        for record in self.data["waitlist"]:
            if record["event_id"] == event_id and record["status"] == "waiting":
                records.append(record)
        records.sort(key=waitlist_sort_key)

        position = 1
        for record in records:
            if record["user_id"] == user_id:
                return position
            position += 1

        return None

    def get_my_bookings(self, user_id):
        confirmed_events = []
        waiting_events = []

        for registration in self.data["registrations"]:
            if registration["user_id"] == user_id and registration["status"] == "confirmed":
                event = self.find_event(registration["event_id"])
                if event is not None:
                    confirmed_events.append(event)

        for record in self.data["waitlist"]:
            if record["user_id"] == user_id and record["status"] == "waiting":
                event = self.find_event(record["event_id"])
                if event is not None:
                    waiting_events.append((event, record))

        confirmed_events.sort(key=event_sort_key)
        waiting_events.sort(key=waiting_event_sort_key)
        return confirmed_events, waiting_events

    def get_roster(self, event_id, organizer_id, now):
        event = self.find_event(event_id)
        if event is None:
            return False, "The event does not exist.", None
        if event["organizer_id"] != organizer_id:
            return False, "You can only view the full roster for events that you created.", None

        confirmed_users = []
        current_waiting = []
        expired_waiting = []

        for registration in self.data["registrations"]:
            if registration["event_id"] == event_id and registration["status"] == "confirmed":
                confirmed_users.append(registration["user_id"])

        waiting_records = []
        for record in self.data["waitlist"]:
            if record["event_id"] == event_id and record["status"] == "waiting":
                waiting_records.append(record)
        waiting_records.sort(key=waitlist_sort_key)

        if get_event_status(event, now) == "Registration open":
            position = 1
            for record in waiting_records:
                current_waiting.append((record["user_id"], position))
                position += 1
        else:
            for record in waiting_records:
                expired_waiting.append(record["user_id"])

        roster = {
            "event": event,
            "confirmed_users": sorted(confirmed_users),
            "current_waiting": current_waiting,
            "expired_waiting": expired_waiting,
            "remaining": self.remaining_places(event),
        }
        return True, "", roster
