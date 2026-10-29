# Run this file with: python3 main.py

from datetime import datetime

from event_manager import EventManager
from registration_manager import RegistrationManager
from room_manager import RoomManager
from storage import Storage
from utils import (
    format_datetime,
    get_event_status,
    parse_datetime,
    parse_positive_integer,
    validate_text,
)


def print_box(title, lines):
    text_lines = []
    longest_length = len(title)

    for line in lines:
        text = str(line)
        text_lines.append(text)
        if len(text) > longest_length:
            longest_length = len(text)

    inside_width = longest_length + 2
    border = "+" + "-" * inside_width + "+"

    print()
    print(border)
    print("| " + title.ljust(longest_length) + " |")
    print(border)
    for text in text_lines:
        print("| " + text.ljust(longest_length) + " |")
    print(border)


def show_message(message_type, message):
    label = "[" + message_type + "]"
    print_box("MESSAGE", [label + " " + message])


def show_result(success, message):
    if success:
        show_message("SUCCESS", message)
    else:
        show_message("ERROR", message)


def event_line(event):
    return (
        event["event_id"]
        + " | "
        + event["title"]
        + " | "
        + event["room_name"]
        + " | "
        + format_datetime(event["start_time"])
        + " to "
        + format_datetime(event["end_time"])
    )


def save_or_exit(storage, data):
    try:
        storage.save_data(data)
    except OSError as error:
        show_message(
            "ERROR",
            "Failed to save data: "
            + str(error)
            + " The program will stop to avoid working with unsaved data.",
        )
        raise SystemExit(1)


def show_promotions(promoted_results):
    lines = []
    for result in promoted_results:
        lines.append(
            "[SUCCESS] Waitlist promotion: user "
            + result["user_id"]
            + " has been promoted to a confirmed place in event "
            + result["event_id"]
            + " ("
            + result["title"]
            + ")."
        )

    if len(lines) > 0:
        print_box("WAITLIST UPDATE", lines)


def run_promotions(registration_manager, storage, data):
    now = datetime.now()
    promoted_results = registration_manager.promote_waitlists(now)
    if len(promoted_results) > 0:
        save_or_exit(storage, data)
    return promoted_results


def handle_promotion_notifications(user_id, registration_manager, storage, data):
    promoted_events = registration_manager.get_promotion_notifications(user_id)
    if len(promoted_events) == 0:
        return

    lines = ["[SUCCESS] You have received a confirmed place from a waitlist:", ""]
    for event in promoted_events:
        lines.append(event_line(event))

    lines.append("")
    lines.append("Would you like to leave all your other waitlists?")
    print_box("NEW WAITLIST PROMOTION", lines)

    while True:
        answer = input("Leave all other waitlists? (y/n): ").strip().lower()
        if answer == "y" or answer == "n":
            break
        show_message("ERROR", "Please enter y or n.")

    withdrawn_event_ids = []
    if answer == "y":
        withdrawn_event_ids = registration_manager.withdraw_all_other_waitlists(
            user_id, datetime.now()
        )

    registration_manager.acknowledge_promotion_notifications(user_id)
    save_or_exit(storage, data)

    if answer == "y" and len(withdrawn_event_ids) > 0:
        show_message(
            "SUCCESS",
            "You left "
            + str(len(withdrawn_event_ids))
            + " other waitlist(s): "
            + ", ".join(withdrawn_event_ids)
            + ".",
        )
    elif answer == "y":
        show_message("INFO", "You had no other active waitlists to leave.")
    else:
        show_message("INFO", "Your other waitlists were kept.")


def print_event_summary(event, event_manager, registration_manager, now):
    confirmed = event_manager.confirmed_count(event["event_id"])
    remaining = event["capacity"] - confirmed
    waiting = event_manager.effective_waiting_count(event, now)

    lines = [
        "Organizer: " + event["organizer_id"],
        "Room: " + event["room_name"],
        "Time: "
        + format_datetime(event["start_time"])
        + " to "
        + format_datetime(event["end_time"]),
        "Confirmed: "
        + str(confirmed)
        + "/"
        + str(event["capacity"])
        + " | Places remaining: "
        + str(remaining)
        + " | Active waitlist: "
        + str(waiting),
        "Registration deadline: " + format_datetime(event["deadline"]),
        "Status: " + get_event_status(event, now),
    ]
    print_box("EVENT " + event["event_id"] + " - " + event["title"], lines)


