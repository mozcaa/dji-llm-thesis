
# Prova LLM - Generazione missioni DJI: JSON oppure XML
# Le due pipeline condividono Ollama ma producono formati diversi prima di creare il KMZ.


import json
import math
import zipfile
from pathlib import Path

import requests
from geopy.distance import geodesic
from jsonschema import validate
from lxml import etree

from mission import mission_from_dict
from parser_xml import mission_to_kmz, write_pretty_xml


# Configurazione


OLLAMA_URL = "http://localhost:11434/api/generate"
MODELLO = "llama3.2"
OUT = Path("out")  # Cartella in cui salvare i file generati.

# URI dei due namespace usati nei file DJI: KML per i punti, WPML per i parametri del drone.
KML_NS = "http://www.opengis.net/kml/2.2"
WPML_NS = "http://www.dji.com/wpmz/1.0.3"
# None indica il namespace predefinito; "wpml" e il prefisso degli elementi DJI.
NSMAP = {None: KML_NS, "wpml": WPML_NS}

# Valori di configurazione di prova:
# verificare con il drone/payload reale.
DRONE_ENUM = 60
PAYLOAD_ENUM = 42
PAYLOAD_INDEX = 0
RTH_HEIGHT = 30
TAKEOFF_SECURITY_HEIGHT = 30

# Prompt comune per confrontare le due pipeline sulla stessa missione.
PROMPT_PROVA = ("""
 Genera una missione drone con esattamente 8 waypoint.

 Usa queste coordinate nell'ordine:
 WP0 lat 43.10876 lon 12.38830;
 WP1 lat 43.10879 lon 12.38835;
 WP2 lat 43.10882 lon 12.38840;
 WP3 lat 43.10885 lon 12.38845;
 WP4 lat 43.10888 lon 12.38850;
 WP5 lat 43.10891 lon 12.38855;
 WP6 lat 43.10894 lon 12.38860;
 WP7 lat 43.10897 lon 12.38865.

 QUOTE E VELOCITA':
 - WP0: quota 10 metri, velocita' 20 m/s.
 - WP1: il doppio della quota e velocita' di WP0.
 - WP2: la meta' della quota e velocita' di WP0.
 - Da WP3 a WP7: il doppio della quota e velocita' di WP0.

 AZIONI:
 - WP0: hover di 5 secondi.
 - WP1: hover di 10 secondi.
 - WP2: hover di 15 secondi.
 - WP3: takePhoto con fileSuffix "jam".
 - WP4: focus con focusX 0.6 e focusY 0.7.
 - WP5: zoom con focalLength 2.
 - WP6: gimbalRotate con:
    gimbalRotateMode = absoluteAngle
    gimbalPitchRotateEnable = 0
    gimbalPitchRotateAngle = -6
    gimbalYawRotateEnable = 0
    gimbalYawRotateAngle = 60
 - WP7: due azioni:
    rotateYaw con aircraftHeading = 50
    zoom con focalLength = 2

 PARAMETRI PAYLOAD:
 - payloadIndex globale = 0.
 - Tutte le azioni hanno payloadPositionIndex = 2,
  tranne takePhoto che ha payloadPositionIndex = 1.
"""

)


# lxml identifica un tag con namespace tramite la forma {URI}nome.
def kml(nome):
    return f"{{{KML_NS}}}{nome}"


# Stessa cosa per i tag DJI, come wpml:waypointSpeed.
def wpml(nome):
    return f"{{{WPML_NS}}}{nome}"


# Aggiunge un figlio WPML a un elemento XML, scrivendone il valore come testo.
def aggiungi_wpml(genitore, nome, valore):
    elemento = etree.SubElement(genitore, wpml(nome))
    elemento.text = str(valore)
    return elemento


# Regole per le sei azioni
# Ogni azione ha parametri obbligatori e vincoli numerici o testuali.


