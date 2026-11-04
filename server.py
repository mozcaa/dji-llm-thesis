
import os
import copy

from flask import Flask, render_template, jsonify, request, send_from_directory
from mission import create_mock_mission, print_mission, Waypoint, Action, ACTIONS, create_empty_mission, mission_from_dict
from parser_xml import mission_to_kmz, kmz_to_mission

# Creazione dell'applicazione Flask.
app = Flask(__name__)

# Missione mantenuta in memoria dal server.
# Per ora viene inizializzata con una missione di esempio.
mission = create_mock_mission()
# mission = create_empty_mission()

# Numero massimo di stati precedenti conservati per l'Undo.
UNDO_LIMIT = 100

# Liste che conservano gli stati della missione per Undo e Redo.
undo_stack = []
redo_stack = []

# print_mission(mission)
# mission.waypoints[3].update_waypoint_action(7, "aircraftHeading", -999)
# print_mission(mission)
# mission.remove_waypoint(1)
# print_mission(mission)
# mission.remove_action(1, 2)
# print_mission(mission)


# Pagina principale della webapp.
# Flask cerca index.html nella cartella templates.
@app.route('/')
def index():
    return render_template('index.html')


# Restituisce il file JavaScript contenente la configurazione della mappa.
@app.route('/map_config.js')
def map_config():
    # render_template permette di inserire nel file il valore
    # della chiave MapTiler recuperata dalle variabili d'ambiente.
    response = app.make_response(render_template(
        'map_config.js',
        maptiler_api_key=os.environ.get('MAPTILER_WEB_API_KEY', '')
    ))

    # Indica al browser che la risposta contiene codice JavaScript.
    response.mimetype = 'application/javascript'

    # Evita che il browser riutilizzi una vecchia versione in cache.
    response.headers['Cache-Control'] = 'no-store'
    return response


# Restituisce al frontend la missione attualmente in memoria.
@app.route('/get_mission')
def get_mission():
    print_mission(mission)

    # to_dict() converte la missione in un dizionario Python,
    # mentre jsonify() lo trasforma in una risposta JSON.
    return jsonify(mission.to_dict())


# Crea una copia dello stato corrente della missione.
def _snapshot_current_mission():
    # deepcopy() produce una copia indipendente del dizionario,
    # comprese le strutture annidate come waypoint e azioni.
    return copy.deepcopy(mission.to_dict())


# Salva lo stato corrente prima di effettuare una modifica.
def _record_undo_state():
    undo_stack.append(_snapshot_current_mission())

    # Se viene superato il limite, elimina lo stato più vecchio.
    if len(undo_stack) > UNDO_LIMIT:
        undo_stack.pop(0)

    # Una nuova modifica interrompe la sequenza degli eventuali Redo.
    redo_stack.clear()


# Ricostruisce la missione a partire da uno stato salvato.
def _restore_from_snapshot(snapshot):
    # global permette di riassegnare la variabile mission
    # dichiarata fuori dalla funzione.
    global mission
    mission = mission_from_dict(snapshot)


# Riceve un file KMZ dal frontend e lo carica come missione corrente.
@app.route('/load_mission', methods=['POST'])
def load_mission():
    global mission

    # Controlla che la richiesta contenga un file nel campo "file".
    if 'file' not in request.files:
        return "No file part", 400

    file = request.files['file']

    # Controlla che sia stato selezionato un file.
    if file.filename == '':
        return "No selected file", 400

    # Costruisce il percorso in cui salvare il file ricevuto.
    out_folder = 'out'
    file_path = os.path.join(out_folder, file.filename)
    file.save(file_path)

    # Ricava il nome della missione dal nome del file.
    mission_name = file.filename.split(".")[0]

    # Conserva lo stato precedente per poter annullare il caricamento.
    _record_undo_state()

    # Il parser legge il KMZ e restituisce un oggetto Mission.
    mission = kmz_to_mission(mission_name)
    print_mission(mission)

    return jsonify({"status": "success", "message": f"Mission loaded successfully"}), 200


# Esporta la missione corrente come file KMZ scaricabile.
@app.route('/save_mission')
def save_mission():
    # Genera il KMZ a partire dall'oggetto Mission.
    mission_to_kmz(mission, "mission")

    output_directory = "out"
    filename = "mission.kmz"

    # Send the file to the client
    # as_attachment=True indica al browser di scaricare il file.
    return send_from_directory(output_directory, filename, as_attachment=True)


# Restituisce al frontend l'elenco delle azioni supportate
# e i relativi parametri, definiti nel dizionario ACTIONS.
@app.route('/available_actions')
def available_actions():
    return jsonify(ACTIONS)


