import os
from datetime import datetime

from utils import format_datetime, parse_stored_datetime, times_overlap


class Storage:
    def __init__(self, data_directory=None):
        if data_directory is None:
            project_directory = os.path.dirname(os.path.abspath(__file__))
            data_directory = os.path.join(project_directory, "data")

        self.data_directory = data_directory
        self.file_paths = {
            "rooms": os.path.join(data_directory, "classrooms.txt"),
            "events": os.path.join(data_directory, "events.txt"),
            "registrations": os.path.join(data_directory, "registrations.txt"),
            "waitlist": os.path.join(data_directory, "waitlist.txt"),
            "notifications": os.path.join(data_directory, "notifications.txt"),
        }
        self.core_file_keys = ["rooms", "events", "registrations", "waitlist"]

    def initialize_data(self):
        core_existing_count = 0

        for file_key in self.core_file_keys:
            if os.path.exists(self.file_paths[file_key]):
                core_existing_count += 1

        notifications_exist = os.path.exists(self.file_paths["notifications"])

        if core_existing_count == 0 and not notifications_exist:
            os.makedirs(self.data_directory, exist_ok=True)

            with open(self.file_paths["rooms"], "w", encoding="utf-8") as file:
                file.write("R001|A101|20|available\n")
                file.write("R002|A102|30|available\n")
                file.write("R003|B201|50|available\n")

            with open(self.file_paths["events"], "w", encoding="utf-8"):
                pass
            with open(self.file_paths["registrations"], "w", encoding="utf-8"):
                pass
            with open(self.file_paths["waitlist"], "w", encoding="utf-8"):
                pass
            with open(self.file_paths["notifications"], "w", encoding="utf-8"):
                pass

            return True

        if core_existing_count != len(self.core_file_keys):
            missing_files = []
            for file_key in self.core_file_keys:
                path = self.file_paths[file_key]
                if not os.path.exists(path):
                    missing_files.append(os.path.basename(path))

            raise FileNotFoundError(
                "The data files are incomplete. Missing: " + ", ".join(missing_files)
            )

        if not notifications_exist:
            with open(self.file_paths["notifications"], "w", encoding="utf-8"):
                pass

        return False

    def read_lines(self, file_key):
        records = []
        path = self.file_paths[file_key]

        with open(path, "r", encoding="utf-8") as file:
            line_number = 0
            for raw_line in file:
                line_number += 1
                line = raw_line.rstrip("\r\n")
                if line.strip() != "":
                    records.append((line_number, line))

        return records

    def load_rooms(self):
        rooms = []

        for line_number, line in self.read_lines("rooms"):
            fields = line.split("|")
            if len(fields) != 4:
                raise ValueError(
                    "classrooms.txt line " + str(line_number) + " must contain 4 fields."
                )

            try:
                capacity = int(fields[2])
            except ValueError:
                raise ValueError(
                    "The capacity on classrooms.txt line " + str(line_number) + " is not an integer."
                )

            rooms.append(
                {
                    "room_id": fields[0],
                    "name": fields[1],
                    "capacity": capacity,
                    "status": fields[3],
                    "source_line": line_number,
                }
            )

        return rooms

    def load_events(self):
        events = []

        for line_number, line in self.read_lines("events"):
            fields = line.split("|")
            if len(fields) != 10:
                raise ValueError(
                    "events.txt line " + str(line_number) + " must contain 10 fields."
                )

            try:
                start_time = parse_stored_datetime(fields[3])
                end_time = parse_stored_datetime(fields[4])
                capacity = int(fields[7])
                deadline = parse_stored_datetime(fields[8])
            except ValueError:
                raise ValueError(
                    "events.txt line "
                    + str(line_number)
                    + " contains an invalid number or date and time."
                )

            events.append(
                {
                    "event_id": fields[0],
                    "organizer_id": fields[1],
                    "title": fields[2],
                    "start_time": start_time,
                    "end_time": end_time,
                    "room_id": fields[5],
                    "room_name": fields[6],
                    "capacity": capacity,
                    "deadline": deadline,
                    "description": fields[9],
                    "source_line": line_number,
                }
            )

        return events

    def load_registrations(self):
        registrations = []

        for line_number, line in self.read_lines("registrations"):
            fields = line.split("|")
            if len(fields) != 3:
                raise ValueError(
                    "registrations.txt line "
                    + str(line_number)
                    + " must contain 3 fields."
                )

            registrations.append(
                {
                    "event_id": fields[0],
                    "user_id": fields[1],
                    "status": fields[2],
                    "source_line": line_number,
                }
            )

        return registrations

    def load_waitlist(self):
        waitlist = []

        for line_number, line in self.read_lines("waitlist"):
            fields = line.split("|")
            if len(fields) != 4:
                raise ValueError(
                    "waitlist.txt line " + str(line_number) + " must contain 4 fields."
                )

            try:
                sequence = int(fields[0])
            except ValueError:
                raise ValueError(
                    "The sequence on waitlist.txt line " + str(line_number) + " is not an integer."
                )

            waitlist.append(
                {
                    "sequence": sequence,
                    "event_id": fields[1],
                    "user_id": fields[2],
                    "status": fields[3],
                    "source_line": line_number,
                }
            )

        return waitlist

    def load_notifications(self):
        notifications = []

        for line_number, line in self.read_lines("notifications"):
            fields = line.split("|")
            if len(fields) != 2:
                raise ValueError(
                    "notifications.txt line "
                    + str(line_number)
                    + " must contain 2 fields."
                )

            notifications.append(
                {
                    "event_id": fields[0],
                    "user_id": fields[1],
                    "source_line": line_number,
                }
            )

        return notifications

    def load_data(self, now=None):
        self.initialize_data()

        data = {
            "rooms": self.load_rooms(),
            "events": self.load_events(),
            "registrations": self.load_registrations(),
            "waitlist": self.load_waitlist(),
            "notifications": self.load_notifications(),
        }

        if now is None:
            now = datetime.now()

        self.validate_data(data, now)

        for record_list in data.values():
            for record in record_list:
                if "source_line" in record:
                    del record["source_line"]

        return data

    def validate_data(self, data, now):
        room_ids = set()
        active_room_names = set()

        for room in data["rooms"]:
            line = str(room["source_line"])
            room_id = room["room_id"]

            if room_id in room_ids:
                raise ValueError("classrooms.txt contains a duplicate room ID: " + room_id)
            room_ids.add(room_id)

            if room["name"].strip() == "":
                raise ValueError("The room name on classrooms.txt line " + line + " is empty.")
            if room["capacity"] <= 0:
                raise ValueError("The capacity on classrooms.txt line " + line + " must be positive.")
            if room["status"] not in ["available", "unavailable", "deleted"]:
                raise ValueError("The status on classrooms.txt line " + line + " is invalid.")

            lowered_name = room["name"].lower()
            if room["status"] != "deleted" and lowered_name in active_room_names:
                raise ValueError("classrooms.txt contains a duplicate active room name: " + room["name"])
            if room["status"] != "deleted":
                active_room_names.add(lowered_name)

        event_ids = set()
        event_lookup = {}
        room_lookup = {}
        for room in data["rooms"]:
            room_lookup[room["room_id"]] = room

        for event in data["events"]:
            line = str(event["source_line"])
            event_id = event["event_id"]

            if event_id in event_ids:
                raise ValueError("events.txt contains a duplicate event ID: " + event_id)
            event_ids.add(event_id)
            event_lookup[event_id] = event

            if event["organizer_id"].strip() == "" or event["title"].strip() == "":
                raise ValueError("The organizer ID or title on events.txt line " + line + " is empty.")
            if event["room_id"] not in room_lookup:
                raise ValueError("events.txt line " + line + " refers to a room that does not exist.")
            if event["capacity"] <= 0:
                raise ValueError("The capacity on events.txt line " + line + " must be positive.")
            if not event["start_time"] < event["end_time"]:
                raise ValueError("The start time on events.txt line " + line + " must be before the end time.")
            if event["deadline"] > event["start_time"]:
                raise ValueError("The deadline on events.txt line " + line + " is after the start time.")

            room = room_lookup[event["room_id"]]
            if event["capacity"] > room["capacity"]:
                raise ValueError("The capacity on events.txt line " + line + " exceeds room capacity.")
            if event["end_time"] > now and room["status"] != "available":
                raise ValueError(
                    "The unfinished event on events.txt line "
                    + line
                    + " uses an unavailable or deleted room."
                )

        first_index = 0
        while first_index < len(data["events"]):
            first_event = data["events"][first_index]
            second_index = first_index + 1

            while second_index < len(data["events"]):
                second_event = data["events"][second_index]

                same_room = first_event["room_id"] == second_event["room_id"]
                same_organizer = (
                    first_event["organizer_id"] == second_event["organizer_id"]
                )
                overlap = times_overlap(
                    first_event["start_time"],
                    first_event["end_time"],
                    second_event["start_time"],
                    second_event["end_time"],
                )

                if same_room and overlap:
                    raise ValueError(
                        "Events "
                        + first_event["event_id"]
                        + " and "
                        + second_event["event_id"]
                        + " overlap in the same room."
                    )

                if same_organizer and overlap:
                    raise ValueError(
                        "Events "
                        + first_event["event_id"]
                        + " and "
                        + second_event["event_id"]
                        + " overlap for the same organizer."
                    )

                second_index += 1
            first_index += 1

        registration_keys = set()
        confirmed_by_event = {}
        confirmed_by_user = {}

        for registration in data["registrations"]:
            line = str(registration["source_line"])
            event_id = registration["event_id"]
            user_id = registration["user_id"]
            key = (event_id, user_id)

            if event_id not in event_lookup:
                raise ValueError("registrations.txt line " + line + " refers to an event that does not exist.")
            if user_id.strip() == "":
                raise ValueError("The user ID on registrations.txt line " + line + " is empty.")
            if registration["status"] not in ["confirmed", "cancelled"]:
                raise ValueError("The status on registrations.txt line " + line + " is invalid.")
            if key in registration_keys:
                raise ValueError("registrations.txt contains a duplicate event and user record: " + str(key))
            registration_keys.add(key)

            if registration["status"] == "confirmed":
                if event_id not in confirmed_by_event:
                    confirmed_by_event[event_id] = []
                confirmed_by_event[event_id].append(registration)

                if user_id not in confirmed_by_user:
                    confirmed_by_user[user_id] = []
                confirmed_by_user[user_id].append(registration)

        for event_id, registrations in confirmed_by_event.items():
            if len(registrations) > event_lookup[event_id]["capacity"]:
                raise ValueError("Event " + event_id + " has more confirmed participants than its capacity.")

        for user_id, registrations in confirmed_by_user.items():
            first_index = 0
            while first_index < len(registrations):
                first_event = event_lookup[registrations[first_index]["event_id"]]
                second_index = first_index + 1

                while second_index < len(registrations):
                    second_event = event_lookup[registrations[second_index]["event_id"]]
                    if times_overlap(
                        first_event["start_time"],
                        first_event["end_time"],
                        second_event["start_time"],
                        second_event["end_time"],
                    ):
                        raise ValueError(
                            "User "
                            + user_id
                            + " has overlapping confirmed events "
                            + first_event["event_id"]
                            + " and "
                            + second_event["event_id"]
                            + "."
                        )
                    second_index += 1
                first_index += 1

        sequences = set()
        waiting_keys = set()

        for record in data["waitlist"]:
            line = str(record["source_line"])
            key = (record["event_id"], record["user_id"])

            if record["sequence"] <= 0:
                raise ValueError("The sequence on waitlist.txt line " + line + " must be positive.")
            if record["sequence"] in sequences:
                raise ValueError("waitlist.txt contains a duplicate sequence: " + str(record["sequence"]))
            sequences.add(record["sequence"])

            if record["event_id"] not in event_lookup:
                raise ValueError("waitlist.txt line " + line + " refers to an event that does not exist.")
            if record["user_id"].strip() == "":
                raise ValueError("The user ID on waitlist.txt line " + line + " is empty.")
            if record["status"] not in ["waiting", "withdrawn", "promoted"]:
                raise ValueError("The status on waitlist.txt line " + line + " is invalid.")

            if record["status"] == "waiting":
                if key in waiting_keys:
                    raise ValueError("waitlist.txt contains a duplicate waiting record: " + str(key))
                waiting_keys.add(key)

                registration = None
                for current in data["registrations"]:
                    if current["event_id"] == key[0] and current["user_id"] == key[1]:
                        registration = current
                        break

                if registration is not None and registration["status"] == "confirmed":
                    raise ValueError(
                        "User "
                        + key[1]
                        + " cannot be confirmed and waiting for event "
                        + key[0]
                        + " at the same time."
                    )

        notification_keys = set()

        for notification in data["notifications"]:
            line = str(notification["source_line"])
            event_id = notification["event_id"]
            user_id = notification["user_id"]
            key = (event_id, user_id)

            if event_id not in event_lookup:
                raise ValueError(
                    "notifications.txt line "
                    + line
                    + " refers to an event that does not exist."
                )
            if user_id.strip() == "":
                raise ValueError(
                    "The user ID on notifications.txt line " + line + " is empty."
                )
            if key in notification_keys:
                raise ValueError(
                    "notifications.txt contains a duplicate event and user record: "
                    + str(key)
                )
            notification_keys.add(key)

            promoted_record_exists = False
            for record in data["waitlist"]:
                if (
                    record["event_id"] == event_id
                    and record["user_id"] == user_id
                    and record["status"] == "promoted"
                ):
                    promoted_record_exists = True
                    break

            if not promoted_record_exists:
                raise ValueError(
                    "Notification "
                    + str(key)
                    + " does not have a matching promoted waitlist record."
                )

    def save_data(self, data):
        with open(self.file_paths["rooms"], "w", encoding="utf-8") as file:
            for room in data["rooms"]:
                line = (
                    room["room_id"]
                    + "|"
                    + room["name"]
                    + "|"
                    + str(room["capacity"])
                    + "|"
                    + room["status"]
                    + "\n"
                )
                file.write(line)

        with open(self.file_paths["events"], "w", encoding="utf-8") as file:
            for event in data["events"]:
                fields = [
                    event["event_id"],
                    event["organizer_id"],
                    event["title"],
                    format_datetime(event["start_time"]),
                    format_datetime(event["end_time"]),
                    event["room_id"],
                    event["room_name"],
                    str(event["capacity"]),
                    format_datetime(event["deadline"]),
                    event["description"],
                ]
                file.write("|".join(fields) + "\n")

        with open(self.file_paths["registrations"], "w", encoding="utf-8") as file:
            for registration in data["registrations"]:
                fields = [
                    registration["event_id"],
                    registration["user_id"],
                    registration["status"],
                ]
                file.write("|".join(fields) + "\n")

        with open(self.file_paths["waitlist"], "w", encoding="utf-8") as file:
            for record in data["waitlist"]:
                fields = [
                    str(record["sequence"]),
                    record["event_id"],
                    record["user_id"],
                    record["status"],
                ]
                file.write("|".join(fields) + "\n")

        with open(self.file_paths["notifications"], "w", encoding="utf-8") as file:
            for notification in data["notifications"]:
                fields = [
                    notification["event_id"],
                    notification["user_id"],
                ]
                file.write("|".join(fields) + "\n")
