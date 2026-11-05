
import os
import shutil
from lxml import etree

from mission import Mission, print_mission, create_empty_mission, Waypoint, ACTIONS, Action


# Scrive un albero XML su file, aggiungendo indentazione e dichiarazione iniziale.
def write_pretty_xml(element, file_path):
    pretty_xml = etree.tostring(
        element,
        pretty_print=True,          # Indenta gli elementi XML per renderli leggibili.
        xml_declaration=True,       # Inserisce la dichiarazione <?xml ... ?>.
        encoding='UTF-8'            # Converte l'albero XML in byte UTF-8.
    )

    with open(file_path, 'wb') as file:   # Modalità binaria, dato che pretty_xml contiene byte.
        file.write(pretty_xml)


# Comprime i file della missione in uno ZIP, lo rinomina in KMZ e lo sposta in out/.
def create_kmz(mission_name, folder_to_zip):
    output_folder = "out"
    kmz_filename = f"{mission_name}.kmz"

    shutil.make_archive(mission_name, 'zip', folder_to_zip)       # Comprime il contenuto della cartella.
    shutil.move(f"{mission_name}.zip", kmz_filename)              # Cambia l'estensione da ZIP a KMZ.
    shutil.move(kmz_filename, os.path.join(output_folder, kmz_filename))  # Sposta il file nella cartella out.


