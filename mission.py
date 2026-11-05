
from typing import List
from geopy.distance import geodesic
import math


# Azioni disponibili e relativi parametri, condivisi con il frontend tramite il server.
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


# Rappresenta una singola azione associata a un waypoint.
class Action:
    def __init__(self, action_type: str, **kwargs):
        self.action_id = None                  # L'ID viene assegnato dalla missione.
        self.action_type = action_type
        self.parameters = kwargs               # Es.: hoverTime=2 diventa {"hoverTime": 2}.

    # Converte l'azione in un dizionario da usare nel JSON della missione.
    def to_dict(self):
        return {
            'action_id': self.action_id,
            'action_type': self.action_type,
            'parameters': self.parameters
        }


# Rappresenta un waypoint e le azioni da eseguire al suo raggiungimento.
# La velocità del waypoint vale per il tratto verso quello successivo.
class Waypoint:
    def __init__(self, lat: float, lon: float, speed: float = 5.0, quote: float = 10.0):
        self.waypoint_id = None
        self.lat = lat
        self.lon = lon
        self.speed = speed
        self.quote = quote
        self.actions: List[Action] = []        # Le azioni vengono mantenute in ordine.

    # Modifica le coordinate del waypoint.
    def update_waypoint_coordinates(self, lat, lon):
        self.lat = lat
        self.lon = lon

    # Modifica la velocità sul tratto che parte da questo waypoint.
    def update_waypoint_speed(self, speed):
        self.speed = speed

    # Modifica la quota del waypoint.
    def update_waypoint_quote(self, quote):
        self.quote = quote

    # Aggiorna un parametro di un'azione esistente.
    def update_waypoint_action(self, action_id, action_type, parameter):
        self.actions[action_id].parameters[action_type] = parameter  # action_type è la chiave del parametro.

    # Aggiunge un'azione alla fine della lista.
    def add_action(self, action: Action):
        self.actions.append(action)

    # Rimuove l'azione indicata dalla sua posizione nella lista.
    def remove_action(self, action_id: int, mission):
        action = self.actions[action_id]
        self.actions.remove(action)

    # Converte il waypoint, comprese le sue azioni, in un dizionario.
    def to_dict(self):
        return {
            'waypoint_id': self.waypoint_id,
            'lat': self.lat,
            'lon': self.lon,
            'speed': self.speed,
            'quote': self.quote,
            'actions': [action.to_dict() for action in self.actions]
        }


# Contiene il payload e i waypoint ordinati della missione.
class Mission:
    def __init__(self, payload_index: int):
        self.payload_index = payload_index
        self.waypoints: List[Waypoint] = []

    # Somma le distanze orizzontali tra waypoint consecutivi, in metri.
    def total_distance(self) -> float:
        if len(self.waypoints) < 2:
            return 0.0

        total = 0.0
        for i in range(len(self.waypoints) - 1):
            wp1 = (self.waypoints[i].lat, self.waypoints[i].lon)
            wp2 = (self.waypoints[i + 1].lat, self.waypoints[i + 1].lon)
            total += geodesic(wp1, wp2).meters  # Distanza geografica, senza differenza di quota.

        return round(total, 2)

    # Stima il tempo di volo sommando i tempi dei singoli tratti tridimensionali.
    def total_time(self) -> float:
        total = 0.0

        for i in range(len(self.waypoints) - 1):
            wp1 = (self.waypoints[i].lat, self.waypoints[i].lon)
            wp2 = (self.waypoints[i + 1].lat, self.waypoints[i + 1].lon)

            distanceX = geodesic(wp1, wp2).meters                       # Distanza orizzontale in metri.
            distanceY = abs(self.waypoints[i].quote - self.waypoints[i + 1].quote)  # Differenza di quota in metri.
            distance = math.sqrt(distanceX**2 + distanceY**2)          # Lunghezza del tratto nello spazio.

            speed = self.waypoints[i].speed                             # Velocità del waypoint di partenza.

            if speed <= 0:
                raise ValueError("La velocità del tratto deve essere positiva")

            total += distance / speed

        return round(total, 2)

    # Inserisce un waypoint nella posizione indicata.
    def add_waypoint_at(self, waypoint: Waypoint, index):
        self.waypoints.insert(index, waypoint)
        self.update_ids()

    # Aggiunge un waypoint alla fine del percorso.
    def add_waypoint(self, waypoint: Waypoint):
        self.waypoints.append(waypoint)
        self.update_ids()

    # Elimina un waypoint e aggiorna gli identificativi.
    def remove_waypoint(self, waypoint_id: int):
        waypoint = self.waypoints[waypoint_id]
        self.waypoints.remove(waypoint)
        self.update_ids()

    # Aggiunge un'azione al waypoint indicato.
    def add_action(self, waypoint_id: int, action: Action):
        waypoint = self.waypoints[waypoint_id]
        waypoint.actions.append(action)
        self.update_ids()

    # Cerca un'azione tramite ID, la rimuove e aggiorna la numerazione.
    def remove_action(self, waypoint_id: int, action_id: int):
        waypoint = self.waypoints[waypoint_id]
        action_del = None

        for i, action in enumerate(waypoint.actions):
            if action.action_id == action_id:
                action_del = action
                break

        waypoint.actions.remove(action_del)
        self.update_ids()

    # Riordina le azioni del waypoint secondo la sequenza di ID ricevuta.
    def reorder_actions(self, waypoint_id: int, ordered_action_ids: List[int]) -> bool:
        waypoint = self.waypoints[waypoint_id]

        if len(ordered_action_ids) != len(waypoint.actions):
            return False

        action_by_id = {action.action_id: action for action in waypoint.actions}  # Associa ogni ID al relativo oggetto.

        if set(action_by_id.keys()) != set(ordered_action_ids):
            return False

        waypoint.actions = [action_by_id[action_id] for action_id in ordered_action_ids]
        self.update_ids()
        return True

    # Riassegna gli ID dei waypoint e, per ciascuno, quelli delle azioni.
    def update_ids(self):
        waypoint_id = 0

        for i, wp in enumerate(self.waypoints):
            action_id = 0            # Ogni waypoint riparte dall'azione 0.
            wp.waypoint_id = waypoint_id
            waypoint_id += 1

            for j, action in enumerate(wp.actions):
                action.action_id = action_id
                action_id += 1

    # Converte la missione e tutti i suoi waypoint in un dizionario.
    def to_dict(self):
        return {
            'payloadIndex': self.payload_index,
            'waypoints': [waypoint.to_dict() for waypoint in self.waypoints]
        }


