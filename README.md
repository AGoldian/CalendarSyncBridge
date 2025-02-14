# CalendarSyncBridge

# CalendarSyncBridge

**CalendarSyncBridge** is a Python project designed to synchronize events between a Yandex calendar (via CalDAV) and Google Calendar. The application retrieves events from both calendars within a specified time window and automatically creates missing events on the other side, ensuring both calendars are kept up-to-date.

> **Note:** This project is intended for personal or small-team use. Please test thoroughly with your calendars before deploying it in a production environment.

---

## Features

- **Bidirectional Synchronization:** Merges events from both calendars using a unique key (combination of event name and start time).
- **Time Range Filtering:** Synchronizes events within a customizable time window (past and future events).
- **Secure Configuration:** Uses a `.env` file (managed by `pydantic-settings`) to securely store Yandex credentials and other settings.
- **Google OAuth2 Authentication:** Handles Google authentication automatically via OAuth2 and stores tokens for future sessions.

---

## How It Works

1. **Configuration:**  
   The project uses a `.env` file to load configuration data (such as Yandex credentials and calendar settings) and a separate `credentials.json` file for Google OAuth2 credentials. The configuration is managed using the `pydantic-settings` package.

2. **Yandex Calendar Client:**  
   - Connects to the Yandex Calendar service using the CalDAV protocol.
   - Retrieves events from the specified Yandex calendar within a defined time window.
   - Adds events to Yandex when they are missing compared to Google Calendar.

3. **Google Calendar Client:**  
   - Authenticates using Google OAuth2. If no valid token is present, a browser window will open to complete the authentication process.
   - Retrieves events from the Google Calendar within the defined time window.
   - Inserts events into Google Calendar if they are missing compared to Yandex.

4. **Synchronization Manager:**  
   - Merges events from both calendars using a unique key (combination of event summary and start time).
   - Identifies events missing in each calendar.
   - Adds the missing events to the corresponding calendar.

---

## Prerequisites

- **Python 3.8+**
- **Virtual Environment Tool:** Such as `venv` or `pipenv`.
- **Google API Credentials:** A `credentials.json` file obtained from the Google Cloud Console.
- **Pydantic Settings:** For managing environment configuration (install via `pip install pydantic-settings`).

---

## Installation

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/agoldian/CalendarSyncBridge.git
   cd CalendarSyncBridge
   ```
Create a Virtual Environment and Install Dependencies:

Using venv:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```
Or using pipenv:

```bash
pipenv install
pipenv shell
```

Setup Environment Variables:

Create a .env file in the project root (or copy the provided .env.example file) and fill in the required values.

Configuration (.env File)
The .env file should contain your Yandex credentials and calendar settings. For example:
### Yandex Calendar Credentials
```
YANDEX_USERNAME=your_yandex_email@example.com
YANDEX_PASSWORD=your_yandex_app_password
YANDEX_CALNAME=YourYandexCalendarName
```

## Optional Google Configuration

Additional configuration options for Google Calendar integration can be adjusted directly in the source code. The default values are defined in the `Config` class and include:

- **google_credentials_file:**  
  Path to your Google OAuth credentials JSON file (default: `credentials.json`).

- **google_token_file:**  
  Path where the Google token file is stored (default: `token.pickle`).

- **google_scopes:**  
  A list of scopes for accessing the Google Calendar API (default: `["https://www.googleapis.com/auth/calendar"]`).

- **google_calname:**  
  The identifier for the Google Calendar to use (default: `"primary"`).

---

## Security Note

Do **not** commit your `.env` file to public repositories. Instead, add it to your `.gitignore` file and provide a template (e.g., `.env.example`) for reference.

---

## Obtaining Google Credentials

### Create a New Project

- Visit the [Google Cloud Console](https://console.cloud.google.com/).
- Create a new project or select an existing one.

### Enable the Google Calendar API

- In the project dashboard, navigate to **APIs & Services > Library**.
- Search for **Google Calendar API** and enable it.

### Configure the OAuth Consent Screen

- Under **APIs & Services**, go to **OAuth consent screen**.
- Configure the consent screen (choose "External" or "Internal" depending on your needs).

### Create OAuth Credentials

- Navigate to **APIs & Services > Credentials**.
- Click on **Create Credentials** and select **OAuth client ID**.
- Choose **Desktop App** as the application type.
- Download the generated `credentials.json` file and place it in the project root.

---

## Running the Application

On the first run, the application will use `credentials.json` to open a browser window for Google authentication. After successful authentication, a `token.pickle` file will be created to store your Google OAuth tokens for future sessions.

Activate your virtual environment and run the main script:

```bash
python main.py
```
The application will:

Load configuration from the .env file using pydantic-settings.
Connect to both Yandex and Google calendars.
Retrieve events within the specified time window.
Synchronize events by adding missing events to either calendar.
Troubleshooting
Missing .env or credentials.json:
Ensure that both files exist in the project directory. Verify that .env contains the correct Yandex credentials and that credentials.json is properly configured for Google OAuth2.

Google OAuth Issues:
If you encounter issues with Google authentication, delete the token.pickle file and run the application again to re-authenticate.

Pydantic Import Errors:
If you see errors regarding BaseSettings, ensure you have installed pydantic-settings and updated the import in your code:

```python
from pydantic_settings import BaseSettings
```
Contributing
Contributions are welcome! Please feel free to open issues or submit pull requests for improvements, bug fixes, or new features.

## License

This project is licensed under the MIT License.  
See the [LICENSE](LICENSE) file for details.

---

## Acknowledgements

- [CalDAV Library](https://github.com/python-caldav/caldav) for providing CalDAV integration with Yandex Calendar.
- [Google API Python Client](https://github.com/googleapis/google-api-python-client) for enabling Google Calendar integration.
- [Pydantic Settings](https://pydantic-settings.readthedocs.io) for robust configuration management.
- Thanks to all contributors and the open source community for their support and valuable contributions.