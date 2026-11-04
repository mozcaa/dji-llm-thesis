# DJI KMZ Mission Planner

A browser-based editor for waypoint missions, built with Python, Flask and MapLibre GL JS. Place waypoints on a satellite map, configure their actions, and export the mission as a KMZ archive using DJI WPML elements.

This project is an experimental local tool. Compatibility with specific DJI aircraft, payloads and mission applications has not been established.

## Features

- Add waypoints by clicking the map and move them by dragging their markers.
- Insert a waypoint between two existing points using the **+** marker.
- Edit mission height, speed and payload position index.
- Add, remove, edit and drag to reorder waypoint actions.
- Undo and redo edits with buttons or keyboard shortcuts.
- Load supported KMZ files and download the edited mission.

Supported actions: `takePhoto`, `focus`, `zoom`, `gimbalRotate`, `rotateYaw` and `hover`.

## Getting started

You need Python 3 with `pip` and virtual environment support, a modern browser, and a MapTiler web API key. Internet access is required for map tiles and the frontend libraries loaded from CDNs.

Run these commands from a terminal on Linux or macOS:

```bash
git clone https://github.com/bettisfr/dji-kmz-mission-planner.git
cd dji-kmz-mission-planner
python3 -m venv .venv
source .venv/bin/activate
python -m pip install Flask geopy lxml
mkdir -p out
export MAPTILER_WEB_API_KEY="your-maptiler-web-api-key"
python server.py
```

Open <http://127.0.0.1:5000> in your browser. Run the server from the repository root: file paths are relative to the working directory.

On Windows PowerShell, activate the environment with `.venv\Scripts\Activate.ps1`, create the output directory with `New-Item -ItemType Directory -Force out`, and set the key with `$env:MAPTILER_WEB_API_KEY = "your-maptiler-web-api-key"`.

The MapTiler key is sent to the browser for map requests. Use a key intended for web use and configure its allowed origins in your MapTiler account. The app reads the environment variable directly; it does not automatically load a `.env` file.

## Usage

1. The app starts with a sample mission near Assisi, Italy.
2. Click the map to append waypoints, drag markers to move them, or click a **+** marker to insert a point along the route.
3. Edit global parameters in the sidebar. Current height and speed inputs accept whole numbers; keep speed greater than zero. Height is in metres and speed is in metres per second.
4. Click **add** beside a waypoint's actions to choose an action and enter its parameters. Drag action blocks to change their execution order. Edited values are submitted when the input loses focus.
5. Use **Undo** / **Redo**, `Ctrl+Z` / `Ctrl+Shift+Z` or `Ctrl+Y` (`Cmd` on macOS). Shortcuts leave native text editing behavior in place while an input has focus.
6. Click **Save** to download `mission.kmz`, or **Load** to replace the current mission with a supported archive.

Save your work before restarting the server: mission data and undo history live in memory, and a restart restores the sample mission.

## KMZ support and current limitations

The importer and exporter implement a limited subset of WPML with namespace `http://www.dji.com/wpmz/1.0.3`.

- Archives currently contain `waylines.wpml` and `template.kml` at the archive root. The importer expects `waylines.wpml` there; archives containing it under `wpmz/` are not supported.
- The exported `template.kml` is a minimal document. Full compatibility with DJI mission editors is not guaranteed.
- Export uses fixed aircraft and payload identifiers (`droneEnumValue=60`, `payloadEnumValue=42`) and fixed mission behavior, including return home on completion. These settings are defined in `parser_xml.py`.
- All waypoints share one height and speed. Import reads takeoff security height and transitional speed into those global values; individual waypoint settings and other unsupported data are not preserved when exporting again.
- Only the actions and parameters listed in `mission.py` are supported. Unknown actions or missing XML fields can cause import errors.
- Use filenames with a single extension, such as `survey.kmz`; additional dots currently break the import filename handling.
- Mission state, undo history and output files are shared by all browser sessions connected to the same server.
- The app uses Flask's development server with debug mode enabled and has no authentication. Run it locally and load trusted files.

Review exported mission settings in a compatible mission application before using them with an aircraft.

## Project structure

```text
server.py               Flask routes, shared mission state, undo/redo
mission.py              Mission, waypoint and action models
parser_xml.py           XML serialization and KMZ import/export
templates/index.html    Main application page
templates/map_config.js Browser map configuration
static/script.js        Map interactions, sidebar and API requests
static/styles.css       Application styles
out/                    Generated archives, XML and uploaded files
```

The frontend uses MapLibre GL JS, MapTiler satellite imagery, jQuery and jQuery UI. No frontend build step is required.

## Contributing

Issues and pull requests are welcome. For import or compatibility problems, include the error message, the expected behavior and a minimal mission example with sensitive coordinates removed.
