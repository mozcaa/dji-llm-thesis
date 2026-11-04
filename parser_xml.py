import os
import shutil
from lxml import etree

from mission import Mission, print_mission, create_empty_mission, Waypoint, ACTIONS, Action


# from mission import create_mock_mission


def write_pretty_xml(element, file_path):
    pretty_xml = etree.tostring(
        element, pretty_print=True, xml_declaration=True, encoding='UTF-8'
    )
    with open(file_path, 'wb') as file:
        file.write(pretty_xml)


def create_kmz(mission_name, folder_to_zip):
    output_folder = "out"
    kmz_filename = f"{mission_name}.kmz"
    shutil.make_archive(mission_name, 'zip', folder_to_zip)
    shutil.move(f"{mission_name}.zip", kmz_filename)
    shutil.move(kmz_filename, os.path.join(output_folder, kmz_filename))


def mission_to_kmz(mission, mission_name):
    wpmz_folder = 'out/wpmz'
    template_file = 'template.kml'
    waylines_file = 'waylines.wpml'

    # Define the namespaces
    namespaces = {
        None: 'http://www.opengis.net/kml/2.2',
        'wpml': 'http://www.dji.com/wpmz/1.0.3'
    }

    # Ensure the output folder exists
    os.makedirs(wpmz_folder, exist_ok=True)

    # Create "template.kml"
    kml_template = etree.Element('kml', nsmap=namespaces)
    document_template = etree.SubElement(kml_template, 'Document')
    write_pretty_xml(kml_template, os.path.join(wpmz_folder, template_file))

    # Create "waylines.wpml"
    kml_waylines = etree.Element('kml', nsmap=namespaces)
    document_waylines = etree.SubElement(kml_waylines, 'Document')

    # Add <wpml:missionConfig> and <Folder> to the document
    mission_config = etree.SubElement(document_waylines, f"{{{namespaces['wpml']}}}missionConfig")

    # Add child elements to <wpml:missionConfig>
    etree.SubElement(mission_config, f"{{{namespaces['wpml']}}}globalRTHHeight").text = '30'
    etree.SubElement(mission_config, f"{{{namespaces['wpml']}}}flyToWaylineMode").text = 'safely'
    etree.SubElement(mission_config, f"{{{namespaces['wpml']}}}finishAction").text = 'goHome'
    etree.SubElement(mission_config, f"{{{namespaces['wpml']}}}exitOnRCLost").text = 'executeLostAction'
    etree.SubElement(mission_config, f"{{{namespaces['wpml']}}}executeRCLostAction").text = 'hover'
    etree.SubElement(mission_config, f"{{{namespaces['wpml']}}}takeOffSecurityHeight").text = str(mission.height)
    etree.SubElement(mission_config, f"{{{namespaces['wpml']}}}globalTransitionalSpeed").text = str(mission.speed)

    # Add <wpml:droneInfo>
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
    etree.SubElement(drone_info, f"{{{namespaces['wpml']}}}droneEnumValue").text = '60'
    # etree.SubElement(drone_info, f"{{{namespaces['wpml']}}}droneSubEnumValue").text = '0'

    # Add <wpml:payloadInfo>
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
    etree.SubElement(payload_info, f"{{{namespaces['wpml']}}}payloadEnumValue").text = '42'
    # etree.SubElement(payload_info, f"{{{namespaces['wpml']}}}payloadSubEnumValue").text = '0'

    # 0: Mount position of 1. The M300 RTK and M350 RTK models correspond to the front left of the drone. Other models correspond to the main gimbal.
    # 1: Mount position of 2. The M300 RTK and M350 RTK models correspond to the front right of the drone.
    # 2: Mount position of 3. The M300 RTK and M350 RTK models correspond to the top of the aircraft.
    etree.SubElement(payload_info, f"{{{namespaces['wpml']}}}payloadPositionIndex").text = str(mission.payload_index)

    # Add <Folder>
    folder = etree.SubElement(document_waylines, 'Folder')

    # Add elements inside <Folder>
    etree.SubElement(folder, f"{{{namespaces['wpml']}}}templateId").text = '0'
    etree.SubElement(folder, f"{{{namespaces['wpml']}}}executeHeightMode").text = 'relativeToStartPoint'
    etree.SubElement(folder, f"{{{namespaces['wpml']}}}waylineId").text = '0'
    etree.SubElement(folder, f"{{{namespaces['wpml']}}}distance").text = str(mission.total_distance())
    etree.SubElement(folder, f"{{{namespaces['wpml']}}}duration").text = str(mission.total_time())
    etree.SubElement(folder, f"{{{namespaces['wpml']}}}autoFlightSpeed").text = str(mission.speed)

    for waypoint in mission.waypoints:
        # Add <Placemark>
        placemark = etree.SubElement(folder, 'Placemark')

        # Add <Point>
        point = etree.SubElement(placemark, 'Point')
        coordinates = etree.SubElement(point, 'coordinates')
        # Very important: LON, LAT
        coordinates.text = f"{waypoint.lon},{waypoint.lat}"

        etree.SubElement(placemark, f"{{{namespaces['wpml']}}}index").text = str(waypoint.waypoint_id)
        etree.SubElement(placemark, f"{{{namespaces['wpml']}}}executeHeight").text = str(mission.height)
        etree.SubElement(placemark, f"{{{namespaces['wpml']}}}waypointSpeed").text = str(mission.speed)

        waypoint_heading_param = etree.SubElement(placemark, f"{{{namespaces['wpml']}}}waypointHeadingParam")
        etree.SubElement(waypoint_heading_param, f"{{{namespaces['wpml']}}}waypointHeadingMode").text = 'followWayline'

        waypoint_turn_param = etree.SubElement(placemark, f"{{{namespaces['wpml']}}}waypointTurnParam")
        etree.SubElement(waypoint_turn_param,
                         f"{{{namespaces['wpml']}}}waypointTurnMode").text = 'toPointAndStopWithDiscontinuityCurvature'
        etree.SubElement(waypoint_turn_param, f"{{{namespaces['wpml']}}}waypointTurnDampingDist").text = '0'

        etree.SubElement(placemark, f"{{{namespaces['wpml']}}}useStraightLine").text = '1'

        # Add <wpml:actionGroup>
        action_group = etree.SubElement(placemark, f"{{{namespaces['wpml']}}}actionGroup")

        etree.SubElement(action_group, f"{{{namespaces['wpml']}}}actionGroupId").text = str(waypoint.waypoint_id)
        etree.SubElement(action_group, f"{{{namespaces['wpml']}}}actionGroupStartIndex").text = str(
            waypoint.waypoint_id)
        etree.SubElement(action_group, f"{{{namespaces['wpml']}}}actionGroupEndIndex").text = str(waypoint.waypoint_id)
        etree.SubElement(action_group, f"{{{namespaces['wpml']}}}actionGroupMode").text = 'sequence'

        action_trigger = etree.SubElement(action_group, f"{{{namespaces['wpml']}}}actionTrigger")
        etree.SubElement(action_trigger, f"{{{namespaces['wpml']}}}actionTriggerType").text = 'reachPoint'

        for action in waypoint.actions:
            # add <wpml:action>
            action_element = etree.SubElement(action_group, f"{{{namespaces['wpml']}}}action")
            etree.SubElement(action_element, f"{{{namespaces['wpml']}}}actionId").text = str(action.action_id)
            etree.SubElement(action_element, f"{{{namespaces['wpml']}}}actionActuatorFunc").text = action.action_type

            # add child <wpml:actionActuatorFuncParam>
            action_actuator_func_param = etree.SubElement(action_element,
                                                          f"{{{namespaces['wpml']}}}actionActuatorFuncParam")
            for param, value in action.parameters.items():
                etree.SubElement(action_actuator_func_param, f"{{{namespaces['wpml']}}}{param}").text = str(value)

    write_pretty_xml(kml_waylines, os.path.join(wpmz_folder, waylines_file))
    create_kmz(mission_name, wpmz_folder)