ACTION_SCHEMAS_JSON = {
    "takePhoto": {
        "payloadPositionIndex": {"type": "integer", "enum": [0, 1, 2]},
        "fileSuffix": {"type": "string", "maxLength": 50},
    },

    "focus": {
        "payloadPositionIndex": {"type": "integer", "enum": [0, 1, 2]},
        "focusX": {"type": "number", "minimum": 0, "maximum": 1},
        "focusY": {"type": "number", "minimum": 0, "maximum": 1},
    },

    "zoom": {
        "payloadPositionIndex": {"type": "integer", "enum": [0, 1, 2]},
        "focalLength": {"type": "number", "exclusiveMinimum": 0},
    },

    "gimbalRotate": {
        "payloadPositionIndex": {"type": "integer", "enum": [0, 1, 2]},
        "gimbalRotateMode": {"type": "string", "enum": ["absoluteAngle"]},
        "gimbalPitchRotateEnable": {"type": "integer", "enum": [0, 1]},
        "gimbalPitchRotateAngle": {
            "type": "number", "minimum": -180, "maximum": 180
        },
        "gimbalYawRotateEnable": {"type": "integer", "enum": [0, 1]},
        "gimbalYawRotateAngle": {
            "type": "number", "minimum": -180, "maximum": 180
        },
    },

    "rotateYaw": {
        "aircraftHeading": {
            "type": "number", "minimum": -180, "maximum": 180
        },
    },

    "hover": {
        "hoverTime": {
            "type": "number",
            "exclusiveMinimum": 0,
            "maximum": 100000,
        },
    },
}


# Costruisce automaticamente le sei varianti dello schema JSON.
# "const" fissa il nome dell'azione; "required" richiede tutti i suoi parametri.
action_variants_json = []

for name, parameters in ACTION_SCHEMAS_JSON.items():
    action_variants_json.append({
        "type": "object",
        "properties": {
            "action_type": {"const": name},
            "parameters": {
                "type": "object",
                "properties": parameters,
                "required": list(parameters.keys()),  # Tutte le chiavi del dizionario sono obbligatorie.
                "additionalProperties": False,  # Non accetta parametri non previsti.
            },
        },
        "required": ["action_type", "parameters"],
        "additionalProperties": False,
    })


# "oneOf" richiede che ogni azione corrisponda esattamente a una variante.
SCHEMA_AZIONE = {
    "oneOf": action_variants_json
}


# Schema della missione JSON: payload e almeno un waypoint, ciascuno con le azioni.
MISSION_SCHEMA_JSON = {
    "type": "object",
    "properties": {
        "payloadIndex": {
            "type": "integer",
            "enum": [0, 1, 2],
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
                        "maximum": 90,
                    },

                    "lon": {
                        "type": "number",
                        "minimum": -180,
                        "maximum": 180,
                    },

                    "quote": {
                        "type": "number",
                        "minimum": 0.1,
                    },

                    "speed": {
                        "type": "number",
                        "minimum": 0.1,
                    },

                    "actions": {
                        "type": "array",
                        "items": SCHEMA_AZIONE,
                    },
                },

                "required": [
                    "lat", "lon", "quote", "speed", "actions"
                ],
                "additionalProperties": False,
            },
        },
    },

    "required": ["payloadIndex", "waypoints"],  # Campi obbligatori al livello della missione.
    "additionalProperties": False,
}


# Schema XSD per la struttura XML intermedia


# "Placemarks" è un contenitore temporaneo: permette a Llama di restituire
# più waypoint sotto un'unica radice XML. Non finisce nel KMZ finale.
# Lo XSD controlla i tag KML e richiede almeno due figli WPML per waypoint.
# xs:any con processContents="skip" non valida quei figli: se ne occupa Python.
# In XSD 1.0 non possiamo usare un oneOf basato sul testo di actionActuatorFunc.

