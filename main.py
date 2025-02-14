import os
import pickle
import uuid
from datetime import datetime, timedelta, timezone, time

import pytz
from caldav import DAVClient
from icalendar import Calendar, Event
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from pydantic_settings import BaseSettings

# Import your helper function (make sure it’s defined in functions.py)
from functions import convert_iso_timezone


# -------------------------------
# Configuration using Pydantic
# -------------------------------
class Config(BaseSettings):
    # Yandex credentials
    yandex_username: str
    yandex_password: str
    yandex_calname: str

    # Google credentials and settings
    google_credentials_file: str = "credentials.json"
    google_token_file: str = "token.pickle"
    google_scopes: list[str] = ["https://www.googleapis.com/auth/calendar"]
    google_calname: str = "primary"

    # Time window settings for events
    past_days: int = 7
    future_days: int = 30

    class Config:
        # You can set your environment file here
        env_file = ".env"


# -------------------------------
# Yandex Calendar Client (using caldav)
# -------------------------------
class YandexCalendarClient:
    def __init__(self, config: Config):
        self.config = config
        self.utc_tz = pytz.utc
        # Connect to Yandex Calendar using DAVClient
        self.client = DAVClient(
            url="https://caldav.yandex.ru",
            username=config.yandex_username,
            password=config.yandex_password,
        )
        self.principal = self.client.principal()
        self.calendar = self._get_calendar_by_name(config.yandex_calname)

    def _get_calendar_by_name(self, cal_name: str):
        """Retrieve the calendar with the specified name."""
        calendars = self.principal.calendars()
        for cal in calendars:
            if cal.name == cal_name:
                return cal
        raise ValueError(f"Calendar named {cal_name} not found.")

    def get_events(self, start: datetime, end: datetime) -> dict:
        """Retrieve events from the Yandex calendar within the specified time range."""
        events_data = {}
        events = self.calendar.search(start=start, end=end)
        for event in events:
            ics_data = event.data
            cal = Calendar.from_ical(ics_data)
            for component in cal.walk("VEVENT"):
                name = component.get("summary").encode("utf-8").decode("utf-8")
                desc = component.get("description", "").encode("utf-8").decode("utf-8")
                dtstart = component.get("dtstart").dt
                dtend = component.get("dtend").dt
                # Ensure datetime objects are in UTC
                if dtstart.tzinfo is None:
                    dtstart = dtstart.replace(tzinfo=timezone.utc)
                else:
                    dtstart = dtstart.astimezone(timezone.utc)
                if dtend.tzinfo is None:
                    dtend = dtend.replace(tzinfo=timezone.utc)
                else:
                    dtend = dtend.astimezone(timezone.utc)
                start_iso = dtstart.isoformat()
                events_data[f"{name}/{start_iso}"] = {
                    "name": name,
                    "description": desc,
                    "start": start_iso,
                    "end": dtend.isoformat(),
                }
        return events_data

    def add_event(self, event_data: dict):
        """Add an event to the Yandex calendar."""
        cal = Calendar()
        cal.add("prodid", "CalendarSyncApp")
        cal.add("version", "2.0")

        ical_event = Event()
        ical_event.add("uid", str(uuid.uuid4()))
        ical_event.add("summary", event_data["name"])
        ical_event.add("description", event_data.get("description", ""))
        ical_event.add("dtstart", datetime.fromisoformat(event_data["start"]))
        ical_event.add("dtend", datetime.fromisoformat(event_data["end"]))

        cal.add_component(ical_event)
        ics_data = cal.to_ical().decode("utf-8")
        self.calendar.add_event(ics_data)


