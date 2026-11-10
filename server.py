
import os
import copy

from flask import Flask, render_template, jsonify, request, send_from_directory
from mission import create_mock_mission, print_mission, Waypoint, Action, ACTIONS, create_empty_mission, mission_from_dict
from parser_xml import mission_to_kmz, kmz_to_mission
import validator  #validatorFun, validateFocus, validatetakePhoto, validategimbalRotate, validaterotateYaw, validatehover, validatezoom, validateRange, validateExistingIndex, validateNewWaypoint, validateNewWaypointAt, validateUpdateWaypoint, validateUpdateWaypointSpeed, validateUpdateWaypointQuote


# Applicazione Flask e missione conservata in memoria.
app = Flask(__name__)
mission = create_mock_mission()
# mission = create_empty_mission()

# Cronologia delle modifiche per Undo e Redo, con un massimo di 100 stati Undo.
UNDO_LIMIT = 100
undo_stack = []
redo_stack = []


# Mostra la pagina principale del planner.
@app.route('/')
def index():
    return render_template('index.html')


# Restituisce la configurazione JavaScript della mappa con la chiave MapTiler.
@app.route('/map_config.js')
def map_config():
    response = app.make_response(render_template(
        'map_config.js',
        maptiler_api_key=os.environ.get('MAPTILER_WEB_API_KEY', '')  # Chiave letta dall'ambiente.
    ))
    response.mimetype = 'application/javascript'
    response.headers['Cache-Control'] = 'no-store'  # Evita di usare una copia in cache.
    return response


# Invia al frontend la missione corrente in formato JSON.
@app.route('/get_mission')
def get_mission():
    print_mission(mission)
    return jsonify(mission.to_dict())


# Crea una copia indipendente della missione per la cronologia.
def _snapshot_current_mission():
    return copy.deepcopy(mission.to_dict())


# Registra la missione prima di una modifica e azzera la cronologia Redo.
def _record_undo_state():
    undo_stack.append(_snapshot_current_mission())
    if len(undo_stack) > UNDO_LIMIT:
        undo_stack.pop(0)  # Elimina lo stato più vecchio.
    redo_stack.clear()


# Ripristina una missione salvata come dizionario.
def _restore_from_snapshot(snapshot):
    global mission  # La missione corrente viene riassegnata.
    mission = mission_from_dict(snapshot)


# Riceve un file KMZ, lo salva e ne carica il contenuto come missione corrente.
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
    mission = kmz_to_mission(mission_name)  # Ricostruisce gli oggetti Python dal KMZ.
    print_mission(mission)

    return jsonify({"status": "success", "message": f"Mission loaded successfully"}), 200


# Esporta la missione in KMZ e lo restituisce al browser come download.
@app.route('/save_mission')
def save_mission():
    mission_to_kmz(mission, "mission")
    output_directory = "out"
    filename = "mission.kmz"
    return send_from_directory(output_directory, filename, as_attachment=True)


# Restituisce al frontend l'elenco delle azioni e dei relativi parametri.
@app.route('/available_actions')
def available_actions():
    return jsonify(ACTIONS)


# Aggiunge un waypoint alla fine della missione, con quota e velocità proprie.
@app.route('/add_waypoint', methods=['POST'])
def add_waypoint():

    data = request.get_json(silent=True) # Restituisce None se il JSON è assente o non valido, senza sollevare automaticamente un errore HTTP.

    if not isinstance(data, dict): #controlla che il JSON ricevuto sia effettivamente un oggetto
     return jsonify({
         "status": "failed",
         "message": "Richiesta JSON non valida"
     }), 400
    
    lat = data.get('lat')
    lon = data.get('lon')
    speed = data.get('speed', 5.0)  # Valore iniziale se il frontend non lo invia.
    quote = data.get('quote', 10.0)  # Quota iniziale se il frontend non la invia.

    status, message= validator.validateNewWaypoint(lat, lon, speed, quote)
    if not(status): 
     return jsonify({"status": "failed", "message": message}), 400 
    
    _record_undo_state()
    wp_new = Waypoint(lat=float(lat), lon=float(lon), speed=float(speed), quote=float(quote))
    mission.add_waypoint(wp_new)  # Aggiorna anche gli ID.

    print(f"Creating new waypoint {wp_new} with new coordinates: {lat}, {lon}, speed: {speed} and quote: {quote}")
    print_mission(mission)
    return jsonify({"status": "success", "message": f"Waypoint added successfully"}), 200