MISSION_SCHEMA_XML = f"""\
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           targetNamespace="{KML_NS}"
           elementFormDefault="qualified">

  <xs:element name="Placemarks">
    <xs:complexType>
      <xs:sequence>

        <xs:element name="Placemark"
                    minOccurs="1"
                    maxOccurs="unbounded">

          <xs:complexType>
            <xs:sequence>

              <xs:element name="Point">
                <xs:complexType>
                  <xs:sequence>
                    <xs:element name="coordinates"
                                type="xs:string"/>
                  </xs:sequence>
                </xs:complexType>
              </xs:element>

              <xs:any namespace="{WPML_NS}"
                      minOccurs="2"
                      maxOccurs="unbounded"
                      processContents="skip"/>

            </xs:sequence>
          </xs:complexType>

        </xs:element>

      </xs:sequence>
    </xs:complexType>
  </xs:element>

</xs:schema>
"""


# Richiesta a Ollama

# Invia il prompt all'API locale di Ollama e restituisce il testo generato.
# "schema" serve solo per la generazione JSON vincolata: Ollama non accetta XSD.
def interroga_llama(prompt, schema=None):
    data = {
        "model": MODELLO,
        "prompt": prompt,
        "stream": False,  # Attende l'intera risposta, invece di riceverla a pezzi.
        "options": {"temperature": 0},  # Riduce la variabilità delle risposte.
    }

    if schema is not None:
        # Ollama accetta JSON Schema, non XSD.
        data["format"] = schema

    # La richiesta HTTP usa JSON anche se chiediamo a Llama di generare XML.
    response = requests.post(OLLAMA_URL, json=data, timeout=200)

    response.raise_for_status()  # Solleva un errore per risposte HTTP non riuscite.

    # response.json() legge il JSON dell'API,, ["response"] estrae solo il testo prodotto da Llama.
    return response.json()["response"]


# Pipeline JSON

# Esegue la pipeline JSON: genera dati strutturati, li valida e li passa al planner esistente.
def esegui_json():
    testo = interroga_llama(PROMPT_PROVA, MISSION_SCHEMA_JSON)

    mission_data = json.loads(testo)  # Trasforma la stringa JSON in dizionari/liste Python.

    validate(instance=mission_data, schema=MISSION_SCHEMA_JSON)  # Applica tutti i vincoli del JSON Schema.

    mission = mission_from_dict(mission_data)  # Ricostruisce l'oggetto Mission usato dal progetto.

    mission_to_kmz(mission, "mission_LLM_JSON")  # Esportazione tramite parser_xml.py.

    print("JSON strutturalmente valido.")
    print(json.dumps(mission.to_dict(), indent=4, ensure_ascii=False))

    print("KMZ creato: out/mission_LLM_JSON.kmz")


# Pipeline XML: istruzioni per Llama

