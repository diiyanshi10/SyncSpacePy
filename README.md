# SyncSpace

SyncSpace is a real-time group and private messaging application built with Flask, Flask-SocketIO, MySQL, and a browser-based frontend.

## Features

- User registration and login
- Group creation, joining, renaming, and member management
- Real-time group chat
- Private messages
- Message reactions
- Online presence updates
- User profiles and password changes
- Light/dark mode and selectable visual themes

## Requirements

- Python 3.10 or newer
- MySQL Server
- A MySQL database with the schema expected by the DAO files

## Setup

1. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install the dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Create the database and required tables in MySQL. The project currently does not include database migrations or schema creation scripts.

4. Copy the example configuration and update the MySQL credentials:

   ```powershell
   Copy-Item config.example.py config.py
   ```

   Edit `config.py` with the host, port, database name, username, and password for your MySQL server.

## Run the application

Start the server from the project directory:

```powershell
python app.py
```

Open [http://localhost:8080](http://localhost:8080) in a browser.

The server listens on port `8080` and serves the frontend from `index.html`.

## Project structure

```text
app.py                 Flask and Socket.IO server
config.example.py      Example MySQL configuration
db.py                  MySQL connection pool
index.html             Browser frontend
requirements.txt       Python dependencies
dao/                   Database access objects
static/                Client-side static files
themes/                Theme wallpaper assets
```

## API overview

The backend provides endpoints for authentication, profiles, groups, messages, private messages, reactions, contacts, and presence. The browser frontend communicates with the backend using HTTP requests and Socket.IO events.

## Configuration and security

- Keep real database credentials in `config.py` only.
- Do not commit passwords or other secrets.
- `config.py` is intended to remain ignored by Git.
- The current development server enables permissive CORS settings; review these before production deployment.