# Inserisce un waypoint nella posizione indicata, con quota e velocità proprie.
@app.route('/add_waypoint_at', methods=['POST'])
def add_waypoint_at():
    data = request.get_json(silent=True)

    if not isinstance(data, dict): #controlla che il JSON ricevuto sia effettivamente un oggetto
     return jsonify({
         "status": "failed",
         "message": "Richiesta JSON non valida"
     }), 400

    lat = data.get('lat')
    lon = data.get('lon')
    speed = data.get('speed', 5.0)
    quote =data.get('quote', 10.0)
    index = data.get('index')

    status, message= validator.validateNewWaypointAt(lat, lon, speed, quote, index, len(mission.waypoints))
    if not(status): 
     return jsonify({"status": "failed", "message": message}), 400 

    _record_undo_state()
    wp_new = Waypoint(lat=float(lat), lon=float(lon), speed=float(speed), quote=float(quote))
    mission.add_waypoint_at(wp_new, index)  # Inserisce il punto senza sostituire quelli esistenti.

    print(f"Creating new waypoint {wp_new} between with new coordinates: {lat}, {lon}, speed: {speed} and quote: {quote}")
    print_mission(mission)
    return jsonify({"status": "success", "message": f"Waypoint added successfully"}), 200



# Aggiorna le coordinate di un waypoint esistente.
@app.route('/update_waypoint', methods=['POST'])
def update_waypoint():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"status": "failed", "message": "Richiesta JSON non valida"}), 400

    waypoint_id = data.get('waypoint_id')
    lat = data.get('lat')
    lon = data.get('lon')

    status, message = validator.validateUpdateWaypoint(lat, lon, waypoint_id, len(mission.waypoints))
    if not status:
        return jsonify({"status": "failed", "message": message}), 400

    _record_undo_state()
    mission.waypoints[waypoint_id].update_waypoint_coordinates(float(lat), float(lon))

    print(f"Updating waypoint {waypoint_id} with new coordinates: {lat}, {lon}")
    print_mission(mission)
    return jsonify({"status": "success", "message": f"Waypoint updated successfully"}), 200


# Aggiorna la velocità del tratto che parte dal waypoint indicato.
@app.route('/update_waypoint/speed', methods=['POST'])
def update_waypoint_speed():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"status": "failed", "message": "Richiesta JSON non valida"}), 400

    waypoint_id = data.get('waypoint_id')
    speed = data.get('speed')

    status, message = validator.validateUpdateWaypointSpeed(speed, waypoint_id, len(mission.waypoints))
    if not status:
        return jsonify({"status": "failed", "message": message}), 400

    _record_undo_state()
    mission.waypoints[waypoint_id].update_waypoint_speed(float(speed))

    print(f"Updating waypoint {waypoint_id} with new speed: {speed}")
    print_mission(mission)
    return jsonify({"status": "success", "message": "Waypoint speed updated successfully"}), 200


# Aggiorna la quota di un waypoint esistente.
@app.route('/update_waypoint/quote', methods=['POST'])
def update_waypoint_quote():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"status": "failed", "message": "Richiesta JSON non valida"}), 400

    waypoint_id = data.get('waypoint_id')
    quote = data.get('quote')

    status, message = validator.validateUpdateWaypointQuote(quote, waypoint_id, len(mission.waypoints))
    if not status:
        return jsonify({"status": "failed", "message": message}), 400

    _record_undo_state()
    mission.waypoints[waypoint_id].update_waypoint_quote(float(quote))

    print(f"Updating waypoint {waypoint_id} with new quote: {quote}")
    print_mission(mission)
    return jsonify({"status": "success", "message": "Waypoint quote updated successfully"}), 200