# Nella pipeline XML lo schema XSD non può essere passato nel campo "format" di Ollama.
# Queste istruzioni spiegano al modello quali tag usare e gli mostrano un esempio.
# Le due variabili nella f-string inseriscono gli URI dei namespace.
PROMPT_XML = PROMPT_PROVA + f"""

Restituisci SOLO XML ben formato, senza testo introduttivo
e senza blocchi Markdown.

Genera esclusivamente gli elementi variabili dei waypoint.

La radice deve essere:

<Placemarks xmlns="{KML_NS}"
            xmlns:wpml="{WPML_NS}">

Ogni Placemark deve contenere ESATTAMENTE, in quest'ordine:

1) Point/coordinates (ordine longitudine,latitudine) 
2) wpml:executeHeight
3) wpml:waypointSpeed
4) zero o piu' wpml:action

Ogni wpml:action deve contenere:
- wpml:actionActuatorFunc (tipo di azione, senza prefisso)
- wpml:actionActuatorFuncParam con i parametri dell'azione

I tipi di azione e i parametri ammessi sono:

- takePhoto: payloadPositionIndex (0,1,2), fileSuffix (stringa)
- focus: payloadPositionIndex (0,1,2), focusX e focusY (0..1)
- zoom: payloadPositionIndex (0,1,2), focalLength (>0)
- gimbalRotate: payloadPositionIndex (0,1,2),
  gimbalRotateMode (absoluteAngle), gimbalPitchRotateEnable (0,1),
  gimbalPitchRotateAngle (-180..180), gimbalYawRotateEnable (0,1),
  gimbalYawRotateAngle (-180..180)
- rotateYaw: aircraftHeading (-180..180)
- hover: hoverTime (>0, <=100000)

Esempio di riferimento di un singolo Placemark:

<Placemark>
  <Point>
    <coordinates>12.38830,43.10876</coordinates>
  </Point>

  <wpml:executeHeight>10</wpml:executeHeight>
  <wpml:waypointSpeed>20</wpml:waypointSpeed>

  <wpml:action>
    <wpml:actionActuatorFunc>hover</wpml:actionActuatorFunc>
    <wpml:actionActuatorFuncParam>
      <wpml:hoverTime>5</wpml:hoverTime>
    </wpml:actionActuatorFuncParam>
  </wpml:action>

  <wpml:action>
    <wpml:actionActuatorFunc>gimbalRotate</wpml:actionActuatorFunc>
    <wpml:actionActuatorFuncParam>
      <wpml:payloadPositionIndex>2</wpml:payloadPositionIndex>
      <wpml:gimbalRotateMode>absoluteAngle</wpml:gimbalRotateMode>
      <wpml:gimbalPitchRotateEnable>0</wpml:gimbalPitchRotateEnable>
      <wpml:gimbalPitchRotateAngle>-4</wpml:gimbalPitchRotateAngle>
      <wpml:gimbalYawRotateEnable>0</wpml:gimbalYawRotateEnable>
      <wpml:gimbalYawRotateAngle>60</wpml:gimbalYawRotateAngle>
    </wpml:actionActuatorFuncParam>
  </wpml:action>
</Placemark>

NON generare:
kml, Document, Folder, missionConfig,
index, actionGroup, actionId, waypointHeadingParam,
waypointTurnParam oppure useStraightLine.

Questi elementi vengono inseriti da Python.

Chiudi correttamente Placemarks.
"""


# Pipeline XML: lettura e validazione

# Converte una stringa in float, rifiutando anche inf e nan (che float accetterebbe).
def numero_finito(testo):
    numero = float(testo)

    if not math.isfinite(numero):
        raise ValueError(f"Numero non finito: {testo}")

    return numero


# Legge un singolo wpml:action generato da Llama e controlla i suoi parametri.
# Restituisce un dizionario Python, non un nuovo elemento XML.
def leggi_azione(elemento):
    figli = list(elemento)  # Solo i figli diretti di wpml:action.

    # L'azione deve contenere esattamente questi due tag, nell'ordine indicato.
    if [x.tag for x in figli] != [
        wpml("actionActuatorFunc"),
        wpml("actionActuatorFuncParam")
    ]:
        raise ValueError("Struttura wpml:action non valida")

    tipo = (figli[0].text or "").strip()  # Elimina spazi e gestisce un testo eventualmente assente.

    if tipo not in ACTION_SCHEMAS_JSON:
        raise ValueError(f'Azione sconosciuta: {tipo}')

    specifiche = ACTION_SCHEMAS_JSON[tipo]  # Prende le regole del tipo di azione trovato.
    parametri = {}

    for p in figli[1]:
        nome = etree.QName(p).localname  # Estrae hoverTime da {URI}hoverTime.

        # Verifica sia il namespace DJI, sia che il parametro appartenga a questa azione.
        if p.tag != wpml(nome) or nome not in specifiche:
            raise ValueError(f'Parametro non previsto per {tipo}: {nome}')

        # Rifiuta ripetizioni e parametri che contengono altri elementi XML.
        if nome in parametri or len(p) > 0:
            raise ValueError(f'Parametro duplicato o annidato: {nome}')

        testo = (p.text or "").strip()
        tipo_previsto = specifiche[nome]["type"]  # Nel testo XML anche i numeri arrivano come stringhe.

        if tipo_previsto == "integer":
            valore = int(testo)

        elif tipo_previsto == "number":
            valore = numero_finito(testo)

        else:
            valore = testo

        parametri[nome] = valore

    azione = {
        "action_type": tipo,
        "parameters": parametri
    }

    # Riutilizza il JSON Schema per controllare valori, intervalli e campi obbligatori
    # anche nella pipeline XML (lo XSD, da solo, non verifica questi parametri).
    validate(instance=azione, schema=SCHEMA_AZIONE)

    return azione