# -------------------------------
# Google Calendar Client
# -------------------------------
class GoogleCalendarClient:
    def __init__(self, config: Config):
        self.config = config
        self.service = self._authenticate()

    def _authenticate(self):
        """Authenticate and obtain the Google Calendar service credentials."""
        creds = None
        token_file = self.config.google_token_file
        if os.path.exists(token_file):
            with open(token_file, "rb") as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.config.google_credentials_file, self.config.google_scopes
                )
                creds = flow.run_local_server(port=0)
            with open(token_file, "wb") as token:
                pickle.dump(creds, token)
        return build("calendar", "v3", credentials=creds)

    def get_events(self, start: datetime, end: datetime) -> dict:
        """Retrieve events from the Google calendar within the specified time range."""
        events_data = {}
        events_result = self.service.events().list(
            calendarId=self.config.google_calname,
            timeMin=start.isoformat(timespec="seconds"),
            timeMax=end.isoformat(timespec="seconds"),
            singleEvents=True,
        ).execute()
        events = events_result.get("items", [])
        for event in events:
            name = event.get("summary")
            desc = event.get("description", "").encode("utf-8").decode("utf-8")
            start_dt = convert_iso_timezone(event.get("start", {}).get("dateTime"), timezone.utc)
            end_dt = convert_iso_timezone(event.get("end", {}).get("dateTime"), timezone.utc)
            events_data[f"{name}/{start_dt}"] = {
                "name": name,
                "description": desc,
                "start": start_dt,
                "end": end_dt,
            }
        return events_data

    def add_event(self, event_data: dict, time_limit: datetime, time_limit_future: datetime):
        """Add an event to the Google calendar if it falls within the allowed time range."""
        start_dt = datetime.fromisoformat(event_data["start"])
        # Skip events outside the defined time range
        if start_dt < time_limit or start_dt > time_limit_future:
            print(
                f"Event '{event_data['name']}' skipped because its start time {start_dt} is out of range."
            )
            return

        event_body = {
            "summary": event_data["name"],
            "description": event_data.get("description", ""),
            "start": {"dateTime": event_data["start"], "timeZone": "UTC"},
            "end": {"dateTime": event_data["end"], "timeZone": "UTC"},
        }
        self.service.events().insert(
            calendarId=self.config.google_calname, body=event_body
        ).execute()


# -------------------------------
# Calendar Synchronization Manager
# -------------------------------
class CalendarSyncManager:
    def __init__(self, config: Config):
        self.config = config
        self.utc_tz = pytz.utc
        self.yandex_client = YandexCalendarClient(config)
        self.google_client = GoogleCalendarClient(config)
        # Define time limits based on the current date and config settings
        today = datetime.now(self.utc_tz).date()
        self.time_limit = datetime.combine(
            today - timedelta(days=config.past_days), time.min
        ).replace(tzinfo=self.utc_tz)
        self.time_limit_future = datetime.combine(
            today + timedelta(days=config.future_days), time.max
        ).replace(tzinfo=self.utc_tz)

    def sync(self):
        """Synchronize events between Yandex and Google calendars."""
        # Retrieve events from both calendars
        yandex_events = self.yandex_client.get_events(self.time_limit, self.time_limit_future)
        google_events = self.google_client.get_events(self.time_limit, self.time_limit_future)

        # Merge events from both calendars (unique key: "name/start_time")
        all_events = {**yandex_events, **google_events}

        print(
            f"Total events: {len(all_events)}, Yandex events: {len(yandex_events)}, Google events: {len(google_events)}"
        )

        # Determine events missing in each calendar
        yandex_missing_keys = set(all_events.keys()) - set(yandex_events.keys())
        google_missing_keys = set(all_events.keys()) - set(google_events.keys())

        print("Missing events in Yandex:", yandex_missing_keys)
        for event_key in yandex_missing_keys:
            event_data = all_events[event_key]
            self.yandex_client.add_event(event_data)

        print("Missing events in Google:", google_missing_keys)
        for event_key in google_missing_keys:
            event_data = all_events[event_key]
            self.google_client.add_event(event_data, self.time_limit, self.time_limit_future)


# -------------------------------
# Main execution
# -------------------------------
def main():
    # Load configuration from environment variables or the .env file
    config = Config()
    sync_manager = CalendarSyncManager(config)
    sync_manager.sync()


if __name__ == "__main__":
    main()
