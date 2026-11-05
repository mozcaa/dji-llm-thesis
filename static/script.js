/* global maplibregl, $ */

// =========================
// Globals & Constants
// =========================
let map;
let markers = [];
let midlineMarkers = [];
let availableActions = {};

const MAP_CENTER = { lat: 43.062715, lng: 12.551034 };
const MAP_ZOOM = 18;

const ROUTE_SOURCE_ID = 'mission-route-source';
const ROUTE_LAYER_ID = 'mission-route-layer';

const DEFAULT_ACTION_VALUES = {
    payloadPositionIndex: '0',
    gimbalRotateMode: 'absoluteAngle',
    gimbalPitchRotateEnable: '1',
    gimbalYawRotateEnable: '1'
};

// =========================
// Bootstrap
// =========================
function initMap() {
    const apiKey = window.MAPTILER_WEB_API_KEY;
    if (!apiKey) {
        console.error('MapTiler key is missing. Set MAPTILER_WEB_API_KEY in the server environment.');
        showMapError('Map key missing. Set MAPTILER_WEB_API_KEY on the server.');
        return;
    }

    map = new maplibregl.Map({
        container: byId('map'),
        style: `https://api.maptiler.com/maps/satellite/style.json?key=${encodeURIComponent(apiKey)}`,
        center: [MAP_CENTER.lng, MAP_CENTER.lat],
        zoom: MAP_ZOOM,
        attributionControl: true
    });
    map.addControl(new maplibregl.NavigationControl(), 'top-right');
    map.on('click', (event) => addWaypoint(event.lngLat));
    map.on('load', () => {
        document.addEventListener('keydown', handleUndoRedoShortcuts);
        refreshMission();
        addOptionsButtons();
    });
    map.on('error', (event) => console.error('MapLibre error:', event.error));
}

function showMapError(message) {
    const error = document.createElement('div');
    error.className = 'map-error';
    error.textContent = message;
    byId('map').appendChild(error);
}

initMap();

// =========================
// Helpers
// =========================
function byId(id) {
    return document.getElementById(id);
}

function markInputDirtyAndCommit(input, onCommit) {
    input.addEventListener('input', () => {
        input.style.backgroundColor = '#fff3bf';
    });

    input.addEventListener('blur', () => {
        onCommit(input.value);
        input.style.backgroundColor = '';
    });
}

function clearMapArtifacts() {
    markers.forEach((marker) => marker.remove());
    markers = [];

    midlineMarkers.forEach((marker) => marker.remove());
    midlineMarkers = [];

    if (map?.getLayer(ROUTE_LAYER_ID)) {
        map.removeLayer(ROUTE_LAYER_ID);
    }
    if (map?.getSource(ROUTE_SOURCE_ID)) {
        map.removeSource(ROUTE_SOURCE_ID);
    }
}

function ensureOk(response, errorMessage) {
    if (!response.ok) {
        throw new Error(errorMessage);
    }
    return response;
}

function postJson(url, payload) {
    return fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
}

function refreshMission() {
    getMission();
}

// =========================
// Map & Rendering
// =========================
function renderMissionToMap(data) {
    const globalParametersEl = byId('globalParameters');//da togliere
    const waypointsListEl = byId('waypointsList'); 

    globalParametersEl.innerHTML = '<strong>Parameters</strong>'; //da togliere
    waypointsListEl.innerHTML = '<strong>Waypoints</strong>';

    Object.entries(data).forEach(([key, value]) => {
        if (typeof value !== 'number' && typeof value !== 'string') {
            return;
        }

        const paramElement = document.createElement('div');
        paramElement.classList.add('actions-list');
        paramElement.style.display = 'flex';
        paramElement.style.alignItems = 'center';
        paramElement.style.marginBottom = '5px';

        const label = document.createElement('span');
        label.textContent = `${key}: `;
        label.style.flex = '1';
        label.style.fontWeight = 'bold';
        label.style.marginRight = '10px';

        const input = document.createElement('input');
        input.type = 'text';
        input.value = value;
        input.classList.add('parameter-input');

        markInputDirtyAndCommit(input, (newValue) => { //toglierer
            updateGlobalParameter(key, newValue);
        });

        paramElement.appendChild(label);
        paramElement.appendChild(input);
        globalParametersEl.appendChild(paramElement);
    });

    clearMapArtifacts();

    const polylinePath = [];
    data.waypoints.forEach((waypoint) => {
        addWaypointMarker(waypoint);
        addWaypointToSidebar(waypoint);
        polylinePath.push([waypoint.lon, waypoint.lat]);
    });

    if (polylinePath.length > 1) {
        drawPolylineAndMidpoints(polylinePath);
    }
}