# Interpreta l'XML intermedio, verifica la struttura ed estrae tutti i waypoint.
# Ritorna una lista di dizionari con lat, lon, quota, velocità e azioni.
def leggi_placemarks(xml_generato):

    xml_generato= xml_generato.strip()

    if( xml_generato.startswith("```")):
     xml_generato= xml_generato.split("\n",1)[1]
     xml_generato = xml_generato.rsplit("```",1)[0]



    # Disabilita entità esterne e accesso alla rete durante la lettura dell'XML.
    parser = etree.XMLParser(resolve_entities=False, no_network=True)

    # fromstring() legge la stringa XML (qui convertita in byte) e restituisce la radice dell'albero.
    root = etree.fromstring(xml_generato.encode("utf-8"), parser)

    # Interpreta anche il testo dello XSD e lo trasforma in un validatore.
    xsd = etree.XMLSchema(etree.fromstring(MISSION_SCHEMA_XML.encode("utf-8")))

    xsd.assertValid(root)  # Interrompe l'esecuzione se la struttura non rispetta lo XSD.

    waypoints = []

    # findall() cerca tutti i Placemark figli della radice, con namespace KML.
    for placemark in root.findall(kml("Placemark")):
        figli = list(placemark)  # Point, executeHeight, waypointSpeed e le eventuali azioni.

        # Controlla i primi tre figli: lo slice [:3] esclude le azioni successive.
        if [x.tag for x in figli[:3]] != [
            kml("Point"),
            wpml("executeHeight"),
            wpml("waypointSpeed")
        ]:
            raise ValueError("Ordine dei campi del Placemark non valido")

        # any() rileva se almeno uno degli elementi rimasti non è un’azione.
        if any(x.tag != wpml("action") for x in figli[3:]):
            raise ValueError("Elemento non ammesso nel Placemark")

        # Le coordinate XML sono nell'ordine lon,lat.
        coord = figli[0].find(kml("coordinates")).text
        parti = coord.split(",")  # Divide "longitudine,latitudine" in due stringhe.
        if len(parti) != 2:
            while (len(parti)> 2):
             parti.pop()

        if len(parti) != 2:
            raise ValueError("Coordinate attese nel formato lon,lat")

        # Converte entrambe le coordinate in numeri, scartando inf e nan.
        lon, lat = [numero_finito(x.strip()) for x in parti]

        quota = numero_finito((figli[1].text or "").strip())

        speed = numero_finito((figli[2].text or "").strip())

        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError("Coordinate fuori intervallo")

        if quota < 0.1 or speed < 0.1:
            raise ValueError("Quota e velocita' devono essere >= 0.1")

        # Legge e valida ogni azione del waypoint usando la funzione precedente.
        azioni = [leggi_azione(a) for a in figli[3:]]

        # Aggiunge il waypoint alla lista, senza conservare il contenitore XML Placemarks.
        waypoints.append({"lat": lat, "lon": lon, "quote": quota, "speed": speed, "actions": azioni})

    return waypoints


# Pipeline XML: assemblaggio WPML

# Stima la distanza orizzontale totale e il tempo di percorrenza, sommando gli hover.
# È una stima semplificata: non include tutte le fasi operative del drone.
def calcola_distanza_e_durata(waypoints):
    distanza_totale = 0.0
    durata_totale = 0.0

    # Ogni coppia di waypoint consecutivi definisce un tratto.
    for i in range(len(waypoints) - 1):
        a = waypoints[i]
        b = waypoints[i + 1]

        # geodesic() misura la distanza sulla superficie terrestre, in metri.
        distanza_orizzontale = geodesic((a["lat"], a["lon"]), (b["lat"], b["lon"])).meters

        differenza_quota = b["quote"] - a["quote"]

        # hypot() calcola la diagonale 3D del tratto considerando la differenza di quota.
        distanza_3d = math.hypot(distanza_orizzontale, differenza_quota)

        distanza_totale += distanza_orizzontale
        durata_totale += distanza_3d / a["speed"]  # Usa la velocità impostata nel waypoint di partenza.

    # Aggiunge i tempi di attesa richiesti.
    for wp in waypoints:
        for action in wp["actions"]:
            if action["action_type"] == "hover":
                durata_totale += action["parameters"]["hoverTime"]

    return (round(distanza_totale, 2), round(durata_totale, 2))


