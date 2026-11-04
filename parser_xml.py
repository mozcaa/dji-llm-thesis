
import os
import shutil
from lxml import etree

from mission import Mission, print_mission, create_empty_mission, Waypoint, ACTIONS, Action


# from mission import create_mock_mission


# Scrive un elemento XML e tutti i suoi figli in un file.
def write_pretty_xml(element, file_path):
    # Converte l'albero XML in una sequenza di byte.
    # pretty_print aggiunge indentazione per rendere il file leggibile.
    pretty_xml = etree.tostring(
        element, pretty_print=True, xml_declaration=True, encoding='UTF-8'
    )

    # Apre il file in modalità binaria e scrive il contenuto XML.
    with open(file_path, 'wb') as file:
        file.write(pretty_xml)


# Crea l'archivio KMZ contenente i file della missione.
def create_kmz(mission_name, folder_to_zip):
    output_folder = "out"
    kmz_filename = f"{mission_name}.kmz"

    # Comprime il contenuto della cartella in un archivio ZIP.
    shutil.make_archive(mission_name, 'zip', folder_to_zip)

    # Rinomina l'archivio da .zip a .kmz.
    shutil.move(f"{mission_name}.zip", kmz_filename)

    # Sposta il file KMZ nella cartella di output.
    shutil.move(kmz_filename, os.path.join(output_folder, kmz_filename))


