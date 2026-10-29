from utils import (
    event_sort_key,
    generate_id,
    get_event_status,
    parse_datetime,
    times_overlap,
    validate_text,
)


class EventManager:
    def __init__(self, data):
        self.data = data

    def find_event(self, event_id):
        for event in self.data["events"]:
            if event["event_id"] == event_id:
                return event
        return None

    def find_room(self, room_id):
        for room in self.data["rooms"]:
            if room["room_id"] == room_id and room["status"] != "deleted":
                return room
        return None

    def confirmed_count(self, event_id):
        count = 0
        for registration in self.data["registrations"]:
            if registration["event_id"] == event_id and registration["status"] == "confirmed":
                count += 1
        return count

    def effective_waiting_count(self, event, now):
        if get_event_status(event, now) != "Registration open":
            return 0

        count = 0
        for record in self.data["waitlist"]:
            if record["event_id"] == event["event_id"] and record["status"] == "waiting":
                count += 1
        return count

    def list_events(self):
        return sorted(self.data["events"], key=event_sort_key)

    def list_organizer_events(self, organizer_id):
        events = []
        for event in self.data["events"]:
            if event["organizer_id"] == organizer_id:
                events.append(event)
        return sorted(events, key=event_sort_key)

    def check_room_conflict(self, room_id, start_time, end_time, excluded_event_id=""):
        conflicts = []

        for event in self.data["events"]:
            if event["event_id"] == excluded_event_id:
                continue
            if event["room_id"] != room_id:
                continue
            if times_overlap(start_time, end_time, event["start_time"], event["end_time"]):
                conflicts.append(event)

        return sorted(conflicts, key=event_sort_key)

    def check_organizer_conflict(
        self,
        organizer_id,
        start_time,
        end_time,
        excluded_event_id="",
    ):
        conflicts = []

        for event in self.data["events"]:
            if event["event_id"] == excluded_event_id:
                continue
            if event["organizer_id"] != organizer_id:
                continue
            if times_overlap(start_time, end_time, event["start_time"], event["end_time"]):
                conflicts.append(event)

        return sorted(conflicts, key=event_sort_key)

    def create_event(
        self,
        organizer_id,
        title,
        start_text,
        end_text,
        room_id,
        capacity_text,
        deadline_text,
        description,
        now,
    ):
        valid, message, cleaned_title = validate_text(title, "Event title")
        if not valid:
            return False, message, None, []

        valid, message, cleaned_description = validate_text(
            description, "Event description", allow_empty=True
        )
        if not valid:
            return False, message, None, []

        try:
            start_time = parse_datetime(start_text)
            end_time = parse_datetime(end_text)
            deadline = parse_datetime(deadline_text)
        except ValueError:
            return False, "Date and time must use the format DD-MM-YYYY HH:MM.", None, []

        if not now < start_time < end_time:
            return False, "Times must satisfy: current time < start time < end time.", None, []

        if not now < deadline <= start_time:
            return False, "The deadline must be after the current time and no later than the event start time.", None, []

        try:
            capacity = int(capacity_text)
        except ValueError:
            return False, "Event capacity must be a positive integer.", None, []

        if capacity <= 0:
            return False, "Event capacity must be a positive integer.", None, []

        room = self.find_room(room_id)
        if room is None:
            return False, "The room does not exist or has been deleted.", None, []
        if room["status"] != "available":
            return False, "The room is currently unavailable.", None, []
        if capacity > room["capacity"]:
            return False, "Event capacity cannot exceed room capacity.", None, []

        conflicts = self.check_organizer_conflict(
            organizer_id, start_time, end_time
        )
        if len(conflicts) > 0:
            return False, "You already organize another event during this time.", None, conflicts

        conflicts = self.check_room_conflict(room_id, start_time, end_time)
        if len(conflicts) > 0:
            return False, "The room already has an event during the selected time.", None, conflicts

        event = {
            "event_id": generate_id(self.data["events"], "event_id", "E"),
            "organizer_id": organizer_id,
            "title": cleaned_title,
            "start_time": start_time,
            "end_time": end_time,
            "room_id": room["room_id"],
            "room_name": room["name"],
            "capacity": capacity,
            "deadline": deadline,
            "description": cleaned_description,
        }
        self.data["events"].append(event)
        return True, "Event created successfully.", event, []

    def check_owner_and_time(self, event_id, organizer_id, now):
        event = self.find_event(event_id)
        if event is None:
            return False, "The event does not exist.", None
        if event["organizer_id"] != organizer_id:
            return False, "You can only manage events that you created.", None
        if now >= event["start_time"]:
            return False, "The event has started and can no longer be edited.", None
        return True, "", event

    def change_title(self, event_id, organizer_id, new_title, now):
        valid, message, event = self.check_owner_and_time(event_id, organizer_id, now)
        if not valid:
            return False, message

        valid, message, cleaned_title = validate_text(new_title, "Event title")
        if not valid:
            return False, message

        event["title"] = cleaned_title
        return True, "Event title updated successfully."

    def change_description(self, event_id, organizer_id, new_description, now):
        valid, message, event = self.check_owner_and_time(event_id, organizer_id, now)
        if not valid:
            return False, message

        valid, message, cleaned_description = validate_text(
            new_description, "Event description", allow_empty=True
        )
        if not valid:
            return False, message

        event["description"] = cleaned_description
        return True, "Event description updated successfully."

    def change_schedule(
        self,
        event_id,
        organizer_id,
        new_start_text,
        new_end_text,
        new_room_id,
        now,
    ):
        valid, message, event = self.check_owner_and_time(event_id, organizer_id, now)
        if not valid:
            return False, message, []

        if get_event_status(event, now) != "Registration open":
            return False, "The time or room can only be changed while registration is open.", []

        if self.confirmed_count(event_id) > 0:
            return False, "The time or room cannot be changed because there are confirmed participants.", []

        for record in self.data["waitlist"]:
            if record["event_id"] == event_id and record["status"] == "waiting":
                return False, "The time or room cannot be changed because there are waiting records.", []

        try:
            new_start = parse_datetime(new_start_text)
            new_end = parse_datetime(new_end_text)
        except ValueError:
            return False, "Date and time must use the format DD-MM-YYYY HH:MM.", []

        if not now < new_start < new_end:
            return False, "Times must satisfy: current time < start time < end time.", []
        if not now < event["deadline"] <= new_start:
            return False, "The existing deadline must be after the current time and no later than the new start time.", []

        room = self.find_room(new_room_id)
        if room is None:
            return False, "The room does not exist or has been deleted.", []
        if room["status"] != "available":
            return False, "The room is currently unavailable.", []
        if event["capacity"] > room["capacity"]:
            return False, "The current event capacity exceeds the new room capacity.", []

        conflicts = self.check_organizer_conflict(
            organizer_id,
            new_start,
            new_end,
            excluded_event_id=event_id,
        )
        if len(conflicts) > 0:
            return False, "You already organize another event during this time.", conflicts

        conflicts = self.check_room_conflict(
            new_room_id, new_start, new_end, excluded_event_id=event_id
        )
        if len(conflicts) > 0:
            return False, "The new schedule conflicts with another event in this room.", conflicts

        event["start_time"] = new_start
        event["end_time"] = new_end
        event["room_id"] = room["room_id"]
        event["room_name"] = room["name"]
        return True, "Event time and room updated successfully.", []

    def change_capacity(self, event_id, organizer_id, new_capacity_text, now):
        valid, message, event = self.check_owner_and_time(event_id, organizer_id, now)
        if not valid:
            return False, message, False

        try:
            new_capacity = int(new_capacity_text)
        except ValueError:
            return False, "Event capacity must be a positive integer.", False

        if new_capacity <= 0:
            return False, "Event capacity must be a positive integer.", False

        room = self.find_room(event["room_id"])
        if room is None:
            return False, "The event room does not exist or has been deleted.", False
        if new_capacity > room["capacity"]:
            return False, "Event capacity cannot exceed room capacity.", False

        confirmed = self.confirmed_count(event_id)
        if new_capacity < confirmed:
            return False, "Event capacity cannot be lower than the confirmed participant count.", False

        old_capacity = event["capacity"]
        event["capacity"] = new_capacity
        increased_while_open = (
            new_capacity > old_capacity and get_event_status(event, now) == "Registration open"
        )
        return True, "Event capacity updated successfully.", increased_while_open

    def change_deadline(self, event_id, organizer_id, new_deadline_text, now):
        valid, message, event = self.check_owner_and_time(event_id, organizer_id, now)
        if not valid:
            return False, message

        if now >= event["deadline"]:
            return False, "Registration has already closed and cannot be reopened."

        try:
            new_deadline = parse_datetime(new_deadline_text)
        except ValueError:
            return False, "Date and time must use the format DD-MM-YYYY HH:MM."

        if not now < new_deadline <= event["start_time"]:
            return False, "The new deadline must be after the current time and no later than the event start time."

        event["deadline"] = new_deadline
        return True, "Registration deadline updated successfully."