# Stampa la missione in console, comprese quote, velocità e azioni.
def print_mission(mission: Mission):
    print("-------------------------------")
    print("Mission Details:")
    print(f"  payload index: {mission.payload_index}")
    print("  waypoints:")

    for waypoint in mission.waypoints:
        print(f"{waypoint.waypoint_id}: latitude: {waypoint.lat}, longitude: {waypoint.lon}, "
              f"quote: {waypoint.quote}, speed: {waypoint.speed}")

        if waypoint.actions:
            print("    actions:")
            for action in waypoint.actions:
                print(f"{action.action_id}: {action.action_type}")

                for param, value in action.parameters.items():
                    print(f"{param}: {value}")


# Crea una missione vuota, senza waypoint.
def create_empty_mission():
    return Mission(payload_index=0)


# Ricostruisce la missione da un dizionario, per esempio dopo Undo o caricamento JSON.
def mission_from_dict(data):
    payload_index = int(data.get('payloadIndex', data.get('payload_index', 0)))
    mission = Mission(payload_index=payload_index)

    default_speed = float(data.get('speed', 5.0))     # Compatibilità con il vecchio JSON a parametri globali.
    default_quote = float(data.get('height', 10.0))   # Usati se il waypoint non specifica valori propri.

    for waypoint_data in data.get('waypoints', []):
        lat = float(waypoint_data.get('lat'))
        lon = float(waypoint_data.get('lon'))
        speed = float(waypoint_data.get('speed', default_speed))
        quote = float(waypoint_data.get('quote', default_quote))

        waypoint = Waypoint(lat=lat, lon=lon, speed=speed, quote=quote)

        for action_data in waypoint_data.get('actions', []):
            action_type = action_data.get('action_type')
            parameters = action_data.get('parameters', {})
            waypoint.add_action(Action(action_type, **parameters))  # ** espande il dizionario nei parametri dell'azione.

        mission.add_waypoint(waypoint)

    mission.update_ids()
    return mission


# Crea una missione di esempio con quattro waypoint e alcune azioni.
def create_mock_mission():
    mission = Mission(payload_index=0)

    wp0 = Waypoint(lat=43.06229630922861, lon=12.549784090599045, speed=5.0, quote=10.0)
    wp0.add_action(Action("rotateYaw", aircraftHeading=-90))
    wp0.add_action(Action("hover", hoverTime=2))
    wp0.add_action(Action("rotateYaw", aircraftHeading=90))
    mission.add_waypoint(wp0)

    wp1 = Waypoint(lat=43.063526959224724, lon=12.549784090599045, speed=5.0, quote=10.0)
    wp1.add_action(Action("gimbalRotate", gimbalRotateMode="absoluteAngle",
                          gimbalPitchRotateEnable=1, gimbalPitchRotateAngle=-20,
                          gimbalYawRotateEnable=1, gimbalYawRotateAngle=45,
                          payloadPositionIndex=0))
    wp1.add_action(Action("focus", focusX=0.5, focusY=0.5, payloadPositionIndex=0))
    wp1.add_action(Action("zoom", focalLength=123, payloadPositionIndex=0))
    wp1.add_action(Action("takePhoto", fileSuffix="azz", payloadPositionIndex=0))
    mission.add_waypoint(wp1)

    wp2 = Waypoint(lat=43.063526959224724, lon=12.551495339950547, speed=5.0, quote=10.0)
    wp2.add_action(Action("rotateYaw", aircraftHeading=-45))
    wp2.add_action(Action("hover", hoverTime=2))
    wp2.add_action(Action("rotateYaw", aircraftHeading=45))
    mission.add_waypoint(wp2)

    wp3 = Waypoint(lat=43.062241438908295, lon=12.551495339950547, speed=5.0, quote=10.0)
    wp3.add_action(Action("gimbalRotate", gimbalRotateMode="absoluteAngle",
                          gimbalPitchRotateEnable=1, gimbalPitchRotateAngle=20,
                          gimbalYawRotateEnable=1, gimbalYawRotateAngle=-45,
                          payloadPositionIndex=0))
    wp3.add_action(Action("focus", focusX=0.5, focusY=0.5, payloadPositionIndex=0))
    wp3.add_action(Action("zoom", focalLength=144, payloadPositionIndex=0))
    wp3.add_action(Action("takePhoto", fileSuffix="uhm", payloadPositionIndex=0))
    mission.add_waypoint(wp3)

    return mission