# Aggiunge un nuovo waypoint alla fine della missione.
@app.route('/add_waypoint', methods=['POST'])
def add_waypoint():
    # Legge il JSON inviato dal frontend.
    data = request.get_json()
    lat = data.get('lat')
    lon = data.get('lon')

    # Salva la missione prima della modifica.
    _record_undo_state()

    # Crea il waypoint e lo aggiunge alla missione.
    # add_waypoint() aggiorna anche gli identificativi.
    wp_new = Waypoint(lat=lat, lon=lon)
    mission.add_waypoint(wp_new)

    print(f"Creating new waypoint {wp_new} with new coordinates: {lat}, {lon}")
    print_mission(mission)

    # Restituisce al browser la conferma dell'operazione.
    return jsonify({"status": "success", "message": f"Waypoint added successfully"}), 200


# Inserisce un waypoint in una posizione specifica del percorso.
@app.route('/add_waypoint_at', methods=['POST'])
def add_waypoint_at():
    data = request.get_json()
    lat = data.get('lat')
    lon = data.get('lon')

    # Indice della posizione in cui inserire il waypoint.
    index = data.get('index')

    _record_undo_state()

    wp_new = Waypoint(lat=lat, lon=lon)

    # A differenza di add_waypoint(), il nuovo punto viene
    # inserito nella posizione indicata dall'indice.
    mission.add_waypoint_at(wp_new, index)

    print(f"Creating new waypoint {wp_new} between with new coordinates: {lat}, {lon}")
    print_mission(mission)

    return jsonify({"status": "success", "message": f"Waypoint added successfully"}), 200


# Aggiorna le coordinate di un waypoint già esistente.
@app.route('/update_waypoint', methods=['POST'])
def update_waypoint():
    data = request.get_json()

    # ID del waypoint da modificare e nuove coordinate.
    waypoint_id = data.get('waypoint_id')
    lat = data.get('lat')
    lon = data.get('lon')

    _record_undo_state()

    # Recupera il waypoint dalla lista della missione
    # e richiama il metodo che aggiorna le coordinate.
    mission.waypoints[waypoint_id].update_waypoint_coordinates(lat, lon)

    print(f"Updating waypoint {waypoint_id} with new coordinates: {lat}, {lon}")
    print_mission(mission)

    return jsonify({"status": "success", "message": f"Waypoint updated successfully"}), 200


# Modifica un parametro di un'azione associata a un waypoint.
@app.route('/update_action', methods=['POST'])
def update_action():
    data = request.get_json()

    # Individua prima il waypoint e poi l'azione da modificare.
    waypoint_id = int(data.get('waypoint_id'))
    action_id = int(data.get('action_id'))

    # action_type contiene il nome del parametro da aggiornare,
    # mentre parameter contiene il nuovo valore.
    action_type = data.get('action_type')
    parameter = data.get('parameter')

    _record_undo_state()

    # La modifica viene effettuata dal metodo della classe Waypoint.
    mission.waypoints[waypoint_id].update_waypoint_action(action_id, action_type, parameter)

    print(f"Updating action {action_type} on waypoint {waypoint_id} with new value: {parameter}")
    print_mission(mission)

    return jsonify({"status": "success", "message": f"Waypoint updated successfully"}), 200


# Aggiorna uno dei parametri globali della missione.
@app.route('/update_global_parameter', methods=['POST'])
def update_global_parameter():
    data = request.get_json()

    # Nome del parametro da modificare e nuovo valore.
    variable = data.get('variable')
    value = int(data.get('value'))

    # In base al nome ricevuto viene aggiornata la proprietà
    # corrispondente dell'oggetto Mission.
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


# Elimina un waypoint dalla missione.
@app.route('/remove_waypoint', methods=['POST'])
def remove_waypoint():
    data = request.get_json()
    waypoint_id = data.get('waypoint_id')

    _record_undo_state()

    # remove_waypoint() elimina il punto e aggiorna gli ID
    # dei waypoint rimasti.
    mission.remove_waypoint(waypoint_id)

    print(f"Removing waypoint {waypoint_id}")
    print_mission(mission)

    return jsonify({"status": "success", "message": f"Waypoint removed successfully"}), 200


# Aggiunge un'azione a un waypoint esistente.
@app.route('/add_action', methods=['POST'])
def add_action():
    data = request.get_json()

    waypoint_id = data.get('waypoint_id')
    action_type = data.get('action_type')

    # Dizionario dei parametri dell'azione.
    # Se non è presente, viene utilizzato un dizionario vuoto.
    parameters = data.get('parameters', {})

    _record_undo_state()

    # **parameters espande il dizionario in argomenti con nome
    # da passare al costruttore di Action.
    action = Action(action_type, **parameters)

    # Inserisce l'azione nel waypoint indicato.
    mission.add_action(waypoint_id, action)

    print(f"Adding action to waypoint {waypoint_id}")
    print_mission(mission)

    return jsonify({"status": "success", "message": f"Action added successfully"}), 200