def kmz_to_mission(mission_name):
    out_dir = "out"
    temp_dir = os.path.join(out_dir, "temp")
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

    kml_path = os.path.join(out_dir, f"{mission_name}.kmz")
    shutil.unpack_archive(kml_path, temp_dir, "zip")

    wpml_path = os.path.join(temp_dir, "waylines.wpml")
    if not os.path.exists(wpml_path):
        raise FileNotFoundError(f"{wpml_path} not found in the KMZ archive.")

    with open(wpml_path, "rb") as wpml_file:
        xml_content = wpml_file.read()

    root = etree.fromstring(xml_content)

    namespaces = {
        "kml": "http://www.opengis.net/kml/2.2",
        "wpml": "http://www.dji.com/wpmz/1.0.3"
    }

    mission = create_empty_mission()

    mission_config = root.xpath("//wpml:missionConfig", namespaces=namespaces)[0]

    mission.height = float(mission_config.xpath("wpml:takeOffSecurityHeight/text()", namespaces=namespaces)[0])
    mission.speed = float(mission_config.xpath("wpml:globalTransitionalSpeed/text()", namespaces=namespaces)[0])
    mission.payload_index = int(mission_config.xpath("wpml:payloadInfo/wpml:payloadPositionIndex/text()", namespaces=namespaces)[0])

    waypoints = root.xpath("//kml:Placemark", namespaces=namespaces)
    for waypoint in waypoints:
        coordinates = waypoint.xpath("kml:Point/kml:coordinates/text()", namespaces=namespaces)[0]
        # Very important: LON, LAT
        lat = float(coordinates.split(",")[1])
        lon = float(coordinates.split(",")[0])

        wp = Waypoint(lat, lon)

        actions = waypoint.xpath(".//wpml:action", namespaces=namespaces)
        for action in actions:
            actuator_func = action.xpath("wpml:actionActuatorFunc/text()", namespaces=namespaces)[0]
            actuator_params = action.xpath("wpml:actionActuatorFuncParam", namespaces=namespaces)

            params = {}

            for actuator_param in actuator_params:
                for child in actuator_param:
                    tag_name = child.tag.split('}')[1]
                    if tag_name in ACTIONS[actuator_func]["parameters"]:
                        tag_value = child.text
                        params[tag_name] = tag_value

            action_obj = Action(action_type=actuator_func, **params)
            wp.add_action(action_obj)

        mission.add_waypoint(wp)

    shutil.rmtree(temp_dir)

    return mission
    # print_mission(mission)


if __name__ == '__main__':
    # mission = create_mock_mission()
    # mission_to_kmz(mission, "azz")
    kmz_to_mission("mission")