# Costruisce manualmente il WPML definitivo dai waypoint già letti e validati.
# Aggiunge gli elementi fissi che Llama non genera, salva i due XML e crea il KMZ.
def crea_kmz_xml(waypoints, nome="mission_LLM_XML"):
    OUT.mkdir(exist_ok=True)
    cartella = OUT / "wpmz"  # La struttura interna del KMZ deve avere la cartella wpmz/.
    cartella.mkdir(parents=True, exist_ok=True)

    # Element() crea la radice <kml>; SubElement() aggiunge i figli al documento.
    # nsmap serve a dichiarare i namespace KML e WPML nella serializzazione.
    kml_root = etree.Element(kml("kml"), nsmap=NSMAP)
    documento = etree.SubElement(kml_root, kml("Document"))

    # Configurazione generale: valori fissati da Python e non generati da Llama.
    config = etree.SubElement(documento, wpml("missionConfig"))
    aggiungi_wpml(config, "globalRTHHeight", RTH_HEIGHT)
    aggiungi_wpml(config, "flyToWaylineMode", "safely")
    aggiungi_wpml(config, "finishAction", "goHome")  # Comportamento previsto a fine missione.
    aggiungi_wpml(config, "exitOnRCLost", "executeLostAction")
    aggiungi_wpml(config, "executeRCLostAction", "hover")  # Azione configurata in caso di link perso.
    aggiungi_wpml(config, "takeOffSecurityHeight", TAKEOFF_SECURITY_HEIGHT)

    # Usa la velocità del primo waypoint per il campo globale di transizione.
    aggiungi_wpml(config, "globalTransitionalSpeed", waypoints[0]["speed"])

    # Identificativi del drone e del payload: per ora sono costanti di prova.
    drone_info = etree.SubElement(config, wpml("droneInfo"))
    aggiungi_wpml(drone_info, "droneEnumValue", DRONE_ENUM)
    payload_info = etree.SubElement(config, wpml("payloadInfo"))
    aggiungi_wpml(payload_info, "payloadEnumValue", PAYLOAD_ENUM)
    aggiungi_wpml(payload_info, "payloadPositionIndex", PAYLOAD_INDEX)

    # Folder contiene i dati generali della wayline e tutti i Placemark.
    folder = etree.SubElement(documento, kml("Folder"))
    distanza, durata = calcola_distanza_e_durata(waypoints)  # Valori stimati dai tratti e dagli hover.
    aggiungi_wpml(folder, "templateId", 0)
    aggiungi_wpml(folder, "executeHeightMode", "relativeToStartPoint")
    aggiungi_wpml(folder, "waylineId", 0)
    aggiungi_wpml(folder, "distance", distanza)
    aggiungi_wpml(folder, "duration", durata)
    aggiungi_wpml(folder, "autoFlightSpeed", waypoints[0]["speed"])

    # enumerate() fornisce sia il waypoint sia il suo indice, che scriviamo nel WPML.
    # Le coordinate restano nel formato KML: longitudine,latitudine.
    for i, wp in enumerate(waypoints):
        placemark = etree.SubElement(folder, kml("Placemark"))
        point = etree.SubElement(placemark, kml("Point"))
        etree.SubElement(point, kml("coordinates")).text = f'{wp["lon"]},{wp["lat"]}'
        aggiungi_wpml(placemark, "index", i)
        aggiungi_wpml(placemark, "executeHeight", wp["quote"])
        aggiungi_wpml(placemark, "waypointSpeed", wp["speed"])

        # Parametri fissi per orientamento e svolta del drone al waypoint.
        heading = etree.SubElement(placemark, wpml("waypointHeadingParam"))
        aggiungi_wpml(heading, "waypointHeadingMode", "followWayline")
        turn = etree.SubElement(placemark, wpml("waypointTurnParam"))
        aggiungi_wpml(turn, "waypointTurnMode", "toPointAndStopWithDiscontinuityCurvature")
        aggiungi_wpml(turn, "waypointTurnDampingDist", 0)
        aggiungi_wpml(placemark, "useStraightLine", 1)

        # Ogni waypoint con azioni riceve un gruppo attivato al raggiungimento del punto.
        if wp["actions"]:
            gruppo = etree.SubElement(placemark, wpml("actionGroup"))
            aggiungi_wpml(gruppo, "actionGroupId", i)
            aggiungi_wpml(gruppo, "actionGroupStartIndex", i)
            aggiungi_wpml(gruppo, "actionGroupEndIndex", i)
            aggiungi_wpml(gruppo, "actionGroupMode", "sequence")
            trigger = etree.SubElement(gruppo, wpml("actionTrigger"))
            aggiungi_wpml(trigger, "actionTriggerType", "reachPoint")

            # enumerate() assegna a ogni azione un ID locale al gruppo, a partire da zero.
            for j, action in enumerate(wp["actions"]):
                elemento = etree.SubElement(gruppo, wpml("action"))
                aggiungi_wpml(elemento, "actionId", j)
                aggiungi_wpml(elemento, "actionActuatorFunc", action["action_type"])

                # Scrive i parametri già validati come tag WPML, senza inventare altri valori.
                params_xml = etree.SubElement(elemento, wpml("actionActuatorFuncParam"))

                for parametro, valore in action["parameters"].items():
                    aggiungi_wpml(params_xml, parametro, valore)

    # Serializza l'albero XML completo nel documento waylines.wpml.
    write_pretty_xml(kml_root, str(cartella / "waylines.wpml"))

    # Crea il secondo documento richiesto dalla struttura KMZ, qui minimale.
    template = etree.Element(kml("kml"), nsmap=NSMAP)
    etree.SubElement(template, kml("Document"))
    write_pretty_xml(template, str(cartella / "template.kml"))

    # Il KMZ è un archivio ZIP: arcname definisce i percorsi interni all'archivio.
    percorso = OUT / f"{nome}.kmz"

    # "w" crea/sovrascrive l'archivio; ZIP_DEFLATED ne abilita la compressione.
    with zipfile.ZipFile(percorso, "w", zipfile.ZIP_DEFLATED) as archivio:
        for file in ("template.kml", "waylines.wpml"):
            archivio.write(cartella / file, arcname=f'wpmz/{file}')

    return percorso  # Restituisce il Path del KMZ, non il suo contenuto.