function drawPolylineAndMidpoints(polylinePath) {
    map.addSource(ROUTE_SOURCE_ID, {
        type: 'geojson',
        data: {
            type: 'Feature',
            properties: {},
            geometry: { type: 'LineString', coordinates: polylinePath }
        }
    });
    map.addLayer({
        id: ROUTE_LAYER_ID,
        type: 'line',
        source: ROUTE_SOURCE_ID,
        layout: { 'line-join': 'round', 'line-cap': 'round' },
        paint: { 'line-color': '#ff2bd6', 'line-opacity': 1, 'line-width': 5 }
    });

    for (let i = 0; i < polylinePath.length - 1; i += 1) {
        const midpoint = {
            lng: (polylinePath[i][0] + polylinePath[i + 1][0]) / 2,
            lat: (polylinePath[i][1] + polylinePath[i + 1][1]) / 2
        };

        const element = document.createElement('button');
        element.type = 'button';
        element.className = 'map-midpoint-marker';
        element.textContent = '+';
        element.title = 'Click to add a waypoint';
        element.setAttribute('aria-label', 'Add waypoint here');
        element.addEventListener('click', (event) => {
            event.stopPropagation();
            addWaypointAt(midpoint, i + 1);
        });

        const midMarker = new maplibregl.Marker({ element, anchor: 'center' })
            .setLngLat([midpoint.lng, midpoint.lat])
            .addTo(map);
        midlineMarkers.push(midMarker);
    }
}

function addWaypointMarker(waypoint) {
    const element = document.createElement('div');
    element.className = 'map-waypoint-marker';
    element.textContent = String(waypoint.waypoint_id);
    element.title = `WP ${waypoint.waypoint_id}: ${waypoint.actions.length} actions`;
    element.setAttribute('aria-label', element.title);

    const marker = new maplibregl.Marker({ element, anchor: 'center', draggable: true })
        .setLngLat([waypoint.lon, waypoint.lat])
        .addTo(map);

    marker.on('dragend', () => {
        const position = marker.getLngLat();
        waypoint.lat = position.lat;
        waypoint.lon = position.lng;
        updateWaypoint(waypoint);
    });

    markers.push(marker);
}

// =========================
// Sidebar UI
// =========================
function addOptionsButtons() {
    const optionsDiv = byId('options');

    const saveButton = document.createElement('button');
    saveButton.id = 'saveButton';
    saveButton.classList.add('option-button');
    saveButton.innerText = 'Save';

    const loadButton = document.createElement('button');
    loadButton.id = 'loadButton';
    loadButton.classList.add('option-button');
    loadButton.innerText = 'Load';

    const undoButton = document.createElement('button');
    undoButton.id = 'undoButton';
    undoButton.classList.add('option-button');
    undoButton.innerText = 'Undo';

    const redoButton = document.createElement('button');
    redoButton.id = 'redoButton';
    redoButton.classList.add('option-button');
    redoButton.innerText = 'Redo';

    saveButton.addEventListener('click', () => {
        window.location.href = '/save_mission';
    });

    loadButton.addEventListener('click', () => {
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.id = 'fileInput';
        fileInput.click();

        fileInput.addEventListener('change', () => {
            loadMission(fileInput);
        });
    });

    undoButton.addEventListener('click', () => {
        undoMission();
    });

    redoButton.addEventListener('click', () => {
        redoMission();
    });

    optionsDiv.appendChild(saveButton);
    optionsDiv.appendChild(loadButton);
    optionsDiv.appendChild(undoButton);
    optionsDiv.appendChild(redoButton);
}