# Converte un oggetto Mission nei documenti XML richiesti da DJI e genera il KMZ.
def mission_to_kmz(mission, mission_name):
    wpmz_folder = 'out/wpmz'             # Cartella temporanea contenente i documenti della missione.
    template_file = 'template.kml'
    waylines_file = 'waylines.wpml'

    namespaces = {
        None: 'http://www.opengis.net/kml/2.2',   # Namespace KML predefinito.
        'wpml': 'http://www.dji.com/wpmz/1.0.3'    # Namespace WPML specifico di DJI.
    }

    kml_ns = namespaces[None]          # URI del namespace KML.
    wpml_ns = namespaces['wpml']       # URI del namespace WPML.

    os.makedirs(wpmz_folder, exist_ok=True)  # Crea la cartella solo se non esiste.

    # Creazione del template.kml.
    kml_template = etree.Element(f"{{{kml_ns}}}kml", nsmap=namespaces)  # Associa gli URI dei namespace ai rispettivi prefissi.
    document_template = etree.SubElement(kml_template, f"{{{kml_ns}}}Document")  # Aggiunge <Document> come figlio di <kml>.

    write_pretty_xml(kml_template, os.path.join(wpmz_folder, template_file))

    # Creazione del waylines.wpml, che contiene la traiettoria della missione.
    kml_waylines = etree.Element(f"{{{kml_ns}}}kml", nsmap=namespaces)
    document_waylines = etree.SubElement(kml_waylines, f"{{{kml_ns}}}Document")

    mission_config = etree.SubElement(document_waylines, f"{{{wpml_ns}}}missionConfig")  # Configurazione generale della missione DJI.

    initial_speed = mission.waypoints[0].speed if mission.waypoints else 5.0  # Velocità di riferimento.

    etree.SubElement(mission_config, f"{{{wpml_ns}}}globalRTHHeight").text = '30'  # Quota di ritorno a casa.
    etree.SubElement(mission_config, f"{{{wpml_ns}}}flyToWaylineMode").text = 'safely'  # Modalità di avvicinamento.
    etree.SubElement(mission_config, f"{{{wpml_ns}}}finishAction").text = 'goHome'  # Azione a fine missione.
    etree.SubElement(mission_config, f"{{{wpml_ns}}}exitOnRCLost").text = 'executeLostAction'  # Gestione perdita segnale.
    etree.SubElement(mission_config, f"{{{wpml_ns}}}executeRCLostAction").text = 'hover'  # Rimane in hovering.
    etree.SubElement(mission_config, f"{{{wpml_ns}}}takeOffSecurityHeight").text = '30'  # Quota di sicurezza al decollo.
    etree.SubElement(mission_config, f"{{{wpml_ns}}}globalTransitionalSpeed").text = str(initial_speed)  # Velocità di transizione.

    drone_info = etree.SubElement(mission_config, f"{{{wpml_ns}}}droneInfo")  # Contenitore delle informazioni sul drone.

    etree.SubElement(drone_info, f"{{{wpml_ns}}}droneEnumValue").text = '60'  # DJI Matrice 300 RTK.

    payload_info = etree.SubElement(mission_config, f"{{{wpml_ns}}}payloadInfo")  # Contenitore delle informazioni sul payload.

    etree.SubElement(payload_info, f"{{{wpml_ns}}}payloadEnumValue").text = '42'  # Camera Zenmuse H20.
    etree.SubElement(payload_info, f"{{{wpml_ns}}}payloadPositionIndex").text = str(mission.payload_index)  # Posizione del payload.

    folder = etree.SubElement(document_waylines, f"{{{kml_ns}}}Folder")  # Contiene le informazioni della traiettoria e i waypoint.

    etree.SubElement(folder, f"{{{wpml_ns}}}templateId").text = '0'  # Identificativo del template.
    etree.SubElement(folder, f"{{{wpml_ns}}}executeHeightMode").text = 'relativeToStartPoint'  # Quote relative al decollo.
    etree.SubElement(folder, f"{{{wpml_ns}}}waylineId").text = '0'  # Identificativo della traiettoria.
    etree.SubElement(folder, f"{{{wpml_ns}}}distance").text = str(mission.total_distance())  # Distanza totale.
    etree.SubElement(folder, f"{{{wpml_ns}}}duration").text = str(mission.total_time())  # Durata stimata.
    etree.SubElement(folder, f"{{{wpml_ns}}}autoFlightSpeed").text = str(initial_speed)  # Velocità generale di riferimento.

    for waypoint in mission.waypoints:
        placemark = etree.SubElement(folder, f"{{{kml_ns}}}Placemark")  # Crea un elemento KML per il waypoint corrente.

        point = etree.SubElement(placemark, f"{{{kml_ns}}}Point")  # Contenitore delle coordinate geografiche.

        coordinates = etree.SubElement(point, f"{{{kml_ns}}}coordinates")  # Elemento KML contenente longitudine e latitudine.

        coordinates.text = f"{waypoint.lon},{waypoint.lat}"  # In KML l'ordine è longitudine, latitudine.

        etree.SubElement(placemark, f"{{{wpml_ns}}}index").text = str(waypoint.waypoint_id)  # ID del waypoint.
        etree.SubElement(placemark, f"{{{wpml_ns}}}executeHeight").text = str(waypoint.quote)  # Quota del waypoint.
        etree.SubElement(placemark, f"{{{wpml_ns}}}waypointSpeed").text = str(waypoint.speed)  # Velocità verso il prossimo punto.

        waypoint_heading_param = etree.SubElement(placemark, f"{{{wpml_ns}}}waypointHeadingParam")  # Contenitore dei parametri di orientamento del drone.

        etree.SubElement(waypoint_heading_param, f"{{{wpml_ns}}}waypointHeadingMode").text = 'followWayline'  # Il drone segue la direzione della traiettoria.

        waypoint_turn_param = etree.SubElement(placemark, f"{{{wpml_ns}}}waypointTurnParam")  # Contenitore delle impostazioni di svolta.

        etree.SubElement(waypoint_turn_param, f"{{{wpml_ns}}}waypointTurnMode").text = 'toPointAndStopWithDiscontinuityCurvature'  # Modalità di svolta con arresto al waypoint.

        etree.SubElement(waypoint_turn_param, f"{{{wpml_ns}}}waypointTurnDampingDist").text = '0'  # Distanza di smorzamento della svolta.

        etree.SubElement(placemark, f"{{{wpml_ns}}}useStraightLine").text = '1'  # Utilizza tratti rettilinei.

        action_group = etree.SubElement(placemark, f"{{{wpml_ns}}}actionGroup")  # Raggruppa le azioni del waypoint.

        etree.SubElement(action_group, f"{{{wpml_ns}}}actionGroupId").text = str(waypoint.waypoint_id)  # ID del gruppo.
        etree.SubElement(action_group, f"{{{wpml_ns}}}actionGroupStartIndex").text = str(waypoint.waypoint_id)  # Primo WP interessato.
        etree.SubElement(action_group, f"{{{wpml_ns}}}actionGroupEndIndex").text = str(waypoint.waypoint_id)  # Ultimo WP interessato.
        etree.SubElement(action_group, f"{{{wpml_ns}}}actionGroupMode").text = 'sequence'  # Azioni eseguite in sequenza.

        action_trigger = etree.SubElement(action_group, f"{{{wpml_ns}}}actionTrigger")  # Contenitore della condizione che avvia le azioni.

        etree.SubElement(action_trigger, f"{{{wpml_ns}}}actionTriggerType").text = 'reachPoint'  # Esegue le azioni al raggiungimento del waypoint.

        for action in waypoint.actions:
            action_element = etree.SubElement(action_group, f"{{{wpml_ns}}}action")  # Crea un elemento XML per ogni azione del waypoint.

            etree.SubElement(action_element, f"{{{wpml_ns}}}actionId").text = str(action.action_id)  # ID dell'azione.
            etree.SubElement(action_element, f"{{{wpml_ns}}}actionActuatorFunc").text = action.action_type  # Tipo di azione.

            action_actuator_func_param = etree.SubElement(action_element, f"{{{wpml_ns}}}actionActuatorFuncParam")  # Contenitore dei parametri specifici dell'azione.

            for param, value in action.parameters.items():
                etree.SubElement(action_actuator_func_param, f"{{{wpml_ns}}}{param}").text = str(value)  # Ogni coppia chiave-valore diventa un elemento XML.

    write_pretty_xml(kml_waylines, os.path.join(wpmz_folder, waylines_file))  # Salva il documento WPML.
    create_kmz(mission_name, wpmz_folder)  # Comprime i file e genera il KMZ finale.


