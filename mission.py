
from typing import List
from geopy.distance import geodesic


# Azioni che possono essere associate ai waypoint.
# Per ogni tipo di azione sono elencati i parametri richiesti.
# Questo dizionario viene utilizzato anche dal server per comunicare
# al frontend quali azioni è possibile aggiungere.
ACTIONS = {
    "takePhoto": {
        "parameters": ["payloadPositionIndex", "fileSuffix"]
    },
    "focus": {
        "parameters": ["payloadPositionIndex", "focusX", "focusY"]
    },
    "zoom": {
        "parameters": ["payloadPositionIndex", "focalLength"]
    },
    "gimbalRotate": {
        "parameters": ["payloadPositionIndex", "gimbalRotateMode", "gimbalPitchRotateEnable", "gimbalPitchRotateAngle",
                       "gimbalYawRotateEnable", "gimbalYawRotateAngle"]
    },
    "rotateYaw": {
        "parameters": ["aircraftHeading"]
    },
    "hover": {
        "parameters": ["hoverTime"]
    },
}


# Rappresenta una singola azione da eseguire in un waypoint.
class Action:
    def __init__(self, action_type: str, **kwargs):
        # L'ID viene assegnato successivamente dalla missione.
        self.action_id = None
        self.action_type = action_type

        # kwargs raccoglie i parametri dell'azione in un dizionario.
        # Ad esempio: Action("hover", hoverTime=5)
        # produce parameters = {"hoverTime": 5}.
        self.parameters = kwargs

    def to_dict(self):
        # Converte l'azione in un dizionario, utile per la
        # serializzazione JSON e la comunicazione con il frontend.
        return {
            'action_id': self.action_id,
            'action_type': self.action_type,
            'parameters': self.parameters
        }


# Rappresenta un punto della missione, identificato dalle sue coordinate.
# Ogni waypoint può contenere più azioni, eseguite nell'ordine della lista.
class Waypoint:
    def __init__(self, lat: float, lon: float):
        self.waypoint_id = None
        self.lat = lat
        self.lon = lon

        # Lista delle azioni associate al waypoint.
        # List[Action] indica che gli elementi previsti sono oggetti Action.
        self.actions: List[Action] = []

    def update_waypoint_coordinates(self, lat, lon):
        # Aggiorna le coordinate del waypoint esistente.
        self.lat = lat
        self.lon = lon

    def update_waypoint_action(self, action_id, action_type, parameter):
        # Modifica un parametro di un'azione già presente.
        # action_id viene usato come indice nella lista delle azioni.
        # action_type qui rappresenta la chiave del parametro da modificare,
        # non il tipo dell'azione (il nome è un po' fuorviante).
        self.actions[action_id].parameters[action_type] = parameter

    def add_action(self, action: Action):
        # Aggiunge l'azione in fondo alla lista.
        self.actions.append(action)

    def remove_action(self, action_id: int, mission):
        # Recupera l'azione dalla sua posizione e la rimuove.
        # Il parametro mission è presente nella firma, ma non viene usato.
        action = self.actions[action_id]
        self.actions.remove(action)

    def to_dict(self):
        # Serializza il waypoint, comprese tutte le sue azioni.
        # La list comprehension richiama to_dict() su ogni oggetto Action.
        return {
            'waypoint_id': self.waypoint_id,
            'lat': self.lat,
            'lon': self.lon,
            'actions': [action.to_dict() for action in self.actions]
        }


