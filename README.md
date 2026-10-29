# Club Event Registration System

A command-line Python application for managing club events, room schedules,
participant registrations, and waitlists. The program supports participant,
organizer, and administrator roles while storing all data in local text files.

## Features

### Participants

- Browse current and upcoming events.
- Register for events with capacity and schedule checks.
- Join or leave event waitlists.
- View and cancel confirmed registrations.
- Receive a notification after being promoted from a waitlist.
- Choose whether to leave other waitlists after a successful promotion.

### Organizers

- View room capacities, availability, and unfinished events.
- Create and edit events with step-by-step input validation.
- Enter `drop` at any stage to cancel event creation.
- Prevent overlapping events for the same organizer.
- View confirmed participants and active waitlists.

### Administrators

- Add rooms.
- Change room availability.
- Delete rooms that have no unfinished events.

## Validation and Scheduling

The system checks:

- Room availability, capacity, and schedule conflicts.
- Organizer schedule conflicts.
- Participant schedule conflicts.
- Event deadlines and start/end time boundaries.
- Duplicate registrations and waitlist requests.
- Event capacity before confirming a registration.

The date and time format is:

```text
DD-MM-YYYY HH:MM
```

Older event data saved as `YYYY-MM-DD HH:MM` can still be loaded. It is
converted to the current format the next time the program saves the data.

## Waitlist Promotion

Waitlist requests use one global sequence number. When a place becomes
available, the system considers requests in sequence order, skips participants
with schedule conflicts, and promotes the first eligible participant. Promotion
notifications are stored until the participant next opens the Participant menu.

## Project Structure

| File | Purpose |
| --- | --- |
| `main.py` | Program entry point and command-line menus |
| `event_manager.py` | Event creation, editing, and scheduling rules |
| `registration_manager.py` | Registrations, waitlists, and promotions |
| `room_manager.py` | Room creation, status changes, and deletion |
| `storage.py` | Text-file loading, validation, and saving |
| `utils.py` | Shared date, validation, sorting, and ID helpers |
| `test_system.py` | Automated tests for the main business rules |

## Requirements

- Python 3
- No third-party packages

## Running the Program

Open a terminal in the project folder and run:

```bash
python3 main.py
```

Enter `admin` as the user ID to open the Administrator menu. Any other valid
user ID opens the normal User menu, where the user can choose the Participant
or Organizer role.

The program automatically creates a `data` folder and the required text files
on first use. It also creates three available rooms so the application can be
used immediately.

## Running the Tests

Run the complete test suite with:

```bash
python3 -m unittest test_system -v
```

The tests use temporary folders and do not change the program's normal data.