# Converte un oggetto Mission in un file KMZ.
# Il processo consiste nel creare i documenti XML/WPML
# e successivamente inserirli in un archivio KMZ.
def mission_to_kmz(mission, mission_name):
    wpmz_folder = 'out/wpmz'
    template_file = 'template.kml'
    waylines_file = 'waylines.wpml'

    # Define the namespaces
    # Namespace utilizzati per distinguere gli elementi KML
    # da quelli specifici del formato WPML di DJI.
    namespaces = {
        None: 'http://www.opengis.net/kml/2.2',
        'wpml': 'http://www.dji.com/wpmz/1.0.3'
    }

    # Ensure the output folder exists
    # Crea la cartella di lavoro se non è già presente.
    os.makedirs(wpmz_folder, exist_ok=True)

    # Create "template.kml"
    # Crea l'elemento principale <kml> e il relativo <Document>.
    # nsmap associa i prefissi ai namespace dichiarati sopra.
    kml_template = etree.Element('kml', nsmap=namespaces)
    document_template = etree.SubElement(kml_template, 'Document')

    # Salva il primo documento XML.
    write_pretty_xml(kml_template, os.path.join(wpmz_folder, template_file))

    # Create "waylines.wpml"
    # Crea un secondo albero XML, destinato a contenere
    # le informazioni necessarie per descrivere la missione.
    kml_waylines = etree.Element('kml', nsmap=namespaces)
    document_waylines = etree.SubElement(kml_waylines, 'Document')

    # Add <wpml:missionConfig> and <Folder> to the document
    # Crea la sezione dedicata alla configurazione generale della missione.
    # La sintassi {namespace}nomeElemento permette a lxml
    # di associare l'elemento al namespace WPML.
    mission_config = etree.SubElement(document_waylines, f"{{{namespaces['wpml']}}}missionConfig")

    # Add child elements to <wpml:missionConfig>
    # Parametri che definiscono il comportamento generale del drone.
    # Ogni SubElement crea un nuovo nodo XML figlio di mission_config.
    # L'attributo .text ne imposta il contenuto.

    # Altezza prevista per il ritorno automatico.
    etree.SubElement(mission_config, f"{{{namespaces['wpml']}}}globalRTHHeight").text = '30'

    # Modalità con cui il drone raggiunge l'inizio del percorso.
    etree.SubElement(mission_config, f"{{{namespaces['wpml']}}}flyToWaylineMode").text = 'safely'

    # Comportamento al termine della missione.
    etree.SubElement(mission_config, f"{{{namespaces['wpml']}}}finishAction").text = 'goHome'

    # Comportamento previsto in caso di perdita del radiocomando.
    etree.SubElement(mission_config, f"{{{namespaces['wpml']}}}exitOnRCLost").text = 'executeLostAction'
    etree.SubElement(mission_config, f"{{{namespaces['wpml']}}}executeRCLostAction").text = 'hover'

    # Altezza di sicurezza al decollo e velocità globale di transizione.
    # I valori provengono dall'oggetto Mission.
    etree.SubElement(mission_config, f"{{{namespaces['wpml']}}}takeOffSecurityHeight").text = str(mission.height)
    etree.SubElement(mission_config, f"{{{namespaces['wpml']}}}globalTransitionalSpeed").text = str(mission.speed)

    # Add <wpml:droneInfo>
    # Sezione dedicata al modello di drone.
    drone_info = etree.SubElement(mission_config, f"{{{namespaces['wpml']}}}droneInfo")

    # 42 (H20),
    # 43 (H20T)
    # 52 (M30),
    # 53 (M30T)
    # 61 (H20N)
    # 66 (Mavic 3E Camera)
    # 67 (Mavic 3T Camera)
    # 68 (Mavic 3M Camera)
    # 80 (Matrice 3D Camera)
    # 81(Matrice 3TD Camera)
    # 65534 (PSDK Payload Device)
    # 82 (H30)
    # 83 (H30T)

    # Identificativo del modello di drone previsto dalla missione.
    etree.SubElement(drone_info, f"{{{namespaces['wpml']}}}droneEnumValue").text = '60'
    # etree.SubElement(drone_info, f"{{{namespaces['wpml']}}}droneSubEnumValue").text = '0'

    # Add <wpml:payloadInfo>
    # Sezione che descrive il payload utilizzato dal drone.
    payload_info = etree.SubElement(mission_config, f"{{{namespaces['wpml']}}}payloadInfo")

    # 42 (H20),
    # 43 (H20T)
    # 52 (M30),
    # 53 (M30T)
    # 61 (H20N)
    # 66 (Mavic 3E Camera)
    # 67 (Mavic 3T Camera)
    # 68 (Mavic 3M Camera)
    # 80 (Matrice 3D Camera)
    # 81(Matrice 3TD Camera)
    # 65534 (PSDK Payload Device)
    # 82 (H30)
    # 83 (H30T

    # Identificativo del payload.
    etree.SubElement(payload_info, f"{{{namespaces['wpml']}}}payloadEnumValue").text = '42'
    # etree.SubElement(payload_info, f"{{{namespaces['wpml']}}}payloadSubEnumValue").text = '0'

    # 0: Mount position of 1. The M300 RTK and M350 RTK models correspond to the front left of the drone. Other models correspond to the main gimbal.
    # 1: Mount position of 2. The M300 RTK and M350 RTK models correspond to the front right of the drone.
    # 2: Mount position of 3. The M300 RTK and M350 RTK models correspond to the top of the aircraft.

    # Indica la posizione del payload sul drone.
    etree.SubElement(payload_info, f"{{{namespaces['wpml']}}}payloadPositionIndex").text = str(mission.payload_index)

    # Add <Folder>
    # Il Folder conterrà il percorso e i singoli waypoint.
    folder = etree.SubElement(document_waylines, 'Folder')

    # Add elements inside <Folder>
    # Parametri generali della traiettoria.

    # Identificativi del template e della traiettoria.
    etree.SubElement(folder, f"{{{namespaces['wpml']}}}templateId").text = '0'

    # Le quote di esecuzione sono riferite al punto di decollo.
    etree.SubElement(folder, f"{{{namespaces['wpml']}}}executeHeightMode").text = 'relativeToStartPoint'

    etree.SubElement(folder, f"{{{namespaces['wpml']}}}waylineId").text = '0'

    # Distanza e durata stimate usando i metodi della classe Mission.
    etree.SubElement(folder, f"{{{namespaces['wpml']}}}distance").text = str(mission.total_distance())
    etree.SubElement(folder, f"{{{namespaces['wpml']}}}duration").text = str(mission.total_time())

    # Velocità di volo della traiettoria.
    etree.SubElement(folder, f"{{{namespaces['wpml']}}}autoFlightSpeed").text = str(mission.speed)

    # Scorre tutti i waypoint nell'ordine previsto dalla missione.
    for waypoint in mission.waypoints:
        # Add <Placemark>
        # Ogni Placemark rappresenta un waypoint nel documento.
        placemark = etree.SubElement(folder, 'Placemark')

        # Add <Point>
        # Il Point contiene le coordinate geografiche del waypoint.
        point = etree.SubElement(placemark, 'Point')
        coordinates = etree.SubElement(point, 'coordinates')

        # Very important: LON, LAT
        # Nel formato KML la longitudine precede la latitudine.
        coordinates.text = f"{waypoint.lon},{waypoint.lat}"

        # Indice, quota e velocità associati al waypoint.
        # Qui vengono utilizzati i valori globali della missione.
        etree.SubElement(placemark, f"{{{namespaces['wpml']}}}index").text = str(waypoint.waypoint_id)
        etree.SubElement(placemark, f"{{{namespaces['wpml']}}}executeHeight").text = str(mission.height)
        etree.SubElement(placemark, f"{{{namespaces['wpml']}}}waypointSpeed").text = str(mission.speed)

        # Parametri che definiscono l'orientamento del drone
        # durante il movimento verso il waypoint.
        waypoint_heading_param = etree.SubElement(placemark, f"{{{namespaces['wpml']}}}waypointHeadingParam")
        etree.SubElement(waypoint_heading_param, f"{{{namespaces['wpml']}}}waypointHeadingMode").text = 'followWayline'

        # Parametri relativi alla modalità di svolta del drone.
        waypoint_turn_param = etree.SubElement(placemark, f"{{{namespaces['wpml']}}}waypointTurnParam")
        etree.SubElement(waypoint_turn_param,
                         f"{{{namespaces['wpml']}}}waypointTurnMode").text = 'toPointAndStopWithDiscontinuityCurvature'
        etree.SubElement(waypoint_turn_param, f"{{{namespaces['wpml']}}}waypointTurnDampingDist").text = '0'

        # Indica l'utilizzo di tratti rettilinei.
        etree.SubElement(placemark, f"{{{namespaces['wpml']}}}useStraightLine").text = '1'

        # Add <wpml:actionGroup>
        # Le azioni associate al waypoint vengono raccolte
        # all'interno di un unico gruppo.
        action_group = etree.SubElement(placemark, f"{{{namespaces['wpml']}}}actionGroup")

        # Identificativo del gruppo e intervallo dei waypoint
        # ai quali sono associate le azioni.
        etree.SubElement(action_group, f"{{{namespaces['wpml']}}}actionGroupId").text = str(waypoint.waypoint_id)
        etree.SubElement(action_group, f"{{{namespaces['wpml']}}}actionGroupStartIndex").text = str(
            waypoint.waypoint_id)
        etree.SubElement(action_group, f"{{{namespaces['wpml']}}}actionGroupEndIndex").text = str(waypoint.waypoint_id)

        # Le azioni del gruppo vengono eseguite in sequenza.
        etree.SubElement(action_group, f"{{{namespaces['wpml']}}}actionGroupMode").text = 'sequence'

        # Definisce l'evento che avvia le azioni del gruppo.
        # reachPoint indica il raggiungimento del waypoint.
        action_trigger = etree.SubElement(action_group, f"{{{namespaces['wpml']}}}actionTrigger")
        etree.SubElement(action_trigger, f"{{{namespaces['wpml']}}}actionTriggerType").text = 'reachPoint'

        # Scorre tutte le azioni associate al waypoint corrente.
        for action in waypoint.actions:
            # add <wpml:action>
            # Crea l'elemento XML che rappresenta la singola azione.
            action_element = etree.SubElement(action_group, f"{{{namespaces['wpml']}}}action")

            # Salva l'identificativo e il tipo di azione.
            etree.SubElement(action_element, f"{{{namespaces['wpml']}}}actionId").text = str(action.action_id)
            etree.SubElement(action_element, f"{{{namespaces['wpml']}}}actionActuatorFunc").text = action.action_type

            # add child <wpml:actionActuatorFuncParam>
            # Contenitore dei parametri specifici dell'azione.
            action_actuator_func_param = etree.SubElement(action_element,
                                                          f"{{{namespaces['wpml']}}}actionActuatorFuncParam")

            # Ogni coppia chiave-valore del dizionario parameters
            # viene trasformata in un elemento XML.
            for param, value in action.parameters.items():
                etree.SubElement(action_actuator_func_param, f"{{{namespaces['wpml']}}}{param}").text = str(value)

    # Terminata la creazione dell'albero XML, salva waylines.wpml.
    write_pretty_xml(kml_waylines, os.path.join(wpmz_folder, waylines_file))

    # Comprime i file generati nell'archivio KMZ finale.
    create_kmz(mission_name, wpmz_folder)


