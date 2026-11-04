import os
import copy

from flask import Flask, render_template, jsonify, request, send_from_directory
from mission import create_mock_mission, print_mission, Waypoint, Action, ACTIONS, create_empty_mission, mission_from_dict
from parser_xml import mission_to_kmz, kmz_to_mission

app = Flask(__name__)

mission = create_mock_mission()
# mission = create_empty_mission()
UNDO_LIMIT = 100
undo_stack = []
redo_stack = []

# print_mission(mission)
# mission.waypoints[3].update_waypoint_action(7, "aircraftHeading", -999)
# print_mission(mission)
# mission.remove_waypoint(1)
# print_mission(mission)
# mission.remove_action(1, 2)
# print_mission(mission)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/map_config.js')
def map_config():
    response = app.make_response(render_template(
        'map_config.js',
        maptiler_api_key=os.environ.get('MAPTILER_WEB_API_KEY', '')
    ))
    response.mimetype = 'application/javascript'
    response.headers['Cache-Control'] = 'no-store'
    return response


@app.route('/get_mission')
def get_mission():
    print_mission(mission)
    return jsonify(mission.to_dict())


def _snapshot_current_mission():
    return copy.deepcopy(mission.to_dict())


def _record_undo_state():
    undo_stack.append(_snapshot_current_mission())
    if len(undo_stack) > UNDO_LIMIT:
        undo_stack.pop(0)
    redo_stack.clear()


def _restore_from_snapshot(snapshot):
    global mission
    mission = mission_from_dict(snapshot)


@app.route('/load_mission', methods=['POST'])
def load_mission():
    global mission
    if 'file' not in request.files:
        return "No file part", 400

    file = request.files['file']

    if file.filename == '':
        return "No selected file", 400

    out_folder = 'out'
    file_path = os.path.join(out_folder, file.filename)
    file.save(file_path)

    mission_name = file.filename.split(".")[0]
    _record_undo_state()
    mission = kmz_to_mission(mission_name)
    print_mission(mission)

    return jsonify({"status": "success", "message": f"Mission loaded successfully"}), 200


@app.route('/save_mission')
def save_mission():
    mission_to_kmz(mission, "mission")
    output_directory = "out"
    filename = "mission.kmz"

    # Send the file to the client
    return send_from_directory(output_directory, filename, as_attachment=True)


@app.route('/available_actions')
def available_actions():
    return jsonify(ACTIONS)


@app.route('/add_waypoint', methods=['POST'])
def add_waypoint():
    data = request.get_json()
    lat = data.get('lat')
    lon = data.get('lon')

    _record_undo_state()
    wp_new = Waypoint(lat=lat, lon=lon)
    mission.add_waypoint(wp_new)
    print(f"Creating new waypoint {wp_new} with new coordinates: {lat}, {lon}")

    print_mission(mission)

    return jsonify({"status": "success", "message": f"Waypoint added successfully"}), 200


@app.route('/add_waypoint_at', methods=['POST'])
def add_waypoint_at():
    data = request.get_json()
    lat = data.get('lat')
    lon = data.get('lon')
    index = data.get('index')

    _record_undo_state()
    wp_new = Waypoint(lat=lat, lon=lon)
    mission.add_waypoint_at(wp_new, index)
    print(f"Creating new waypoint {wp_new} between with new coordinates: {lat}, {lon}")

    print_mission(mission)

    return jsonify({"status": "success", "message": f"Waypoint added successfully"}), 200


@app.route('/update_waypoint', methods=['POST'])
def update_waypoint():
    data = request.get_json()
    waypoint_id = data.get('waypoint_id')
    lat = data.get('lat')
    lon = data.get('lon')

    _record_undo_state()
    mission.waypoints[waypoint_id].update_waypoint_coordinates(lat, lon)
    print(f"Updating waypoint {waypoint_id} with new coordinates: {lat}, {lon}")

    print_mission(mission)

    return jsonify({"status": "success", "message": f"Waypoint updated successfully"}), 200


@app.route('/update_action', methods=['POST'])
def update_action():
    data = request.get_json()
    waypoint_id = int(data.get('waypoint_id'))
    action_id = int(data.get('action_id'))
    action_type = data.get('action_type')
    parameter = data.get('parameter')

    _record_undo_state()
    mission.waypoints[waypoint_id].update_waypoint_action(action_id, action_type, parameter)
    print(f"Updating action {action_type} on waypoint {waypoint_id} with new value: {parameter}")

    print_mission(mission)

    return jsonify({"status": "success", "message": f"Waypoint updated successfully"}), 200