function handleUndoRedoShortcuts(event) {
    const target = event.target;
    const isTypingField = target &&
        (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable);
    if (isTypingField) {
        return;
    }

    const modifierPressed = event.ctrlKey || event.metaKey;
    if (!modifierPressed) {
        return;
    }

    const key = event.key.toLowerCase();
    if (key === 'z' && !event.shiftKey) {
        event.preventDefault();
        undoMission();
        return;
    }

    if ((key === 'z' && event.shiftKey) || key === 'y') {
        event.preventDefault();
        redoMission();
    }
}
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////Commento notabile mentre scrollo
function addWaypointToSidebar(waypoint) {
    const waypointsListEl = byId('waypointsList');

    const waypointElement = document.createElement('div');
    waypointElement.id = `waypoint-${waypoint.waypoint_id}`;

    const latFixed = waypoint.lat.toFixed(6);
    const lonFixed = waypoint.lon.toFixed(6); 
    waypointElement.innerHTML = `<b>${waypoint.waypoint_id}: (${latFixed}, ${lonFixed})</b> <b><a href="#" class="remove-waypoint">del</a></b>`; //Aggiunegere il bottone anche per speed e quote

    waypointElement.querySelector('.remove-waypoint').addEventListener('click', (event) => {
        event.stopPropagation();
        removeWaypoint(waypoint.waypoint_id);
    });
 //aggiungere il markInputDirtyAndCommit qui che richiama la funzione di aggiornamento quota e v
    const actionsList = document.createElement('div');
    actionsList.classList.add('actions-list');
    actionsList.innerHTML = '<u><b>Actions</b></u> <b><a href="#" class="add-action">add</a></b>';
    const actionItemsContainer = document.createElement('div');
    actionItemsContainer.classList.add('action-items');

    actionsList.querySelector('.add-action').addEventListener('click', (event) => {
        event.stopPropagation();
        getAvailableActions(waypoint.waypoint_id);
    });

    waypoint.actions.forEach((action) => {
        const actionElement = document.createElement('div');
        actionElement.id = `action-${waypoint.waypoint_id}-${action.action_id}`;
        actionElement.dataset.actionId = `${action.action_id}`;
        actionElement.classList.add('action-draggable');
        actionElement.innerHTML = `<b>${action.action_id} - ${action.action_type}</b> <b><a href="#" class="remove-action">del</a></b>`;

        actionElement.querySelector('.remove-action').addEventListener('click', (event) => {
            event.stopPropagation();
            removeAction(waypoint.waypoint_id, action.action_id);
        });

        const parametersList = document.createElement('div');
        Object.entries(action.parameters).forEach(([param, value]) => {
            const paramElement = document.createElement('div');
            paramElement.style.display = 'flex';

            const label = document.createElement('span');
            label.textContent = `${param}: `;
            label.style.flex = '1';
            label.style.fontStyle = 'italic';

            const input = document.createElement('input');
            input.type = 'text';
            input.value = value;
            input.classList.add('parameter-input');

            markInputDirtyAndCommit(input, (newValue) => {
                const [, waypointId, actionId] = actionElement.id.split('-');
                updateAction(waypointId, actionId, param, newValue);
            });

            paramElement.appendChild(label);
            paramElement.appendChild(input);
            parametersList.appendChild(paramElement);
        });

        actionElement.appendChild(parametersList);
        actionItemsContainer.appendChild(actionElement);
    });

    actionsList.appendChild(actionItemsContainer);
    enableActionSorting(actionItemsContainer, waypoint.waypoint_id);
    waypointElement.appendChild(actionsList);
    waypointsListEl.appendChild(waypointElement);
}

function enableActionSorting(actionItemsContainer, waypointId) {
    if (typeof $ === 'undefined' || !$.fn.sortable) {
        return;
    }

    $(actionItemsContainer).sortable({
        items: '> div[id^="action-"]',
        axis: 'y',
        tolerance: 'pointer',
        placeholder: 'action-sort-placeholder',
        cancel: 'input, textarea, select, a, button',
        update() {
            const orderedActionIds = Array.from(
                actionItemsContainer.querySelectorAll('div[id^="action-"]')
            )
                .map((el) => Number.parseInt(el.dataset.actionId, 10))
                .filter((id) => Number.isInteger(id));

            reorderActions(waypointId, orderedActionIds);
        }
    });
}