# Aggiorna il payloadIndex, unico parametro globale della missione.
@app.route('/update_global_parameter', methods=['POST'])
def update_global_parameter():
    data = request.get_json()
    
    if data.get('variable') != 'payloadIndex':
        return jsonify({"status": "error", "message": "Unsupported parameter"}), 400

    try:
        value = int(data.get('value'))
        if value < 0:
            return jsonify({"status": "error", "message": "Invalid payload index"}), 400
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "Invalid payload index"}), 400

    _record_undo_state()  # Salva lo stato precedente per Undo/Redo.
    mission.payload_index = value  # Modifica il parametro globale della missione.

    print(f"Updating global payload index to: {value}")
    print_mission(mission)
    return jsonify({"status": "success", "message": "Payload index updated successfully"}), 200


# Modifica un parametro di un'azione presente in un waypoint.
@app.route('/update_action', methods=['POST'])
def update_action():
    data = request.get_json()
    waypoint_id = int(data.get('waypoint_id'))
    action_id = int(data.get('action_id'))
    action_type = data.get('action_type')  # Nome del parametro da aggiornare.
    parameter = data.get('parameter')

    _record_undo_state()
    mission.waypoints[waypoint_id].update_waypoint_action(action_id, action_type, parameter)

    print(f"Updating action {action_type} on waypoint {waypoint_id} with new value: {parameter}")
    print_mission(mission)
    return jsonify({"status": "success", "message": f"Waypoint updated successfully"}), 200


# Elimina un waypoint e rinumera quelli rimasti.
@app.route('/remove_waypoint', methods=['POST'])
def remove_waypoint():
    data = request.get_json()
    waypoint_id = int(data.get('waypoint_id'))

    _record_undo_state()
    mission.remove_waypoint(waypoint_id)
    print(f"Removing waypoint {waypoint_id}")
    print_mission(mission)
    return jsonify({"status": "success", "message": f"Waypoint removed successfully"}), 200


# Aggiunge un'azione al waypoint specificato.
@app.route('/add_action', methods=['POST'])
def add_action():
    data = request.get_json()
    waypoint_id = int(data.get('waypoint_id'))
    action_type = data.get('action_type')
    parameters = data.get('parameters', {})

    _record_undo_state()
    action = Action(action_type, **parameters)  # Espande il dizionario nei parametri dell'azione.
    mission.add_action(waypoint_id, action)

    print(f"Adding action to waypoint {waypoint_id}")
    print_mission(mission)
    return jsonify({"status": "success", "message": f"Action added successfully"}), 200


# Rimuove un'azione dal waypoint specificato.
@app.route('/remove_action', methods=['POST'])
def remove_action():
    data = request.get_json()
    waypoint_id = int(data.get('waypoint_id'))
    action_id = int(data.get('action_id'))

    _record_undo_state()
    mission.remove_action(waypoint_id, action_id)
    print(f"Removing action {waypoint_id} - {action_id}")
    print_mission(mission)
    return jsonify({"status": "success", "message": f"Waypoint removed successfully"}), 200


# Riordina le azioni di un waypoint dopo aver controllato gli ID ricevuti.
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


# Annulla l'ultima modifica, conservando lo stato corrente per un eventuale Redo.
@app.route('/undo', methods=['POST'])
def undo():
    if len(undo_stack) == 0:
        return jsonify({"status": "error", "message": "Nothing to undo"}), 400

    redo_stack.append(_snapshot_current_mission())
    snapshot = undo_stack.pop()  # Recupera lo stato precedente.
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


# Ripristina l'ultima modifica annullata, conservando lo stato per un eventuale Undo.
@app.route('/redo', methods=['POST'])
def redo():
    if len(redo_stack) == 0:
        return jsonify({"status": "error", "message": "Nothing to redo"}), 400

    undo_stack.append(_snapshot_current_mission())
    snapshot = redo_stack.pop()  # Recupera lo stato da ripristinare.
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


# Avvia il server Flask quando il modulo viene eseguito direttamente.
if __name__ == '__main__':
    app.run(debug=True)
