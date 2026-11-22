import requests
import json
from jsonschema import validate
from mission import mission_from_dict
from parser_xml import mission_to_kmz

# =========================
# JSON Schema - Missioni DJI
# =========================

# Definisce i parametri e i vincoli di ciascuna azione.
ACTION_SCHEMAS = {
    "takePhoto": {
        "payloadPositionIndex": {"type": "integer", "enum": [0, 1, 2]},
        "fileSuffix": {"type": "string", "maxLength": 50}
    },

    "focus": {
        "payloadPositionIndex": {"type": "integer", "enum": [0, 1, 2]},
        "focusX": {"type": "number", "minimum": 0, "maximum": 1},
        "focusY": {"type": "number", "minimum": 0, "maximum": 1}
    },

    "zoom": {
        "payloadPositionIndex": {"type": "integer", "enum": [0, 1, 2]},
        "focalLength": {"type": "number", "exclusiveMinimum": 0}
    },

    "gimbalRotate": {
        "payloadPositionIndex": {"type": "integer", "enum": [0, 1, 2]},
        "gimbalRotateMode": {"type": "string", "enum": ["absoluteAngle"]},
        "gimbalPitchRotateEnable": {"type": "integer", "enum": [0, 1]},
        "gimbalPitchRotateAngle": {"type": "number", "minimum": -180, "maximum": 180},
        "gimbalYawRotateEnable": {"type": "integer", "enum": [0, 1]},
        "gimbalYawRotateAngle": {"type": "number", "minimum": -180, "maximum": 180}
    },

    "rotateYaw": {
        "aircraftHeading": {"type": "number", "minimum": -180, "maximum": 180}
    },

    "hover": {
        "hoverTime": {"type": "number", "exclusiveMinimum": 0, "maximum": 100000}
    }
}


# Crea uno schema completo per ogni tipo di azione.
action_variants = []

for name, parameters in ACTION_SCHEMAS.items():
    action_variants.append({
        "type": "object",
        "properties": {
            "action_type": {"const": name},
            "parameters": {
                "type": "object",
                "properties": parameters,
                "required": list(parameters.keys()),
                "additionalProperties": False
            }
        },
        "required": ["action_type", "parameters"],
        "additionalProperties": False
    })


# Definisce la struttura completa della missione.
MISSION_SCHEMA = {
    "type": "object",
    "properties": {

        "payloadIndex": {
            "type": "integer",
            "enum": [0, 1, 2]
        },

        "waypoints": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {

                    "lat": {
                        "type": "number",
                        "minimum": -90,
                        "maximum": 90
                    },

                    "lon": {
                        "type": "number",
                        "minimum": -180,
                        "maximum": 180
                    },

                    "quote": {
                        "type": "number",
                        "minimum": 0.1
                    },

                    "speed": {
                        "type": "number",
                        "minimum": 0.1
                    },

                    "actions": {
                        "type": "array",
                        "items": {
                            "oneOf": action_variants
                        }
                    }
                },

                "required": ["lat", "lon", "quote", "speed", "actions"],
                "additionalProperties": False
            }
        }
    },

    "required": ["payloadIndex", "waypoints"],
    "additionalProperties": False
}


url = "http://localhost:11434/api/generate"

data = {
     "model": "llama3.2",
     "prompt": "Genera una missione drone con esattamente 3 waypoint. Usa queste coordinate, lat 43.10876 lon 12.38830,  lat 43.10879 lon 12.38835, lat 43.10882, lon 12.38840. Ogni waypoint deve avere stessa velocita' di 20 e stessa quota di 10. Ogni waypoint ha una sola azione, ovvero un Hover di 5 secondi per il primo waypoint, 10 per il secondo e 15 per il terzo. Il payload index è 0",
     "format": MISSION_SCHEMA,
     "stream": False     
}

response= requests.post( url, json=data, timeout=200)

response.raise_for_status()

result=response.json()

mission_data = json.loads(result["response"])

validate(instance=mission_data, schema=MISSION_SCHEMA)
print("JSON valido secondo lo schema!")

print(mission_data)
print(" ")

# Costruisce l'oggetto Mission e assegna gli ID.
mission = mission_from_dict(mission_data)
mission_to_kmz(mission,"mission_llm")

print(json.dumps(mission.to_dict(), indent=4)) # Converte l'oggetto Mission in un dizionario Python, poi lo serializza in una stringa JSON indentata e la stampa.
print(" ")

for i, wp in enumerate(mission_data["waypoints"]): #visualizzare piu' velocemente quello che creato per le azioni
    print(" ")
    print(f"WP{i}:")

    for j, action in enumerate(wp["actions"]):
        print(f" Azione numero: {j}, tipo: {action['action_type']}, parametri: {action['parameters']}")

print(" ")

print("KMZ generato!")

print(" ")