import requests
import os
import json
from jsonschema import validate
from mission import mission_from_dict
from parser_xml import mission_to_kmz, write_pretty_xml, create_kmz
from lxml import etree
import xml.etree.ElementTree as ET
from geopy.distance import geodesic
import math

namespaces = {
        None: 'http://www.opengis.net/kml/2.2',   # Namespace KML predefinito.
        'wpml': 'http://www.dji.com/wpmz/1.0.3'    # Namespace WPML specifico di DJI.
    }

kml_ns = namespaces[None]          # URI del namespace KML.
wpml_ns = namespaces['wpml']       # URI del namespace WPML.
# =========================
# XML Schema - Azioni DJI
# =========================

ACTION_SCHEMAS_XML = {
    "takePhoto":
        f'<xs:element name="{{{wpml_ns}}}payloadPositionIndex"><xs:simpleType><xs:restriction base="xs:integer"><xs:minInclusive value="0"/><xs:maxInclusive value="2"/></xs:restriction></xs:simpleType></xs:element>'
        f'<xs:element name="{{{wpml_ns}}}fileSuffix"><xs:simpleType><xs:restriction base="xs:string"><xs:maxLength value="50"/></xs:restriction></xs:simpleType></xs:element>',

    "focus":
        f'<xs:element name="{{{wpml_ns}}}payloadPositionIndex"><xs:simpleType><xs:restriction base="xs:integer"><xs:minInclusive value="0"/><xs:maxInclusive value="2"/></xs:restriction></xs:simpleType></xs:element>'
        f'<xs:element name="{{{wpml_ns}}}focusX"><xs:simpleType><xs:restriction base="xs:decimal"><xs:minInclusive value="0"/><xs:maxInclusive value="1"/></xs:restriction></xs:simpleType></xs:element>'
        f'<xs:element name="{{{wpml_ns}}}focusY"><xs:simpleType><xs:restriction base="xs:decimal"><xs:minInclusive value="0"/><xs:maxInclusive value="1"/></xs:restriction></xs:simpleType></xs:element>',

    "zoom":
        f'<xs:element name="{{{wpml_ns}}}payloadPositionIndex"><xs:simpleType><xs:restriction base="xs:integer"><xs:minInclusive value="0"/><xs:maxInclusive value="2"/></xs:restriction></xs:simpleType></xs:element>'
        f'<xs:element name="{{{wpml_ns}}}focalLength"><xs:simpleType><xs:restriction base="xs:decimal"><xs:minExclusive value="0"/></xs:restriction></xs:simpleType></xs:element>',

    "gimbalRotate":
        f'<xs:element name="{{{wpml_ns}}}payloadPositionIndex"><xs:simpleType><xs:restriction base="xs:integer"><xs:minInclusive value="0"/><xs:maxInclusive value="2"/></xs:restriction></xs:simpleType></xs:element>'
        f'<xs:element name="{{{wpml_ns}}}gimbalRotateMode" type="xs:string" fixed="absoluteAngle"/>'
        f'<xs:element name="{{{wpml_ns}}}gimbalPitchRotateEnable"><xs:simpleType><xs:restriction base="xs:integer"><xs:minInclusive value="0"/><xs:maxInclusive value="1"/></xs:restriction></xs:simpleType></xs:element>'
        f'<xs:element name="{{{wpml_ns}}}gimbalPitchRotateAngle"><xs:simpleType><xs:restriction base="xs:decimal"><xs:minInclusive value="-180"/><xs:maxInclusive value="180"/></xs:restriction></xs:simpleType></xs:element>'
        f'<xs:element name="{{{wpml_ns}}}gimbalYawRotateEnable"><xs:simpleType><xs:restriction base="xs:integer"><xs:minInclusive value="0"/><xs:maxInclusive value="1"/></xs:restriction></xs:simpleType></xs:element>'
        f'<xs:element name="{{{wpml_ns}}}gimbalYawRotateAngle"><xs:simpleType><xs:restriction base="xs:decimal"><xs:minInclusive value="-180"/><xs:maxInclusive value="180"/></xs:restriction></xs:simpleType></xs:element>',

    "rotateYaw":
        f'<xs:element name="{{{wpml_ns}}}aircraftHeading"><xs:simpleType><xs:restriction base="xs:decimal"><xs:minInclusive value="-180"/><xs:maxInclusive value="180"/></xs:restriction></xs:simpleType></xs:element>',

    "hover":
        f'<xs:element name="{{{wpml_ns}}}hoverTime"><xs:simpleType><xs:restriction base="xs:decimal"><xs:minExclusive value="0"/><xs:maxInclusive value="100000"/></xs:restriction></xs:simpleType></xs:element>'
}