def print_event_details(event, event_manager, registration_manager, now):
    confirmed = event_manager.confirmed_count(event["event_id"])
    remaining = event["capacity"] - confirmed
    waiting = event_manager.effective_waiting_count(event, now)

    if event["description"] == "":
        description = "None"
    else:
        description = event["description"]

    lines = [
        "Organizer: " + event["organizer_id"],
        "Room: " + event["room_name"],
        "Time: "
        + format_datetime(event["start_time"])
        + " to "
        + format_datetime(event["end_time"]),
        "Confirmed: "
        + str(confirmed)
        + "/"
        + str(event["capacity"])
        + " | Places remaining: "
        + str(remaining)
        + " | Active waitlist: "
        + str(waiting),
        "Registration deadline: " + format_datetime(event["deadline"]),
        "Status: " + get_event_status(event, now),
        "Description: " + description,
    ]
    print_box("EVENT DETAILS - " + event["event_id"] + " " + event["title"], lines)


def print_conflicting_events(events, title="CONFLICTING EVENTS"):
    lines = []
    for event in events:
        lines.append(event_line(event))
    print_box(title, lines)


def browse_events(event_manager, registration_manager):
    while True:
        now = datetime.now()
        all_events = event_manager.list_events()
        events = []

        for event in all_events:
            if get_event_status(event, now) != "Ended":
                events.append(event)

        if len(events) == 0:
            show_message("INFO", "There are no current or upcoming events.")
            return

        print_box("ALL EVENTS", ["Choose an event ID below to view more details."])
        for event in events:
            print_event_summary(event, event_manager, registration_manager, now)

        event_id = input("\nEnter an event ID to view details, or press Enter to return: ").strip()
        if event_id == "":
            return

        event = event_manager.find_event(event_id)
        if event is None:
            show_message("ERROR", "The event ID does not exist. Please try again.")
        elif get_event_status(event, now) == "Ended":
            show_message("INFO", "This event has ended and is no longer displayed.")
        else:
            print_event_details(event, event_manager, registration_manager, now)


def apply_for_event(user_id, registration_manager, storage, data):
    while True:
        event_id = input(
            "Enter the event ID, or press Enter to return: "
        ).strip()

        if event_id == "":
            show_message("INFO", "Registration cancelled.")
            return

        event = registration_manager.find_event(event_id)
        if event is None:
            show_message("ERROR", "The event ID does not exist. Please try again.")
        else:
            break

    now = datetime.now()
    result, message, promoted_results = registration_manager.register(event_id, user_id, now)
    data_changed = len(promoted_results) > 0

    if result == "full":
        show_message("WARNING", message)
        answer = input("Would you like to join the waitlist? (y/n): ").strip().lower()

        if answer == "y":
            success, wait_message, record = registration_manager.join_waitlist(
                event_id, user_id, now
            )
            if success:
                data_changed = True

            if data_changed:
                save_or_exit(storage, data)
            show_promotions(promoted_results)
            show_result(success, wait_message)
        else:
            if data_changed:
                save_or_exit(storage, data)
            show_promotions(promoted_results)
            show_message("INFO", "You did not join the waitlist.")
        return

    if result == "confirmed":
        data_changed = True

    if data_changed:
        save_or_exit(storage, data)

    show_promotions(promoted_results)
    show_result(result == "confirmed", message)


def show_my_bookings(user_id, registration_manager):
    now = datetime.now()
    confirmed_events, waiting_events = registration_manager.get_my_bookings(user_id)

    confirmed_lines = []
    if len(confirmed_events) == 0:
        confirmed_lines.append("You have no confirmed registrations.")
    else:
        for event in confirmed_events:
            confirmed_lines.append(
                event["event_id"]
                + " | "
                + event["title"]
                + " | "
                + format_datetime(event["start_time"])
                + " | "
                + get_event_status(event, now)
            )
    print_box("MY CONFIRMED REGISTRATIONS", confirmed_lines)

    waiting_lines = []
    if len(waiting_events) == 0:
        waiting_lines.append("You have no current waitlist records.")
    else:
        for event, record in waiting_events:
            position = registration_manager.waitlist_position(
                event["event_id"], user_id, now
            )
            if position is None:
                wait_status = "Waitlist ended"
            else:
                wait_status = "Waitlist position " + str(position)

            waiting_lines.append(
                event["event_id"]
                + " | "
                + event["title"]
                + " | "
                + wait_status
            )
    print_box("MY WAITLISTS", waiting_lines)