function populateActionSelect() {
    const actionSelect = byId('actionSelect');
    actionSelect.innerHTML = '';

    const defaultOption = document.createElement('option');
    defaultOption.value = '';
    defaultOption.textContent = 'Select an action';
    actionSelect.appendChild(defaultOption);

    Object.keys(availableActions).forEach((action) => {
        const option = document.createElement('option');
        option.value = action;
        option.textContent = action;
        actionSelect.appendChild(option);
    });

    updateParameters();
}

function updateParameters() {
    const selectedAction = byId('actionSelect').value;
    const container = byId('parametersContainer');
    container.innerHTML = '';

    if (!selectedAction) {
        return;
    }

    const parameters = availableActions[selectedAction]?.parameters || [];

    parameters.forEach((param) => {
        const inputGroup = document.createElement('div');
        inputGroup.classList.add('form-group');

        const label = document.createElement('label');
        label.textContent = param;

        const input = document.createElement('input');
        input.type = 'text';
        input.name = param;

        if (DEFAULT_ACTION_VALUES[param] !== undefined) {
            input.value = DEFAULT_ACTION_VALUES[param];
        }

        inputGroup.appendChild(label);
        inputGroup.appendChild(input);
        container.appendChild(inputGroup);
    });
}

function handleAddButtonClick(waypointId) {
    const selectedAction = byId('actionSelect').value;
    if (!selectedAction) {
        return;
    }

    const params = {};
    const parameters = availableActions[selectedAction]?.parameters || [];

    parameters.forEach((param) => {
        const input = document.querySelector(`[name=${param}]`);
        if (input) {
            params[param] = input.value;
        }
    });

    addAction(waypointId, selectedAction, params);
    $('#popup').dialog('close');
}

// =========================
// API Calls
// =========================
function getMission() {
    fetch('/get_mission')
        .then((response) => ensureOk(response, 'Failed to get mission from server.'))
        .then((response) => response.json())
        .then((data) => {
            renderMissionToMap(data);
        })
        .catch((error) => {
            console.error('Error loading mission:', error);
        });
}

