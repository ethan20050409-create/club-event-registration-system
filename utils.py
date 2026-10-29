from datetime import datetime


DATETIME_FORMAT = "%d-%m-%Y %H:%M"
OLD_DATETIME_FORMAT = "%Y-%m-%d %H:%M"


def parse_datetime(text):
    """Turn DD-MM-YYYY HH:MM text into a datetime object."""
    return datetime.strptime(text.strip(), DATETIME_FORMAT)


def parse_stored_datetime(text):
    """Read the new format, or the old format used by earlier data files."""
    try:
        return parse_datetime(text)
    except ValueError:
        return datetime.strptime(text.strip(), OLD_DATETIME_FORMAT)


def format_datetime(value):
    return value.strftime(DATETIME_FORMAT)


def times_overlap(first_start, first_end, second_start, second_end):
    return first_start < second_end and second_start < first_end


def validate_text(text, field_name, allow_empty=False):
    cleaned_text = text.strip()

    if not allow_empty and cleaned_text == "":
        return False, field_name + " cannot be empty.", ""

    if "|" in cleaned_text or "\n" in cleaned_text or "\r" in cleaned_text:
        return False, field_name + " cannot contain | or a line break.", ""

    return True, "", cleaned_text


def parse_positive_integer(text, field_name):
    try:
        number = int(text)
    except ValueError:
        return False, field_name + " must be a positive integer.", None

    if number <= 0:
        return False, field_name + " must be a positive integer.", None

    return True, "", number


def generate_id(records, id_key, prefix):
    largest_number = 0

    for record in records:
        old_id = record[id_key]
        number_text = old_id[len(prefix):]

        if old_id.startswith(prefix) and number_text.isdigit():
            number = int(number_text)
            if number > largest_number:
                largest_number = number

    return prefix + str(largest_number + 1).zfill(3)


def get_event_status(event, now):
    if now >= event["end_time"]:
        return "Ended"
    if now >= event["start_time"]:
        return "In progress"
    if now >= event["deadline"]:
        return "Registration closed"
    return "Registration open"


def event_sort_key(event):
    return event["start_time"], event["event_id"]


def room_sort_key(room):
    return room["room_id"]


def waitlist_sort_key(record):
    return record["sequence"]


def waiting_event_sort_key(item):
    event, waitlist_record = item
    return waitlist_record["sequence"]