def modify_my_bookings(user_id, registration_manager, storage, data):
    while True:
        show_my_bookings(user_id, registration_manager)
        print_box(
            "CHANGE MY BOOKINGS",
            [
                "1. Cancel a confirmed registration",
                "2. Leave a waitlist",
                "3. Return",
            ],
        )
        choice = input("Choose an option: ").strip()

        if choice == "1":
            event_id = input("Enter the event ID to cancel: ").strip()
            now = datetime.now()
            success, message, promoted_results = registration_manager.cancel_registration(
                event_id, user_id, now
            )
            if success:
                save_or_exit(storage, data)
                show_result(True, message)
                show_promotions(promoted_results)
            else:
                show_result(False, message)
        elif choice == "2":
            event_id = input("Enter the event ID whose waitlist you want to leave: ").strip()
            now = datetime.now()
            success, message = registration_manager.withdraw_waitlist(
                event_id, user_id, now
            )
            if success:
                save_or_exit(storage, data)
            show_result(success, message)
        elif choice == "3":
            return
        else:
            show_message("ERROR", "Invalid option. Please try again.")


def participant_menu(
    user_id,
    event_manager,
    registration_manager,
    storage,
    data,
):
    while True:
        run_promotions(registration_manager, storage, data)
        handle_promotion_notifications(
            user_id, registration_manager, storage, data
        )
        print_box(
            "PARTICIPANT MENU - USER " + user_id,
            [
                "1. Browse events",
                "2. Register for an event",
                "3. View and change my registrations and waitlists",
                "4. Return to the user menu",
            ],
        )
        choice = input("Choose an option: ").strip()

        if choice == "1":
            browse_events(event_manager, registration_manager)
        elif choice == "2":
            apply_for_event(user_id, registration_manager, storage, data)
        elif choice == "3":
            modify_my_bookings(user_id, registration_manager, storage, data)
        elif choice == "4":
            return
        else:
            show_message("ERROR", "Invalid option. Please try again.")


def show_rooms(room_manager, now):
    rooms = room_manager.list_rooms()

    if len(rooms) == 0:
        show_message("INFO", "There are no active rooms.")
        return

    lines = []
    for room in rooms:
        lines.append(
            room["room_id"]
            + " | "
            + room["name"]
            + " | Capacity: "
            + str(room["capacity"])
            + " | Status: "
            + room["status"]
        )
        events = room_manager.get_unfinished_events(room["room_id"], now)
        if len(events) == 0:
            lines.append("  Unfinished events: None")
        else:
            lines.append("  Unfinished events:")
            for event in events:
                lines.append("  " + event_line(event))
        lines.append("")

    print_box("ROOMS AND UNFINISHED EVENTS", lines)