# Crea un tipo di schema XSD per ciascuna azione.
action_variants_xml = []

for name, parameters in ACTION_SCHEMAS_XML.items():
    action_variants_xml.append(
                f'<xs:element name="{{{wpml_ns}}}actionActuatorFunc" type="xs:string" fixed="{name}"/>'
                f'<xs:element name="{{{wpml_ns}}}actionActuatorFuncParam">'
                    '<xs:complexType>'
                        '<xs:sequence>'
                            f'{parameters}'
                        '</xs:sequence>'
                    '</xs:complexType>'
                '</xs:element>'
    )


MISSION_SCHEMA_XML = f"""
                     '<xs:element name="missionConfig">'
                       '<xs:complexType>'
                          '<xs:sequence>'
                             '<xs:element name="{{{wpml_ns}}}globalRTHHeight" type="xs:integer" default="30"/>'
                             '<xs:element name="{{{wpml_ns}}}flyToWaylineMode" type="xs:string" fixed="safely"/>'
                             '<xs:element name="{{{wpml_ns}}}finishAction" type="xs:string" fixed="goHome"/>'
                             '<xs:element name="{{{wpml_ns}}}exitOnRCLost" type="xs:string" fixed="executeLostAction"/>'
                             '<xs:element name="{{{wpml_ns}}}executeRCLostAction" type="xs:string" fixed="hover"/>'
                             '<xs:element name="{{{wpml_ns}}}executeRCLostAction" type="xs:decimal" default"30.0"/>'
                             '<xs:element name="{{{wpml_ns}}}executeRCLostAction" type="xs:string" default="20.0"/>'
                             '<xs:element name="droneInfo">'
                               '<xs:complexType>'
                                  '<xs:sequence>'
                                     '<xs:element name="{{{wpml_ns}}}droneEnumValue" type="xs:integer" default="60"/>'
                                  '</xs:sequence>'
                                '</xs:complexType>'
                             '</xs:element>
                             '<xs:element name="droneInfo">'
                               '<xs:complexType>'
                                  '<xs:sequence>'
                                     '<xs:element name="{{{wpml_ns}}}payloadEnumValue" type="xs:integer" default="42"/>'
                                     '<xs:element name="{{{wpml_ns}}}payloadPositionIndex"><xs:simpleType><xs:restriction base="xs:integer"><xs:minInclusive value="0"/><xs:maxInclusive value="2"/></xs:restriction></xs:simpleType></xs:element>'
                                  '</xs:sequence>'
                              '</xs:complexType>'
                            '</xs:element>                          
                           '</xs:sequence>'
                         '</xs:complexType>'
                      '</xs:element>

                 '<xs:element name="Folder">'
                   '<xs:complexType>'
                     '<xs:sequence>'
                       '<xs:element name="{{{wpml_ns}}}templateId" type="xs:integer" default="0"/>'
                       '<xs:element name="{{{wpml_ns}}}executeHeightMode" type="xs:string" fixed="relativeToStartPoint"/>'
                       '<xs:element name="{{{wpml_ns}}}waylineId" type="xs:integer" default="0"/>'
                       '<xs:element name="{{{wpml_ns}}}distance" type="xs:decimal" default="0"/>'
                       '<xs:element name="{{{wpml_ns}}}duration" type="xs:decimal" default="0"/>'
                       '<xs:element name="{{{wpml_ns}}}autoFlightSpeed" type="xs:decimal" default="5.0"/>'
                        '<xs:element name="Placemark">'
                          '<xs:complexType>'
                             '<xs:sequence>'
                             
                                '<xs:element name="Point">'
                                   '<xs:complexType>'
                                      '<xs:sequence>'
                                               '<xs:element name="{{{wpml_ns}}}coordinates"><xs:type="xs:string"/>
                                      '</xs:sequence>'
                                  ' </xs:complexType>'
                                '</xs:element>                       
                              '<xs:element name="{{{wpml_ns}}}index"type="xs:integer" default="0"/>
                              '<xs:element name="{{{wpml_ns}}}waypointSpeed"><xs:simpleType><xs:restriction base="xs:decimal"><xs:minInclusive value="0.1"/><xs:maxInclusive value="unbonded"/></xs:restriction></xs:simpleType></xs:element>'
                              '<xs:element name="{{{wpml_ns}}}waypointHeadingParam">'
                                  '<xs:complexType>'
                                     '<xs:sequence>'
                                         '<xs:element name="{{{wpml_ns}}}waypointHeadingMode" type="xs:string" fixed="followWayline"/>'
                                     '</xs:sequence>'
                                 '</xs:complexType>'
                              '</xs:element>
                              '<xs:element name="{{{wpml_ns}}}waypointTurnParam">'
                                  '<xs:complexType>'
                                     '<xs:sequence>'
                                         '<xs:element name="{{{wpml_ns}}}waypointTurnMode" type="xs:string" fixed="toPointAndStopWithDiscontinuityCurvature"/>'
                                         '<xs:element name="{{{wpml_ns}}}waypointTurnDampingDist" type="xs:integer" default="0"/>'
                                  '</xs:complexType>'
                              '</xs:element>                           
                              '<xs:element name="{{{wpml_ns}}}useStraightLine" type="xs:integer" default="1"/>'
                              '<xs:element name="{{{wpml_ns}}}actionGroup">'
                                 '<xs:complexType>'
                                    '</xs:sequence>'
                                        '<xs:element name="{{{wpml_ns}}}actionGroupId"type="xs:integer" default="0"/>
                                        '<xs:element name="{{{wpml_ns}}}actionGroupStartIndex"type="xs:integer" default="0"/>
                                        '<xs:element name="{{{wpml_ns}}}actionGroupEndIndex"type="xs:integer" default="0"/>
                                        '<xs:element name="{{{wpml_ns}}}actionGroupMode" type="xs:string" fixed="sequence"/>'
                                        '<xs:element name="{{{wpml_ns}}}actionTrigger">'
                                            '<xs:complexType>'
                                               '</xs:sequence>'
                                                   '<xs:element name="{{{wpml_ns}}}actionTriggerType" type="xs:string" fixed="reachPoint"/>'
                                               '</xs:sequence>'
                                            '</xs:complexType>'
                                        '</xs:element> 
                                        '<xs:element name="{{{wpml_ns}}}action">'
                                            '<xs:complexType>'
                                               '</xs:sequence>'
                                                    '<xs:element name="{{{wpml_ns}}}actionId"type="xs:integer" default="0"/>
                                                    <xs:choice>
                                                      {action_variants_xml[0]}
                                                      {action_variants_xml[1]}
                                                      {action_variants_xml[2]}
                                                      {action_variants_xml[3]}
                                                      {action_variants_xml[4]}
                                                      {action_variants_xml[5]}
                                                    </xs:choice>
                                               '</xs:sequence>'
                                            '</xs:complexType>'
                                        '</xs:element>                                     
                                    '</xs:sequence>'
                                  '</xs:complexType>'
                              '</xs:element>     
                             '</xs:sequence>'
                         ' </xs:complexType>'
                       '</xs:element>
                     '</xs:sequence>'
                  ' </xs:complexType>'
                '</xs:element>
"""