@app.route('/update_global_parameter', methods=['POST'])
def update_global_parameter():
    data = request.get_json()
    variable = data.get('variable')
    value = int(data.get('value'))

    if variable == "height":
        _record_undo_state()
        mission.height = value
    elif variable == "speed":
        _record_undo_state()
        mission.speed = value
    elif variable == "payloadIndex":
        _record_undo_state()
        mission.payload_index = value
    else:
        return jsonify({"status": "error", "message": f"Invalid variable"}), 400

    print(f"Updating global parameter {variable} with new value: {value}")

    print_mission(mission)

    return jsonify({"status": "success", "message": f"Waypoint updated successfully"}), 200


@app.route('/remove_waypoint', methods=['POST'])
def remove_waypoint():
    data = request.get_json()
    waypoint_id = data.get('waypoint_id')

    _record_undo_state()
    mission.remove_waypoint(waypoint_id)
    print(f"Removing waypoint {waypoint_id}")

    print_mission(mission)

    return jsonify({"status": "success", "message": f"Waypoint removed successfully"}), 200


@app.route('/add_action', methods=['POST'])
def add_action():
    data = request.get_json()
    waypoint_id = data.get('waypoint_id')
    action_type = data.get('action_type')
    parameters = data.get('parameters', {})

    _record_undo_state()
    action = Action(action_type, **parameters)
    mission.add_action(waypoint_id, action)
    print(f"Adding action to waypoint {waypoint_id}")

    print_mission(mission)

    return jsonify({"status": "success", "message": f"Action added successfully"}), 200


@app.route('/remove_action', methods=['POST'])
def remove_action():
    data = request.get_json()
    waypoint_id = data.get('waypoint_id')
    action_id = data.get('action_id')

    _record_undo_state()
    mission.remove_action(waypoint_id, action_id)
    print(f"Removing action {waypoint_id} - {action_id}")

    print_mission(mission)

    return jsonify({"status": "success", "message": f"Waypoint removed successfully"}), 200


@app.route('/reorder_actions', methods=['POST'])
def reorder_actions():
    data = request.get_json()
    waypoint_id = int(data.get('waypoint_id'))
    ordered_action_ids = data.get('action_ids', [])

    if not isinstance(ordered_action_ids, list):
        return jsonify({"status": "error", "message": "action_ids must be a list"}), 400

    try:
        ordered_action_ids = [int(action_id) for action_id in ordered_action_ids]
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "action_ids must contain integers"}), 400

    if waypoint_id < 0 or waypoint_id >= len(mission.waypoints):
        return jsonify({"status": "error", "message": "Invalid waypoint id"}), 400

    current_action_ids = [action.action_id for action in mission.waypoints[waypoint_id].actions]
    if len(current_action_ids) != len(ordered_action_ids):
        return jsonify({"status": "error", "message": "Invalid action order length"}), 400
    if set(current_action_ids) != set(ordered_action_ids):
        return jsonify({"status": "error", "message": "Invalid action order ids"}), 400

    _record_undo_state()
    ok = mission.reorder_actions(waypoint_id, ordered_action_ids)
    if not ok:
        return jsonify({"status": "error", "message": "Invalid action order"}), 400

    print(f"Reordered actions on waypoint {waypoint_id}: {ordered_action_ids}")
    print_mission(mission)

    return jsonify({"status": "success", "message": "Actions reordered successfully"}), 200


@app.route('/undo', methods=['POST'])
def undo():
    if len(undo_stack) == 0:
        return jsonify({"status": "error", "message": "Nothing to undo"}), 400

    redo_stack.append(_snapshot_current_mission())
    snapshot = undo_stack.pop()
    _restore_from_snapshot(snapshot)

    print("Undo applied")
    print_mission(mission)

    return jsonify({
        "status": "success",
        "message": "Undo applied successfully",
        "mission": mission.to_dict(),
        "canUndo": len(undo_stack) > 0,
        "canRedo": len(redo_stack) > 0
    }), 200


@app.route('/redo', methods=['POST'])
def redo():
    if len(redo_stack) == 0:
        return jsonify({"status": "error", "message": "Nothing to redo"}), 400

    undo_stack.append(_snapshot_current_mission())
    snapshot = redo_stack.pop()
    _restore_from_snapshot(snapshot)

    print("Redo applied")
    print_mission(mission)

    return jsonify({
        "status": "success",
        "message": "Redo applied successfully",
        "mission": mission.to_dict(),
        "canUndo": len(undo_stack) > 0,
        "canRedo": len(redo_stack) > 0
    }), 200


if __name__ == '__main__':
    app.run(debug=True)