# Estrae un KMZ e ricostruisce l'oggetto Mission leggendo coordinate, quote, velocità e azioni.
def kmz_to_mission(mission_name):
    out_dir = "out"
    temp_dir = os.path.join(out_dir, "temp")

    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)         # Elimina la cartella temporanea precedente.

    kml_path = os.path.join(out_dir, f"{mission_name}.kmz")  # Percorso del KMZ da importare.
    shutil.unpack_archive(kml_path, temp_dir, "zip")         # Estrae il contenuto dello ZIP/KMZ.

    wpml_path = os.path.join(temp_dir, "waylines.wpml")      # File contenente la traiettoria.

    if not os.path.exists(wpml_path):
        raise FileNotFoundError(f"{wpml_path} not found in the KMZ archive.")

    with open(wpml_path, "rb") as wpml_file:
        xml_content = wpml_file.read()  # Legge il documento XML come sequenza di byte.

    root = etree.fromstring(xml_content)  # Converte il documento in un albero XML navigabile.

    namespaces = {
        "kml": "http://www.opengis.net/kml/2.2",   # Prefisso usato per cercare gli elementi KML con XPath.
        "wpml": "http://www.dji.com/wpmz/1.0.3"    # Prefisso usato per gli elementi WPML.
    }

    mission = create_empty_mission()  # Crea una Mission senza waypoint.

    mission_config = root.xpath("//wpml:missionConfig", namespaces=namespaces)[0]  # Cerca missionConfig nell'intero documento e prende il primo risultato.

    mission.payload_index = int(
        mission_config.xpath(
            "wpml:payloadInfo/wpml:payloadPositionIndex/text()",
            namespaces=namespaces
        )[0]
    )                                 # Ricava la posizione del payload dalla configurazione.

    waypoints = root.xpath("//kml:Placemark", namespaces=namespaces)  # Recupera tutti i waypoint presenti nel documento.

    for waypoint in waypoints:
        coordinates = waypoint.xpath("kml:Point/kml:coordinates/text()", namespaces=namespaces)[0]  # Legge le coordinate del Placemark corrente.

        quote = float(waypoint.xpath("wpml:executeHeight/text()", namespaces=namespaces)[0])  # Recupera la quota specifica del waypoint.

        speed = float(waypoint.xpath("wpml:waypointSpeed/text()", namespaces=namespaces)[0])  # Recupera la velocità verso il waypoint successivo.

        lat = float(coordinates.split(",")[1])  # Secondo valore delle coordinate KML.
        lon = float(coordinates.split(",")[0])  # Primo valore delle coordinate KML.

        wp = Waypoint(lat, lon, speed, quote)  # Ricostruisce l'oggetto Waypoint.

        actions = waypoint.xpath(".//wpml:action", namespaces=namespaces)  # Cerca le azioni all'interno del waypoint corrente.

        for action in actions:
            actuator_func = action.xpath("wpml:actionActuatorFunc/text()", namespaces=namespaces)[0]  # Legge il tipo di azione, ad esempio hover o takePhoto.

            actuator_params = action.xpath("wpml:actionActuatorFuncParam", namespaces=namespaces)  # Recupera gli elementi contenenti i parametri dell'azione.

            params = {}               # Dizionario dei parametri che verranno ricostruiti.

            for actuator_param in actuator_params:
                for child in actuator_param:
                    tag_name = child.tag.split('}')[1]  # Rimuove il namespace dal nome XML.

                    if tag_name in ACTIONS[actuator_func]["parameters"]:  # Controlla se il parametro è supportato.
                        tag_value = child.text         # Recupera il contenuto testuale dell'elemento.
                        params[tag_name] = tag_value   # Associa nome e valore nel dizionario.

            action_obj = Action(action_type=actuator_func, **params)  # Ricostruisce l'azione espandendo il dizionario dei parametri.

            wp.add_action(action_obj)  # Associa l'azione al waypoint corrente.

        mission.add_waypoint(wp)       # Aggiunge il waypoint e aggiorna gli identificativi.

    shutil.rmtree(temp_dir)            # Rimuove i file temporanei estratti dal KMZ.
    return mission


# Prova l'importazione di mission.kmz eseguendo direttamente il parser.
if __name__ == '__main__':
    kmz_to_mission("mission")
