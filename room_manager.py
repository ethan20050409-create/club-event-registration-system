from utils import event_sort_key, generate_id, room_sort_key, validate_text


class RoomManager:
    def __init__(self, data):
        self.data = data

    def find_room(self, room_id):
        for room in self.data["rooms"]:
            if room["room_id"] == room_id and room["status"] != "deleted":
                return room
        return None

    def list_rooms(self):
        rooms = []
        for room in self.data["rooms"]:
            if room["status"] != "deleted":
                rooms.append(room)
        return sorted(rooms, key=room_sort_key)

    def get_unfinished_events(self, room_id, now):
        events = []
        for event in self.data["events"]:
            if event["room_id"] == room_id and event["end_time"] > now:
                events.append(event)
        return sorted(events, key=event_sort_key)

    def add_room(self, name, capacity_text):
        valid, message, cleaned_name = validate_text(name, "Room name")
        if not valid:
            return False, message, None

        try:
            capacity = int(capacity_text)
        except ValueError:
            return False, "Room capacity must be a positive integer.", None

        if capacity <= 0:
            return False, "Room capacity must be a positive integer.", None

        for room in self.data["rooms"]:
            same_name = room["name"].lower() == cleaned_name.lower()
            if room["status"] != "deleted" and same_name:
                return False, "An active room already has this name.", None

        room = {
            "room_id": generate_id(self.data["rooms"], "room_id", "R"),
            "name": cleaned_name,
            "capacity": capacity,
            "status": "available",
        }
        self.data["rooms"].append(room)
        return True, "Room added successfully.", room

    def change_room_status(self, room_id, new_status, now):
        room = self.find_room(room_id)
        if room is None:
            return False, "The room does not exist or has been deleted.", []

        if new_status not in ["available", "unavailable"]:
            return False, "The status must be available or unavailable.", []

        if room["status"] == new_status:
            return True, "The status was not changed.", []

        unfinished_events = self.get_unfinished_events(room_id, now)
        if new_status == "unavailable" and len(unfinished_events) > 0:
            return False, "The room has unfinished events and cannot be made unavailable.", unfinished_events

        room["status"] = new_status
        return True, "Room status updated successfully.", []

    def delete_room(self, room_id, now):
        room = self.find_room(room_id)
        if room is None:
            return False, "The room does not exist or has been deleted.", [], None

        unfinished_events = self.get_unfinished_events(room_id, now)
        if len(unfinished_events) > 0:
            return False, "The room has unfinished events and cannot be deleted.", unfinished_events, room

        room["status"] = "deleted"
        return True, "The room has been permanently deleted.", [], room