# =========================
# JSON Schema - Missioni DJI
# =========================

# Definisce i parametri e i vincoli di ciascuna azione.
ACTION_SCHEMAS_JSON = {
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
action_variants_json = []

for name, parameters in ACTION_SCHEMAS_JSON.items():
    action_variants_json.append({
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
MISSION_SCHEMA_JSON = {
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
                            "oneOf": action_variants_json
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

risposta = -1

while risposta not in (0, 1):
    try:
        risposta = int(input("Usare pipeline Json o direttamente xml? 0 o 1: "))
    except ValueError:
        print("Per favore, inserisci un numero valido (0 oppure 1).")

print(f"Hai scelto: {risposta}")

if(risposta==0):
 data = {
     "model": "llama3.2",
     "prompt": "Genera una missione drone con esattamente 3 waypoint. Usa queste coordinate, lat 43.10876 lon 12.38830,  lat 43.10879 lon 12.38835, lat 43.10882, lon 12.38840. Ogni waypoint deve avere stessa velocita' di 20 e stessa quota di 10. Ogni waypoint ha una sola azione, ovvero un Hover di 5 secondi per il primo waypoint, 10 per il secondo e 15 per il terzo. Il payload index è 0",
     "format": MISSION_SCHEMA_JSON,
     "stream": False     
 } 
 response= requests.post( url, json=data, timeout=200)

 response.raise_for_status()


 result=response.json()

 mission_data = json.loads(result["response"])

 validate(instance=mission_data, schema=MISSION_SCHEMA_JSON)
 print("JSON valido secondo lo schema!")

 print(mission_data)
 print(" ")

 # Costruisce l'oggetto Mission e assegna gli ID.
 mission = mission_from_dict(mission_data)
 mission_to_kmz(mission,"mission_LLM_JSON")

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
else: 
     data = {
     "model": "llama3.2",
     "prompt": "Genera una missione drone con esattamente 3 waypoint. Usa queste coordinate, lat 43.10876 lon 12.38830,  lat 43.10879 lon 12.38835, lat 43.10882, lon 12.38840. Ogni waypoint deve avere stessa velocita' di 20 e stessa quota di 10. Ogni waypoint ha una sola azione, ovvero un Hover di 5 secondi per il primo waypoint, 10 per il secondo e 15 per il terzo. Il payload index è 0",
     "format": MISSION_SCHEMA_XML,
     "stream": False     
    } 

     response= requests.post( url, data, timeout=200)
     response.raise_for_status()
     print(response)
     print(" ")

     wpmz_folder = 'out/wpmz'
     os.makedirs(wpmz_folder, exist_ok=True) 



     waylines= etree.Element(f"{{{kml_ns}}}kml", nsmap=namespaces)
     document_waylines = etree.SubElement(waylines, f"{{{kml_ns}}}Document")
     write_pretty_xml(waylines+MISSION_SCHEMA_XML, os.path.join(wpmz_folder, waylines.wpml) )
        
     template = etree.Element(f"{{{kml_ns}}}kml", nsmap=namespaces)  # Associa gli URI dei namespace ai rispettivi prefissi.
     document_template = etree.SubElement(template, f"{{{kml_ns}}}Document")  # Aggiunge <Document> come figlio di <kml>.
     write_pretty_xml(template, os.path.join(wpmz_folder, template.kml) )




     percorso_file = "waylines.wpml"
     tree = ET.parse('out/wpmz')
     root = tree.getroot()

     waypoints=[]
     waypointspeeds=[]
     waypointheights=[]

     for elem in root.iter():
     # Ignora il namespace e controlla solo il nome pulito del tag
      if elem.tag.endswith("coordinates"):
       waypoints.append(elem.text)

      if elem.tag.endswith("executeHeight"):
       waypointheights.append(elem.text)

      if elem.tag.endswith("waypointspeeds"):
       waypointspeeds.append(elem.text)
       
     def total_distance() -> float:
        if len((waypoints)) < 2:
            return 0.0

        total = 0.0
        for i in range(len(waypoints) - 1):
            parti=waypoints[i].split(",")
            lat = parti[0].strip()    # '22'
            lon = parti[1].strip()
            wp1 = (lat, lon)
            wp2 = (lat, lon)
            total += geodesic(wp1, wp2).meters  # Distanza geografica, senza differenza di quota.

        return round(total, 2)

   # Stima il tempo di volo sommando i tempi dei singoli tratti tridimensionali.
     def total_time(self) -> float:
        total = 0.0

        for i in range(len(waypoints) - 1):

            parti=waypoints[i].split(",")
            lat = parti[0].strip()    
            lon = parti[1].strip()
            wp1 = (lat, lon)
            wp2 = (lat, lon)           

            distanceX = geodesic(wp1, wp2).meters                       # Distanza orizzontale in metri.
            distanceY = abs(waypointheights[i] - waypointheights[i + 1])  # Differenza di quota in metri.
            distance = math.sqrt(distanceX**2 + distanceY**2)          # Lunghezza del tratto nello spazio.

            speed = waypointspeeds[i]                            # Velocità del waypoint di partenza.

            if speed <= 0:
                raise ValueError("La velocità del tratto deve essere positiva")

            total += distance / speed

        for elem in root.iter():
          if elem.tag.endswith("hoverTime"):
                   total += float(elem.text)
        return round(total, 2)

     for elem in root.iter():
        if elem.tag.endswith("distance"):
                   elem.text=total_distance()
        
     for elem in root.iter():
        if elem.tag.endswith("duration"):
                   elem.text=total_time()  

     stop=False
     for elem in root.iter(): #autoFlightSpeed riprende la v del primo point
         if elem.tag.endswith("waypointSpeed"):        
           for elemtwo in root.iter():
            if elemtwo.tag.endswith("autoFlightSpeed"):
                    elemtwo.text=elem.text
                    stop=True
                    break
         if(not(stop)):
             break 

     counterwaypoint=0
     counteraction=0

     for elem in root.iter(): #sistemo id
         counteraction=0
         if elem.tag==(f"{{{wpml_ns}}}index"): 
           elem.text=counterwaypoint      
         if elem.tag==(f"{{{wpml_ns}}}actionGroupId"):
           elem.text=counterwaypoint
         if elem.tag==(f"{{{wpml_ns}}}actionGroupStartIndex"):
           elem.text=counterwaypoint
         if elem.tag==(f"{{{wpml_ns}}}actionGroupEndIndex"):
           elem.text=counterwaypoint
         if elem.tag==(f"action"):
           counterwaypoint+=1
           for elemtwo in elem.iter():
               if elemtwo.tag.endswith("actionId"):
                   elemtwo.text=counteraction
                   counteraction+=1
               if elemtwo.tag==("/Placemark"):
                   break
                   
          
     create_kmz('mission_LLM_XML', wpmz_folder)  # Comprime i file e genera il KMZ finale.