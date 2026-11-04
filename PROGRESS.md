
# Development Log — DJI LLM Mission Planner

## Project objective
Development and evaluation of a system that converts natural language instructions into DJI KMZ missions using local LLMs.

## November 2026 — Initial analysis

### Completed
- Studied the Mission data model (`mission.py`).
- Analyzed KMZ import/export (`parser_xml.py`).
- Studied the Flask backend (`server.py`).
- Reviewed the JavaScript frontend (`script.js`).
- Created a dedicated public GitHub repository.

### Next steps
- Test the existing planner and KMZ import/export.
- Refactor the frontend where necessary.
- Implement per-waypoint altitude and per-segment speed.
- Introduce mission validation and automated tests.
- Develop the first LLM-to-JSON pipeline.