def create_event(organizer_id, event_manager, room_manager, storage, data):
    now = datetime.now()
    show_rooms(room_manager, now)
    show_message("INFO", "Date and time format: DD-MM-YYYY HH:MM")
    show_message("INFO", "Enter drop at any time to cancel event creation.")

    while True:
        title = input("Event title: ")
        if title.strip().lower() == "drop":
            show_message("INFO", "Event creation cancelled.")
            return

        valid, message, title = validate_text(title, "Event title")
        if valid:
            break
        show_message("ERROR", message)

    while True:
        while True:
            start_text = input("Start time: ").strip()
            if start_text.lower() == "drop":
                show_message("INFO", "Event creation cancelled.")
                return

            try:
                start_time = parse_datetime(start_text)
                if start_time <= now:
                    show_message("ERROR", "Start time must be after the current time.")
                else:
                    break
            except ValueError:
                show_message("ERROR", "Please use the format DD-MM-YYYY HH:MM.")

        while True:
            end_text = input("End time: ").strip()
            if end_text.lower() == "drop":
                show_message("INFO", "Event creation cancelled.")
                return

            try:
                end_time = parse_datetime(end_text)
                if end_time <= start_time:
                    show_message("ERROR", "End time must be after the start time.")
                else:
                    break
            except ValueError:
                show_message("ERROR", "Please use the format DD-MM-YYYY HH:MM.")

        conflicts = event_manager.check_organizer_conflict(
            organizer_id, start_time, end_time
        )
        if len(conflicts) == 0:
            break

        show_message(
            "ERROR",
            "You already organize another event during this time. "
            + "Please enter the start and end times again.",
        )
        print_conflicting_events(conflicts, "YOUR CONFLICTING EVENTS")

    while True:
        room_id = input("Room ID: ").strip()
        if room_id.lower() == "drop":
            show_message("INFO", "Event creation cancelled.")
            return

        room = event_manager.find_room(room_id)
        if room is None:
            show_message("ERROR", "The room does not exist or has been deleted.")
        elif room["status"] != "available":
            show_message("ERROR", "The room is currently unavailable.")
        else:
            conflicts = event_manager.check_room_conflict(
                room_id, start_time, end_time
            )
            if len(conflicts) > 0:
                show_message(
                    "ERROR", "The room already has an event during the selected time."
                )
                print_conflicting_events(conflicts)
            else:
                break

    while True:
        capacity_text = input("Event capacity: ").strip()
        if capacity_text.lower() == "drop":
            show_message("INFO", "Event creation cancelled.")
            return

        valid, message, capacity = parse_positive_integer(
            capacity_text, "Event capacity"
        )
        if not valid:
            show_message("ERROR", message)
        elif capacity > room["capacity"]:
            show_message("ERROR", "Event capacity cannot exceed room capacity.")
        else:
            break

    while True:
        deadline_text = input("Registration deadline: ").strip()
        if deadline_text.lower() == "drop":
            show_message("INFO", "Event creation cancelled.")
            return

        try:
            deadline = parse_datetime(deadline_text)
            if deadline <= now:
                show_message(
                    "ERROR", "Registration deadline must be after the current time."
                )
            elif deadline > start_time:
                show_message(
                    "ERROR", "Registration deadline cannot be after the start time."
                )
            else:
                break
        except ValueError:
            show_message("ERROR", "Please use the format DD-MM-YYYY HH:MM.")

    while True:
        description = input("Event description (optional): ")
        if description.strip().lower() == "drop":
            show_message("INFO", "Event creation cancelled.")
            return

        valid, message, description = validate_text(
            description, "Event description", allow_empty=True
        )
        if valid:
            break
        show_message("ERROR", message)

    success, message, event, conflicts = event_manager.create_event(
        organizer_id,
        title,
        start_text,
        end_text,
        room_id,
        capacity_text,
        deadline_text,
        description,
        now,
    )

    if success:
        save_or_exit(storage, data)
        show_result(True, message + " Event ID: " + event["event_id"])
    else:
        show_result(False, message)
        if len(conflicts) > 0:
            print_conflicting_events(conflicts)


def list_my_events(organizer_id, event_manager, registration_manager):
    events = event_manager.list_organizer_events(organizer_id)
    now = datetime.now()

    if len(events) == 0:
        show_message("INFO", "You have not created any events.")
    else:
        print_box("EVENTS I CREATED", ["Select an event ID from the events below."])
        for event in events:
            print_event_summary(event, event_manager, registration_manager, now)
    return events