# Esegue l'operazione inversa di mission_to_kmz():
# legge un KMZ e ricostruisce un oggetto Mission.
def kmz_to_mission(mission_name):
    out_dir = "out"
    temp_dir = os.path.join(out_dir, "temp")

    # Elimina l'eventuale cartella temporanea già presente.
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

    # Costruisce il percorso del KMZ e ne estrae il contenuto.
    kml_path = os.path.join(out_dir, f"{mission_name}.kmz")
    shutil.unpack_archive(kml_path, temp_dir, "zip")

    # Cerca il file WPML all'interno dell'archivio estratto.
    wpml_path = os.path.join(temp_dir, "waylines.wpml")

    if not os.path.exists(wpml_path):
        raise FileNotFoundError(f"{wpml_path} not found in the KMZ archive.")

    # Legge il contenuto XML in modalità binaria.
    with open(wpml_path, "rb") as wpml_file:
        xml_content = wpml_file.read()

    # Converte il contenuto XML in un albero di elementi lxml.
    root = etree.fromstring(xml_content)

    # Namespace utilizzati per le ricerche XPath.
    # Il prefisso kml permette di cercare gli elementi KML,
    # mentre wpml identifica gli elementi specifici DJI.
    namespaces = {
        "kml": "http://www.opengis.net/kml/2.2",
        "wpml": "http://www.dji.com/wpmz/1.0.3"
    }

    # Crea una missione inizialmente vuota, che verrà
    # riempita con i dati letti dal documento XML.
    mission = create_empty_mission()

    # Cerca l'elemento missionConfig nell'intero albero XML.
    # L'indice [0] seleziona il primo elemento trovato.
    mission_config = root.xpath("//wpml:missionConfig", namespaces=namespaces)[0]

    # Estrae i parametri globali della missione.
    # /text() recupera il contenuto testuale dell'elemento,
    # che viene poi convertito nel tipo numerico appropriato.
    mission.height = float(mission_config.xpath("wpml:takeOffSecurityHeight/text()", namespaces=namespaces)[0])
    mission.speed = float(mission_config.xpath("wpml:globalTransitionalSpeed/text()", namespaces=namespaces)[0])
    mission.payload_index = int(mission_config.xpath("wpml:payloadInfo/wpml:payloadPositionIndex/text()", namespaces=namespaces)[0])

    # Cerca tutti gli elementi Placemark, cioè i waypoint della missione.
    waypoints = root.xpath("//kml:Placemark", namespaces=namespaces)

    # Ricostruisce un oggetto Waypoint per ogni Placemark.
    for waypoint in waypoints:
        # Recupera le coordinate contenute nell'elemento Point.
        coordinates = waypoint.xpath("kml:Point/kml:coordinates/text()", namespaces=namespaces)[0]

        # Very important: LON, LAT
        # Nel file XML le coordinate sono nell'ordine longitudine, latitudine.
        # split(",") le divide in una lista di stringhe.
        lat = float(coordinates.split(",")[1])
        lon = float(coordinates.split(",")[0])

        # Crea il waypoint con le coordinate estratte.
        wp = Waypoint(lat, lon)

        # Cerca tutte le azioni contenute nel waypoint.
        # Il punto iniziale in .// indica che la ricerca parte
        # dal waypoint corrente e comprende i suoi discendenti.
        actions = waypoint.xpath(".//wpml:action", namespaces=namespaces)

        for action in actions:
            # Recupera il tipo di azione, ad esempio takePhoto o hover.
            actuator_func = action.xpath("wpml:actionActuatorFunc/text()", namespaces=namespaces)[0]

            # Cerca il contenitore dei parametri dell'azione.
            actuator_params = action.xpath("wpml:actionActuatorFuncParam", namespaces=namespaces)

            # Dizionario nel quale raccogliere i parametri trovati.
            params = {}

            # Scorre gli eventuali contenitori dei parametri.
            for actuator_param in actuator_params:
                # Ogni figlio del contenitore rappresenta un parametro.
                for child in actuator_param:
                    # I nomi degli elementi lxml comprendono il namespace
                    # tra parentesi graffe. split('}')[1] recupera
                    # soltanto il nome del parametro.
                    tag_name = child.tag.split('}')[1]

                    # Considera i parametri previsti per il tipo di azione,
                    # secondo il dizionario ACTIONS definito in mission.py.
                    if tag_name in ACTIONS[actuator_func]["parameters"]:
                        tag_value = child.text
                        params[tag_name] = tag_value

            # Ricostruisce l'oggetto Action passando i parametri raccolti.
            # **params espande il dizionario in argomenti con nome.
            action_obj = Action(action_type=actuator_func, **params)

            # Associa l'azione al waypoint corrente.
            wp.add_action(action_obj)

        # Aggiunge alla missione il waypoint completo delle sue azioni.
        # add_waypoint() aggiorna gli identificativi.
        mission.add_waypoint(wp)

    # Rimuove la cartella temporanea utilizzata per l'estrazione.
    shutil.rmtree(temp_dir)

    # Restituisce la missione ricostruita.
    return mission
    # print_mission(mission)


# Permette di eseguire direttamente questo file per effettuare
# una prova di importazione di una missione KMZ.
if __name__ == '__main__':
    # mission = create_mock_mission()
    # mission_to_kmz(mission, "azz")
    kmz_to_mission("mission")