function loadMission(fileInput) {
    if (fileInput.files.length <= 0) {
        alert('Please select a file to upload');
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    fetch('/load_mission', {
        method: 'POST',
        body: formData
    })
        .then((response) => ensureOk(response, 'Failed to load mission on server.'))
        .then((response) => response.json())
        .then((data) => {
            console.log(data.message);
            refreshMission();
        })
        .catch((error) => {
            console.error('Error loading mission:', error);
        });
}

function getAvailableActions(waypointId) {
    fetch('/available_actions')
        .then((response) => ensureOk(response, 'Failed to retrieve available actions.'))
        .then((response) => response.json())
        .then((data) => {
            availableActions = data;
            populateActionSelect();

            $('#popup').dialog({
                modal: true,
                width: '30%',
                height: 'auto',
                buttons: {
                    Add() {
                        handleAddButtonClick(waypointId);
                    }
                }
            });
        })
        .catch((error) => {
            console.error('Error retrieving available actions:', error);
        });
}

function undoMission() {
    fetch('/undo', { method: 'POST' })
        .then((response) => ensureOk(response, 'Nothing to undo'))
        .then((response) => response.json())
        .then((data) => {
            if (data.mission) {
                renderMissionToMap(data.mission);
            } else {
                refreshMission();
            }
        })
        .catch((error) => {
            console.warn('Undo not applied:', error.message);
        });
}

function redoMission() {
    fetch('/redo', { method: 'POST' })
        .then((response) => ensureOk(response, 'Nothing to redo'))
        .then((response) => response.json())
        .then((data) => {
            if (data.mission) {
                renderMissionToMap(data.mission);
            } else {
                refreshMission();
            }
        })
        .catch((error) => {
            console.warn('Redo not applied:', error.message);
        });
}

function addWaypoint(latLng) {
    const payload = { lat: latLng.lat, lon: latLng.lng }; //aggiungere i 2 parametri

    postJson('/add_waypoint', payload)
        .then((response) => ensureOk(response, 'Failed to add waypoint on server.'))
        .then((response) => response.json())
        .then((data) => {
            console.log(data.message);
            refreshMission();
        })
        .catch((error) => {
            console.error('Error adding waypoint:', error);
        });
}

function addWaypointAt(latLng, index) {
    const payload = { lat: latLng.lat, lon: latLng.lng, index };//aggiungere i 2 parametri

    postJson('/add_waypoint_at', payload)
        .then((response) => ensureOk(response, 'Failed to add waypoint on server.'))
        .then((response) => response.json())
        .then((data) => {
            console.log(data.message);
            refreshMission();
        })
        .catch((error) => {
            console.error('Error adding waypoint at:', error);
        });
}

function updateWaypoint(waypoint) {
    postJson('/update_waypoint', {
        waypoint_id: waypoint.waypoint_id,
        lat: waypoint.lat,
        lon: waypoint.lon
    })
        .then((response) => ensureOk(response, 'Failed to update waypoint on server.'))
        .then((response) => response.json())
        .then((data) => {
            console.log('Waypoint updated on server:', data);
            refreshMission();
        })
        .catch((error) => {
            console.error('Error updating waypoint on server:', error);
        });
}

/*
function updateSpeed(waypoint) {
    postJson('/update_waypoint_speed', {
        waypoint_id: waypoint.waypoint_id,
        speed: waypoint.speed
    })
        .then((response) => ensureOk(response, 'Failed to update waypoint on server.'))
        .then((response) => response.json())
        .then((data) => {
            console.log('Waypoint updated on server:', data);
            refreshMission();
        })
        .catch((error) => {
            console.error('Error updating waypoint on server:', error);
        });
}

/*
function updateQuote(waypoint) {
    postJson('/update_waypoint_quote', {
        waypoint_id: waypoint.waypoint_id,
        quote: waypoint.quote
    })
        .then((response) => ensureOk(response, 'Failed to update waypoint on server.'))
        .then((response) => response.json())
        .then((data) => {
            console.log('Waypoint updated on server:', data);
            refreshMission();
        })
        .catch((error) => {
            console.error('Error updating waypoint on server:', error);
        });
}


*/
function updateGlobalParameter(variable, value) { //tutta da togliere
    postJson('/update_global_parameter', { variable, value })
        .then((response) => ensureOk(response, 'Failed to update global parameter on server.'))
        .then((response) => response.json())
        .then((data) => {
            console.log('Global parameter updated on server:', data);
            refreshMission();
        })
        .catch((error) => {
            console.error('Error updating global parameter on server:', error);
        });
}

function updateAction(waypointId, actionId, param, value) {
    postJson('/update_action', {
        waypoint_id: waypointId,
        action_id: actionId,
        action_type: param,
        parameter: value
    })
        .then((response) => ensureOk(response, 'Failed to update action on server.'))
        .then((response) => response.json())
        .then((data) => {
            console.log('Action updated on server:', data);
            refreshMission();
        })
        .catch((error) => {
            console.error('Error updating action on server:', error);
        });
}

function removeWaypoint(waypointId) {
    postJson('/remove_waypoint', { waypoint_id: waypointId })
        .then((response) => ensureOk(response, 'Failed to remove waypoint on server.'))
        .then((response) => response.json())
        .then((data) => {
            console.log(data.message);
            refreshMission();
        })
        .catch((error) => {
            console.error('Error removing waypoint:', error);
        });
}

function addAction(waypointId, actionType, parameters) {
    postJson('/add_action', {
        waypoint_id: waypointId,
        action_type: actionType,
        parameters
    })
        .then((response) => ensureOk(response, 'Failed to add action on server.'))
        .then((response) => response.json())
        .then((data) => {
            console.log(data.message);
            refreshMission();
        })
        .catch((error) => {
            console.error('Error adding action:', error);
        });
}

function removeAction(waypointId, actionId) {
    postJson('/remove_action', {
        waypoint_id: waypointId,
        action_id: actionId
    })
        .then((response) => ensureOk(response, 'Failed to remove action on server.'))
        .then((response) => response.json())
        .then((data) => {
            console.log(data.message);
            refreshMission();
        })
        .catch((error) => {
            console.error('Error removing action:', error);
        });
}

function reorderActions(waypointId, actionIds) {
    postJson('/reorder_actions', {
        waypoint_id: waypointId,
        action_ids: actionIds
    })
        .then((response) => ensureOk(response, 'Failed to reorder actions on server.'))
        .then((response) => response.json())
        .then((data) => {
            console.log(data.message);
            refreshMission();
        })
        .catch((error) => {
            console.error('Error reordering actions:', error);
            refreshMission();
        });
}