def edit_my_event(
    organizer_id,
    event_manager,
    registration_manager,
    storage,
    data,
):
    events = list_my_events(organizer_id, event_manager, registration_manager)
    if len(events) == 0:
        return

    event_id = input("Enter the event ID to edit: ").strip()
    event = event_manager.find_event(event_id)
    if event is None or event["organizer_id"] != organizer_id:
        show_message("ERROR", "The event does not exist, or you are not its organizer.")
        return

    print_box(
        "EDIT EVENT " + event_id,
        [
            "1. Change title",
            "2. Change description",
            "3. Change start time, end time, and room",
            "4. Change capacity",
            "5. Change registration deadline",
            "6. Return",
        ],
    )
    choice = input("Choose an option: ").strip()
    now = datetime.now()

    if choice == "1":
        new_title = input("New title: ")
        success, message = event_manager.change_title(
            event_id, organizer_id, new_title, now
        )
        if success:
            save_or_exit(storage, data)
        show_result(success, message)
    elif choice == "2":
        new_description = input("New description (optional): ")
        success, message = event_manager.change_description(
            event_id, organizer_id, new_description, now
        )
        if success:
            save_or_exit(storage, data)
        show_result(success, message)
    elif choice == "3":
        show_message("INFO", "Press Enter to keep the current value.")
        new_start = input(
            "New start time [" + format_datetime(event["start_time"]) + "]: "
        ).strip()
        new_end = input(
            "New end time [" + format_datetime(event["end_time"]) + "]: "
        ).strip()
        new_room = input("New room ID [" + event["room_id"] + "]: ").strip()

        if new_start == "":
            new_start = format_datetime(event["start_time"])
        if new_end == "":
            new_end = format_datetime(event["end_time"])
        if new_room == "":
            new_room = event["room_id"]

        success, message, conflicts = event_manager.change_schedule(
            event_id,
            organizer_id,
            new_start,
            new_end,
            new_room,
            now,
        )
        if success:
            save_or_exit(storage, data)
        show_result(success, message)
        if len(conflicts) > 0:
            print_conflicting_events(conflicts)
    elif choice == "4":
        new_capacity = input("New event capacity: ").strip()
        success, message, should_promote = event_manager.change_capacity(
            event_id, organizer_id, new_capacity, now
        )
        promoted_results = []
        if success and should_promote:
            promoted_results = registration_manager.promote_waitlists(now)
        if success:
            save_or_exit(storage, data)
        show_result(success, message)
        show_promotions(promoted_results)
    elif choice == "5":
        new_deadline = input("New deadline (DD-MM-YYYY HH:MM): ")
        success, message = event_manager.change_deadline(
            event_id, organizer_id, new_deadline, now
        )
        if success:
            save_or_exit(storage, data)
        show_result(success, message)
    elif choice == "6":
        return
    else:
        show_message("ERROR", "Invalid option.")


def show_roster(organizer_id, event_manager, registration_manager):
    events = list_my_events(organizer_id, event_manager, registration_manager)
    if len(events) == 0:
        return

    event_id = input("Enter the event ID: ").strip()
    now = datetime.now()
    success, message, roster = registration_manager.get_roster(
        event_id, organizer_id, now
    )

    if not success:
        show_result(False, message)
        return

    event = roster["event"]
    lines = [
        "Confirmed: "
        + str(len(roster["confirmed_users"]))
        + " | Places remaining: "
        + str(roster["remaining"])
        + " | Active waitlist: "
        + str(len(roster["current_waiting"]))
    ]

    lines.append("")
    lines.append("Confirmed participants (sorted by user ID):")
    if len(roster["confirmed_users"]) == 0:
        lines.append("  None")
    else:
        for user_id in roster["confirmed_users"]:
            lines.append("  - " + user_id)

    lines.append("")
    lines.append("Current waitlist:")
    if len(roster["current_waiting"]) == 0:
        lines.append("  None")
    else:
        for user_id, position in roster["current_waiting"]:
            lines.append("  - Position " + str(position) + ": " + user_id)

    lines.append("")
    lines.append("Not promoted before the deadline (expired):")
    if len(roster["expired_waiting"]) == 0:
        lines.append("  None")
    else:
        for user_id in roster["expired_waiting"]:
            lines.append("  - " + user_id)

    print_box("ROSTER - " + event["event_id"] + " " + event["title"], lines)


def organizer_menu(
    user_id,
    room_manager,
    event_manager,
    registration_manager,
    storage,
    data,
):
    while True:
        run_promotions(registration_manager, storage, data)
        print_box(
            "ORGANIZER MENU - USER " + user_id,
            [
                "1. View room capacity, status, and schedule",
                "2. Create an event",
                "3. View and edit my events",
                "4. View an event roster",
                "5. Return to the user menu",
            ],
        )
        choice = input("Choose an option: ").strip()

        if choice == "1":
            show_rooms(room_manager, datetime.now())
        elif choice == "2":
            create_event(user_id, event_manager, room_manager, storage, data)
        elif choice == "3":
            edit_my_event(
                user_id,
                event_manager,
                registration_manager,
                storage,
                data,
            )
        elif choice == "4":
            show_roster(user_id, event_manager, registration_manager)
        elif choice == "5":
            return
        else:
            show_message("ERROR", "Invalid option. Please try again.")