# Contiene i parametri generali della missione e la lista dei waypoint.
# Attualmente altezza e velocità sono globali: in seguito verranno
# introdotte quote per waypoint e velocità per tratto.
class Mission:
    def __init__(self, height: float, speed: float, payload_index: int):
        self.height = height
        self.speed = speed
        self.payload_index = payload_index

        # I waypoint vengono mantenuti nell'ordine di percorrenza.
        self.waypoints: List[Waypoint] = []

    def total_distance(self) -> float:
        # Calcola la lunghezza totale del percorso in metri.
        # Non considera le variazioni di quota, ma solo le coordinate
        # geografiche dei waypoint consecutivi.

        # Con meno di due waypoint non esiste un tratto da percorrere.
        if len(self.waypoints) < 2:
            return 0.0

        total = 0.0

        # Si ferma al penultimo waypoint per poter accedere a i+1.
        for i in range(len(self.waypoints) - 1):
            wp1 = (self.waypoints[i].lat, self.waypoints[i].lon)
            wp2 = (self.waypoints[i + 1].lat, self.waypoints[i + 1].lon)

            # geodesic calcola la distanza tra due coordinate geografiche.
            # .meters restituisce il risultato espresso in metri.
            total += geodesic(wp1, wp2).meters

        # Arrotonda la distanza totale a due cifre decimali.
        return round(total, 2)

    def total_time(self) -> float:
        # Stima la durata in secondi usando distanza / velocità.
        # Attualmente assume una velocità costante e non considera
        # le attese o i tempi necessari per eseguire le azioni.
        # Attenzione: con speed = 0 si verifica una divisione per zero.
        return round(self.total_distance() / self.speed, 2)

    def add_waypoint_at(self, waypoint: Waypoint, index):
        # Inserisce un waypoint in una posizione specifica della lista.
        # I waypoint successivi vengono spostati in avanti.
        self.waypoints.insert(index, waypoint)

        # Riassegna gli ID in base al nuovo ordine.
        self.update_ids()

    def add_waypoint(self, waypoint: Waypoint):
        # Aggiunge il waypoint alla fine della missione.
        self.waypoints.append(waypoint)
        self.update_ids()

    def remove_waypoint(self, waypoint_id: int):
        # Recupera il waypoint usando il suo ID come indice.
        waypoint = self.waypoints[waypoint_id]
        self.waypoints.remove(waypoint)

        # Aggiorna gli ID per evitare buchi nella numerazione.
        self.update_ids()

    def add_action(self, waypoint_id: int, action: Action):
        # Recupera il waypoint e aggiunge l'azione alla sua lista.
        waypoint = self.waypoints[waypoint_id]
        waypoint.actions.append(action)

        # Aggiorna gli identificativi delle azioni.
        self.update_ids()

    def remove_action(self, waypoint_id: int, action_id: int):
        waypoint = self.waypoints[waypoint_id]
        action_del = None

        # Cerca l'azione confrontando il suo ID con quello richiesto.
        for i, action in enumerate(waypoint.actions):
            if action.action_id == action_id:
                action_del = action
                break

        # Rimuove l'azione trovata e aggiorna la numerazione.
        # Se non viene trovata, remove(None) genera un errore.
        waypoint.actions.remove(action_del)
        self.update_ids()

    def reorder_actions(self, waypoint_id: int, ordered_action_ids: List[int]) -> bool:
        # Riordina le azioni di un waypoint secondo la lista di ID ricevuta.
        # Restituisce False se gli ID forniti non corrispondono
        # esattamente alle azioni presenti.

        waypoint = self.waypoints[waypoint_id]

        # Il nuovo ordine deve contenere lo stesso numero di azioni.
        if len(ordered_action_ids) != len(waypoint.actions):
            return False

        # Dizionario che associa ogni ID al rispettivo oggetto Action.
        # Serve a ricostruire la lista nel nuovo ordine.
        action_by_id = {action.action_id: action for action in waypoint.actions}

        # Controlla che non siano stati aggiunti o omessi ID.
        if set(action_by_id.keys()) != set(ordered_action_ids):
            return False

        # Ricostruisce la lista seguendo l'ordine degli ID ricevuti.
        waypoint.actions = [action_by_id[action_id] for action_id in ordered_action_ids]

        # Gli ID vengono poi riassegnati secondo le nuove posizioni.
        self.update_ids()
        return True

    def update_ids(self):
        # Riassegna gli identificativi di waypoint e azioni.
        # I waypoint sono numerati progressivamente da 0.
        # Anche le azioni partono da 0, separatamente per ogni waypoint.

        waypoint_id = 0

        for i, wp in enumerate(self.waypoints):
            action_id = 0

            wp.waypoint_id = waypoint_id
            waypoint_id += 1

            for j, action in enumerate(wp.actions):
                action.action_id = action_id
                action_id += 1

        # Gli indici i e j restituiti da enumerate() non vengono usati.

    def to_dict(self):
        # Converte la missione in un dizionario Python.
        # Ogni waypoint viene convertito richiamando il suo to_dict(),
        # che a sua volta serializza anche le azioni.
        # payloadIndex usa il nome previsto dal formato JSON del frontend.
        return {
            'height': self.height,
            'speed': self.speed,
            'payloadIndex': self.payload_index,
            'waypoints': [waypoint.to_dict() for waypoint in self.waypoints]
        }


def print_mission(mission: Mission):
    # Stampa in console i dati della missione.
    # Utile per il debug, senza modificare gli oggetti.

    print("-------------------------------")
    print(f"Mission Details:")
    print(f"  height: {mission.height}")
    print(f"  speed: {mission.speed}")
    print(f"  payload index: {mission.payload_index}")
    print(f"  waypoints:")

    # Scorre i waypoint nell'ordine della missione.
    for waypoint in mission.waypoints:
        print(f"    {waypoint.waypoint_id}: latitude: {waypoint.lat}, longitude: {waypoint.lon}")

        # Le azioni vengono stampate soltanto se presenti.
        if waypoint.actions:
            print(f"    actions:")
            for action in waypoint.actions:
                print(f"      {action.action_id}: {action.action_type}")

                # Stampa i parametri specifici dell'azione.
                for param, value in action.parameters.items():
                    print(f"        {param}: {value}")