# Rimuove un'azione da un waypoint.
@app.route('/remove_action', methods=['POST'])
def remove_action():
    data = request.get_json()

    waypoint_id = data.get('waypoint_id')
    action_id = data.get('action_id')

    _record_undo_state()

    # La classe Mission individua l'azione, la elimina
    # e aggiorna gli identificativi delle azioni rimanenti.
    mission.remove_action(waypoint_id, action_id)

    print(f"Removing action {waypoint_id} - {action_id}")
    print_mission(mission)

    return jsonify({"status": "success", "message": f"Waypoint removed successfully"}), 200


# Cambia l'ordine delle azioni di un waypoint.
@app.route('/reorder_actions', methods=['POST'])
def reorder_actions():
    data = request.get_json()

    waypoint_id = int(data.get('waypoint_id'))

    # Lista degli ID delle azioni nel nuovo ordine richiesto.
    ordered_action_ids = data.get('action_ids', [])

    # Controlla che l'ordine ricevuto sia una lista.
    if not isinstance(ordered_action_ids, list):
        return jsonify({"status": "error", "message": "action_ids must be a list"}), 400

    # Converte gli identificativi ricevuti in numeri interi.
    try:
        ordered_action_ids = [int(action_id) for action_id in ordered_action_ids]
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "action_ids must contain integers"}), 400

    # Verifica che l'ID del waypoint rientri negli indici disponibili.
    if waypoint_id < 0 or waypoint_id >= len(mission.waypoints):
        return jsonify({"status": "error", "message": "Invalid waypoint id"}), 400

    # Recupera gli ID delle azioni attualmente presenti nel waypoint.
    current_action_ids = [action.action_id for action in mission.waypoints[waypoint_id].actions]

    # Il numero di azioni deve rimanere invariato.
    if len(current_action_ids) != len(ordered_action_ids):
        return jsonify({"status": "error", "message": "Invalid action order length"}), 400

    # Controlla che il nuovo ordine contenga gli stessi ID.
    if set(current_action_ids) != set(ordered_action_ids):
        return jsonify({"status": "error", "message": "Invalid action order ids"}), 400

    _record_undo_state()

    # Riordina le azioni secondo la sequenza ricevuta.
    ok = mission.reorder_actions(waypoint_id, ordered_action_ids)

    if not ok:
        return jsonify({"status": "error", "message": "Invalid action order"}), 400

    print(f"Reordered actions on waypoint {waypoint_id}: {ordered_action_ids}")
    print_mission(mission)

    return jsonify({"status": "success", "message": "Actions reordered successfully"}), 200


# Annulla l'ultima modifica effettuata alla missione.
@app.route('/undo', methods=['POST'])
def undo():
    # Se non ci sono stati precedenti non è possibile annullare nulla.
    if len(undo_stack) == 0:
        return jsonify({"status": "error", "message": "Nothing to undo"}), 400

    # Salva lo stato corrente nello stack Redo, così da poterlo ripristinare.
    redo_stack.append(_snapshot_current_mission())

    # Recupera e rimuove l'ultimo stato salvato nello stack Undo.
    snapshot = undo_stack.pop()

    # Ricostruisce la missione a partire dallo stato recuperato.
    _restore_from_snapshot(snapshot)

    print("Undo applied")
    print_mission(mission)

    # Invia al frontend la missione aggiornata e indica
    # se sono ancora disponibili operazioni Undo e Redo.
    return jsonify({
        "status": "success",
        "message": "Undo applied successfully",
        "mission": mission.to_dict(),
        "canUndo": len(undo_stack) > 0,
        "canRedo": len(redo_stack) > 0
    }), 200


# Ripristina una modifica precedentemente annullata.
@app.route('/redo', methods=['POST'])
def redo():
    # Verifica che ci sia uno stato disponibile da ripristinare.
    if len(redo_stack) == 0:
        return jsonify({"status": "error", "message": "Nothing to redo"}), 400

    # Conserva lo stato corrente per poter tornare indietro.
    undo_stack.append(_snapshot_current_mission())

    # Recupera l'ultimo stato annullato.
    snapshot = redo_stack.pop()

    # Ripristina quello stato come missione corrente.
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


# Avvia il server Flask quando il file viene eseguito direttamente.
if __name__ == '__main__':
    app.run(debug=True)