def normal_user_menu(
    user_id,
    room_manager,
    event_manager,
    registration_manager,
    storage,
    data,
):
    while True:
        run_promotions(registration_manager, storage, data)
        print_box(
            "USER MENU - USER " + user_id,
            [
                "1. Participant",
                "2. Organizer",
                "3. Exit",
            ],
        )
        choice = input("Choose an option: ").strip()

        if choice == "1":
            participant_menu(
                user_id,
                event_manager,
                registration_manager,
                storage,
                data,
            )
        elif choice == "2":
            organizer_menu(
                user_id,
                room_manager,
                event_manager,
                registration_manager,
                storage,
                data,
            )
        elif choice == "3":
            show_message("INFO", "Goodbye!")
            return
        else:
            show_message("ERROR", "Invalid option. Please try again.")


def add_room(room_manager, storage, data):
    name = input("Room name: ")
    capacity = input("Room capacity: ").strip()
    success, message, room = room_manager.add_room(name, capacity)

    if success:
        save_or_exit(storage, data)
        show_result(True, message + " Room ID: " + room["room_id"])
    else:
        show_result(False, message)


def change_room_status(room_manager, storage, data):
    room_id = input("Room ID: ").strip()
    new_status = input("New status (available/unavailable): ").strip().lower()
    success, message, blocking_events = room_manager.change_room_status(
        room_id, new_status, datetime.now()
    )

    if success:
        save_or_exit(storage, data)
    show_result(success, message)
    if len(blocking_events) > 0:
        print_conflicting_events(blocking_events, "EVENTS BLOCKING THIS CHANGE")


def delete_room(room_manager, storage, data):
    now = datetime.now()
    room_id = input("Room ID to delete: ").strip()
    room = room_manager.find_room(room_id)

    if room is None:
        show_message("ERROR", "The room does not exist or has been deleted.")
        return

    blocking_events = room_manager.get_unfinished_events(room_id, now)
    if len(blocking_events) > 0:
        show_message("ERROR", "The room has unfinished events and cannot be deleted.")
        print_conflicting_events(blocking_events, "EVENTS BLOCKING DELETION")
        return

    print_box(
        "DELETE ROOM WARNING",
        [
            "[WARNING] Room to delete: "
            + room["room_id"]
            + " | "
            + room["name"]
            + " | Capacity "
            + str(room["capacity"]),
            "This action cannot be undone.",
        ],
    )
    answer = input("Deletion cannot be undone. Confirm? (y/n): ").strip().lower()
    if answer != "y":
        show_message("INFO", "Deletion cancelled.")
        return

    success, message, blocking_events, deleted_room = room_manager.delete_room(
        room_id, now
    )
    if success:
        save_or_exit(storage, data)
    show_result(success, message)
    if len(blocking_events) > 0:
        print_conflicting_events(blocking_events, "EVENTS BLOCKING DELETION")


def admin_menu(room_manager, registration_manager, storage, data):
    while True:
        run_promotions(registration_manager, storage, data)
        print_box(
            "ADMINISTRATOR MENU",
            [
                "1. Browse rooms",
                "2. Add a room",
                "3. Change room status",
                "4. Delete a room",
                "5. Exit",
            ],
        )
        choice = input("Choose an option: ").strip()

        if choice == "1":
            show_rooms(room_manager, datetime.now())
        elif choice == "2":
            add_room(room_manager, storage, data)
        elif choice == "3":
            change_room_status(room_manager, storage, data)
        elif choice == "4":
            delete_room(room_manager, storage, data)
        elif choice == "5":
            show_message("INFO", "Administrator signed out.")
            return
        else:
            show_message("ERROR", "Invalid option. Please try again.")


def main():
    storage = Storage()

    try:
        data = storage.load_data()
    except (FileNotFoundError, ValueError, OSError) as error:
        show_message("ERROR", "Failed to load data: " + str(error))
        return

    room_manager = RoomManager(data)
    event_manager = EventManager(data)
    registration_manager = RegistrationManager(data)

    run_promotions(registration_manager, storage, data)

    while True:
        user_input = input("Enter a user ID (enter admin for administrator mode): ")
        valid, message, user_id = validate_text(user_input, "User ID")
        if valid:
            break
        show_message("ERROR", message)

    if user_id.lower() == "admin":
        admin_menu(room_manager, registration_manager, storage, data)
    else:
        normal_user_menu(
            user_id,
            room_manager,
            event_manager,
            registration_manager,
            storage,
            data,
        )


if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        show_message("INFO", "The program exited safely.")