def create_empty_mission():
    # Crea una missione senza waypoint e con parametri iniziali a zero.
    # La velocità dovrà essere impostata prima di calcolare total_time().
    return Mission(height=0, speed=0, payload_index=0)


def mission_from_dict(data):
    # Ricostruisce un oggetto Mission a partire da un dizionario.
    # È l'operazione inversa di to_dict() per i campi gestiti dal modello.
    # Sarà utile anche per convertire il JSON generato dall'LLM.

    # get() restituisce il valore della chiave, oppure quello predefinito.
    # float() e int() convertono i dati nei tipi richiesti.
    height = float(data.get('height', 0))
    speed = float(data.get('speed', 0))

    # Accetta sia payloadIndex sia payload_index.
    payload_index = int(data.get('payloadIndex', data.get('payload_index', 0)))

    # Crea inizialmente una missione senza waypoint.
    mission = Mission(height=height, speed=speed, payload_index=payload_index)

    # Se la chiave waypoints manca, viene utilizzata una lista vuota.
    for waypoint_data in data.get('waypoints', []):
        lat = float(waypoint_data.get('lat'))
        lon = float(waypoint_data.get('lon'))

        # Crea il waypoint con le coordinate recuperate dal dizionario.
        waypoint = Waypoint(lat=lat, lon=lon)

        # Ricostruisce le azioni eventualmente associate al waypoint.
        for action_data in waypoint_data.get('actions', []):
            action_type = action_data.get('action_type')
            parameters = action_data.get('parameters', {})

            # ** espande il dizionario in argomenti con nome.
            # Ad esempio {"hoverTime": 5} diventa hoverTime=5.
            waypoint.add_action(Action(action_type, **parameters))

        # Inserisce il waypoint, completo delle sue azioni, nella missione.
        mission.add_waypoint(waypoint)

    # Assicura che gli identificativi siano coerenti con l'ordine corrente.
    # add_waypoint() li aggiorna già, ma questa chiamata finale li riassegna.
    mission.update_ids()
    return mission


def create_mock_mission():
    # Crea una missione di esempio con quattro waypoint.
    # Utile per provare il planner e le funzioni di import/export KMZ
    # senza dover inserire manualmente ogni waypoint e azione.

    mission = Mission(height=10.0, speed=5.0, payload_index=0)

    # Primo waypoint: due rotazioni attorno all'asse verticale,
    # separate da un'attesa di 2 secondi.
    wp0 = Waypoint(lat=43.06229630922861, lon=12.549784090599045)
    wp0.add_action(Action("rotateYaw", aircraftHeading=-90))
    wp0.add_action(Action("hover", hoverTime=2))
    wp0.add_action(Action("rotateYaw", aircraftHeading=90))

    mission.add_waypoint(wp0)

    # Secondo waypoint: orientamento del gimbal, messa a fuoco,
    # zoom e scatto di una fotografia.
    wp1 = Waypoint(lat=43.063526959224724, lon=12.549784090599045)
    wp1.add_action(Action("gimbalRotate", gimbalRotateMode="absoluteAngle",
                          gimbalPitchRotateEnable=1, gimbalPitchRotateAngle=-20,
                          gimbalYawRotateEnable=1, gimbalYawRotateAngle=45,
                          payloadPositionIndex=0))
    wp1.add_action(Action("focus", focusX=0.5, focusY=0.5, payloadPositionIndex=0))
    wp1.add_action(Action("zoom", focalLength=123, payloadPositionIndex=0))
    wp1.add_action(Action("takePhoto", fileSuffix="azz", payloadPositionIndex=0))
    mission.add_waypoint(wp1)

    # Terzo waypoint: altra sequenza di rotazioni e attesa.
    wp2 = Waypoint(lat=43.063526959224724, lon=12.551495339950547)
    wp2.add_action(Action("rotateYaw", aircraftHeading=-45))
    wp2.add_action(Action("hover", hoverTime=2))
    wp2.add_action(Action("rotateYaw", aircraftHeading=45))
    mission.add_waypoint(wp2)

    # Quarto waypoint: nuova configurazione del gimbal,
    # messa a fuoco, zoom e fotografia.
    wp3 = Waypoint(lat=43.062241438908295, lon=12.551495339950547)
    wp3.add_action(Action("gimbalRotate", gimbalRotateMode="absoluteAngle",
                          gimbalPitchRotateEnable=1, gimbalPitchRotateAngle=20,
                          gimbalYawRotateEnable=1, gimbalYawRotateAngle=-45,
                          payloadPositionIndex=0))
    wp3.add_action(Action("focus", focusX=0.5, focusY=0.5, payloadPositionIndex=0))
    wp3.add_action(Action("zoom", focalLength=144, payloadPositionIndex=0))
    wp3.add_action(Action("takePhoto", fileSuffix="uhm", payloadPositionIndex=0))
    mission.add_waypoint(wp3)

    return mission