# Esecuzione della pipeline XML

# Coordina la pipeline XML: richiesta a Llama, validazione, stampa ed esportazione.
def esegui_xml():
    # Qui NON passiamo format=XSD.
    xml_generato = interroga_llama(PROMPT_XML)  # Una stringa XML dentro la risposta JSON dell'API.

    print("Risposta XML di Llama:")
    print(xml_generato)

    waypoints = leggi_placemarks(xml_generato)  # Converte l'XML in dati Python validati.

    print("XML ben formato, struttura e parametri validati.")

    for i, wp in enumerate(waypoints):
        print(f'WP{i}: {wp["lat"]}, {wp["lon"]}, quota={wp["quote"]}, speed={wp["speed"]}')

        for j, azione in enumerate(wp["actions"]):
            print(f'  Azione {j}: {azione["action_type"]}, {azione["parameters"]}')

    percorso = crea_kmz_xml(waypoints)  # Completa il WPML e comprime i file in KMZ.

    print(f"KMZ creato: {percorso}")


# Avvio del programma

# Questo blocco parte solo eseguendo direttamente il file, non quando viene importato.
if __name__ == "__main__":
    scelta = input("Pipeline JSON (0) oppure XML (1)? ").strip()  # input() restituisce testo.

    if scelta == "0":
        esegui_json()

    elif scelta == "1":
        esegui_xml()

    else:
        print("Scelta non valida: inserisci 0 oppure 1.")
