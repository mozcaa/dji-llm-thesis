
// Indica al linter che MapLibre e jQuery sono caricati separatamente dalla pagina.
/* global maplibregl, $ */

// =========================
// Globals & Constants
// =========================

let map;
// Marker dei waypoint visibili, da rimuovere quando si ridisegna.
let markers = [];
// Marker dei pulsanti + tra due waypoint.
let midlineMarkers = [];
// Dizionario delle azioni ricevuto dall'endpoint /available_actions.
let availableActions = {};

const MAP_CENTER = { lat: 43.062715, lng: 12.551034 };
const MAP_ZOOM = 18;

const ROUTE_SOURCE_ID = 'mission-route-source';
// Nome con cui MapLibre identifica il layer della linea.
const ROUTE_LAYER_ID = 'mission-route-layer';

// Valori proposti quando si crea una nuova azione nel popup.
const DEFAULT_ACTION_VALUES = {
    payloadPositionIndex: '0',
    gimbalRotateMode: 'absoluteAngle',
    gimbalPitchRotateEnable: '1',
    gimbalYawRotateEnable: '1'
};


// =========================
// Helpers
// =========================

// Recupera un elemento HTML tramite il suo ID.
function byId(id) {
    return document.getElementById(id);
}

// Controlla la risposta HTTP e segnala un errore se la richiesta non è andata a buon fine.
function ensureOk(response, errorMessage) {
    // fetch non lancia errori per risposte HTTP 4xx/5xx: li controlliamo qui.
    if (!response.ok) {
        throw new Error(errorMessage);
    }
    return response;
}

// Invia una richiesta POST al backend, convertendo il payload in JSON.
function postJson(url, payload) {
    // fetch restituisce una Promise: la risposta arriverà in modo asincrono.
    return fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)  // Serializza l'oggetto JS nel corpo della richiesta.
    });
}

// Evidenzia un input modificato e richiama onCommit quando l'utente esce dal campo.
function markInputDirtyAndCommit(input, onCommit) {
    let lastValue = input.value;  // Ricorda il valore iniziale per evitare POST inutili.

    // L'evento input scatta mentre si digita.
    input.addEventListener('input', () => {
        input.style.backgroundColor = '#fff3bf';
    });

    // blur scatta quando il campo perde il focus.
    input.addEventListener('blur', () => {
        // La callback parte solo se il valore è effettivamente cambiato.
        if (input.value !== lastValue) {
            lastValue = input.value;
            onCommit(input.value);  // Chiama la callback associata al campo (es. updateSpeed).
        }
        input.style.backgroundColor = '';
    });
}


// =========================
// API Calls
// =========================

// Recupera la missione dal server e aggiorna la sua rappresentazione grafica.
function getMission() {
    // Richiesta GET: Flask restituisce mission.to_dict() come JSON.
    fetch('/get_mission')
        // Se la risposta HTTP non è OK, interrompe la catena .then.
        .then((response) => ensureOk(response, 'Failed to get mission from server.'))
        .then((response) => response.json())  // Trasforma la risposta JSON in oggetti JavaScript.
        // data contiene il dizionario JS ricostruito dalla risposta.
        .then((data) => {
            renderMissionToMap(data);
        })
        .catch((error) => {
            console.error('Error loading mission:', error);
        });
}

// Ricarica la missione dal backend dopo una modifica.
function refreshMission() {
    getMission();
}

// Carica un file KMZ selezionato dall'utente e aggiorna il planner.
function loadMission(fileInput) {
    // Evita di caricare se il selettore non contiene file.
    if (fileInput.files.length <= 0) {
        alert('Please select a file to upload');
        return;
    }

    const formData = new FormData();  // FormData serve a inviare il file come multipart/form-data.
    // La chiave "file" coincide con request.files["file"] in Flask.
    formData.append('file', fileInput.files[0]);

    // Non impostiamo Content-Type: il browser aggiunge il boundary corretto.
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

// Chiede al backend le azioni disponibili e apre il popup di scelta.
function getAvailableActions(waypointId) {
    fetch('/available_actions')
        .then((response) => ensureOk(response, 'Failed to retrieve available actions.'))
        .then((response) => response.json())
        .then((data) => {
            availableActions = data;  // Salva la descrizione dei parametri delle azioni.
            populateActionSelect();

            // jQuery UI gestisce la finestra modale delle azioni.
            $('#popup').dialog({
                modal: true,
                width: '30%',
                height: 'auto',
                buttons: {
                    // La funzione Add viene eseguita al clic sul pulsante del popup.
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

// Invia al backend le coordinate del nuovo waypoint aggiunto in fondo alla missione.
function addWaypoint(latLng) {
    // latLng proviene dall'evento di MapLibre.
    const payload = { lat: latLng.lat, lon: latLng.lng };  // Quota e velocità iniziali sono gestite da Flask.

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

// Inserisce un waypoint tra due punti esistenti, nella posizione indicata.
function addWaypointAt(latLng, index) {
    // { index } equivale a { index: index }.
    const payload = { lat: latLng.lat, lon: latLng.lng, index };  // index indica dove inserire il nuovo waypoint.

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

// Invia al server le nuove coordinate di un waypoint trascinato sulla mappa.
function updateWaypoint(waypoint) {
    // Il backend identifica il waypoint tramite waypoint_id.
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

// Controlla e aggiorna la velocità del tratto in uscita da un waypoint.
function updateSpeed(waypoint, newspeed) {
    const speed = Number(newspeed);  // Converte il valore ricevuto in numero.

    // Scarta stringhe vuote, numeri non finiti e velocità non positive.
    if (newspeed.trim() === '' || !Number.isFinite(speed) || speed <= 0) {
        // In caso di input errato ripristina il valore presente sul server.
        refreshMission();
        return;
    }

    postJson('/update_waypoint/speed', {
        waypoint_id: waypoint.waypoint_id,
        speed: speed
    })
        .then((response) => ensureOk(response, 'Failed to update waypoint on server.'))
        .then((response) => response.json())
        .then((data) => {
            console.log('Waypoint updated on server:', data);
            refreshMission();
        })
        .catch((error) => {
            console.error('Error updating waypoint on server:', error);
            refreshMission();
        });
}

// Controlla e aggiorna la quota del waypoint.
function updateQuote(waypoint, newquote) {
    const quote = Number(newquote);  // Converte il valore ricevuto in numero.

    // La quota può essere anche 0: qui controlliamo che sia un numero valido.
    if (newquote.trim() === '' || !Number.isFinite(quote)) {
        refreshMission();
        return;
    }

    postJson('/update_waypoint/quote', {
        waypoint_id: waypoint.waypoint_id,
        quote: quote
    })
        .then((response) => ensureOk(response, 'Failed to update waypoint on server.'))
        .then((response) => response.json())
        .then((data) => {
            console.log('Waypoint updated on server:', data);
            refreshMission();
        })
        .catch((error) => {
            console.error('Error updating waypoint on server:', error);
            refreshMission();
        });
}

// Aggiorna il parametro globale della missione (attualmente payloadIndex).
function updateGlobalParameter(variable, value) {
    // Il server accetta come variable soltanto "payloadIndex".
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

// Modifica un parametro di una delle azioni associate a un waypoint.
function updateAction(waypointId, actionId, param, value) {
    postJson('/update_action', {
        waypoint_id: waypointId,
        action_id: actionId,
        // In questa API action_type contiene il NOME del parametro da cambiare.
        action_type: param,
        // parameter contiene il nuovo valore.
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

// Elimina un waypoint tramite il relativo endpoint Flask.
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

// Aggiunge un'azione con i suoi parametri a un waypoint.
function addAction(waypointId, actionType, parameters) {
    postJson('/add_action', {
        waypoint_id: waypointId,
        action_type: actionType,
        // Forma abbreviata di "parameters: parameters".
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

// Rimuove un'azione dal waypoint indicato.
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

// Invia al server il nuovo ordine delle azioni dopo il trascinamento nella sidebar.
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

// Annulla l'ultima modifica e aggiorna l'interfaccia con lo stato ripristinato.
function undoMission() {
    // L'Undo vero e proprio viene eseguito dalla cronologia Python.
    fetch('/undo', { method: 'POST' })
        .then((response) => ensureOk(response, 'Nothing to undo'))
        .then((response) => response.json())
        .then((data) => {
            // Flask può includere la missione già aggiornata nella risposta.
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

// Ripristina una modifica annullata e aggiorna l'interfaccia.
function redoMission() {
    // Come per Undo, gli stati precedenti sono gestiti nel backend.
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


// =========================
// Map & Rendering
// =========================

// Mostra un messaggio di errore sopra la mappa se la configurazione non è disponibile.
function showMapError(message) {
    const error = document.createElement('div');
    error.className = 'map-error';
    error.textContent = message;
    byId('map').appendChild(error);
}

// Rimuove marker, punti intermedi e linea del percorso prima di ridisegnarli.
function clearMapArtifacts() {
    // remove() stacca ogni marker dalla mappa.
    markers.forEach((marker) => marker.remove());
    // Svuota anche l'array locale, così non conserva vecchi riferimenti.
    markers = [];

    midlineMarkers.forEach((marker) => marker.remove());
    midlineMarkers = [];

    if (map?.getLayer(ROUTE_LAYER_ID)) {  // ?. evita errori se la mappa non è ancora inizializzata.
        map.removeLayer(ROUTE_LAYER_ID);
    }
    // MapLibre richiede di togliere il layer prima della sua source.
    if (map?.getSource(ROUTE_SOURCE_ID)) {
        map.removeSource(ROUTE_SOURCE_ID);
    }
}

// Disegna il percorso e i pulsanti + per inserire waypoint tra due punti.
function drawPolylineAndMidpoints(polylinePath) {
    map.addSource(ROUTE_SOURCE_ID, {  // Registra i dati GeoJSON del percorso.
        type: 'geojson',
        data: {
            type: 'Feature',
            properties: {},
            // Il percorso è una LineString con l'elenco delle coordinate.
            geometry: { type: 'LineString', coordinates: polylinePath }
        }
    });
    // Il layer usa i dati della source registrata sopra.
    map.addLayer({
        id: ROUTE_LAYER_ID,
        type: 'line',
        source: ROUTE_SOURCE_ID,
        layout: { 'line-join': 'round', 'line-cap': 'round' },
        paint: { 'line-color': '#ff2bd6', 'line-opacity': 1, 'line-width': 5 }
    });

    // Con N punti esistono N-1 tratti, ciascuno con un pulsante +.
    for (let i = 0; i < polylinePath.length - 1; i += 1) {
        const midpoint = {
            // Media aritmetica delle longitudini dei due estremi.
            lng: (polylinePath[i][0] + polylinePath[i + 1][0]) / 2,
            // Media aritmetica delle latitudini dei due estremi.
            lat: (polylinePath[i][1] + polylinePath[i + 1][1]) / 2
        };

        const element = document.createElement('button');
        element.type = 'button';
        element.className = 'map-midpoint-marker';
        element.textContent = '+';
        element.title = 'Click to add a waypoint';
        element.setAttribute('aria-label', 'Add waypoint here');
        element.addEventListener('click', (event) => {
            event.stopPropagation();  // Evita che il clic sul + aggiunga anche un waypoint sulla mappa.
            addWaypointAt(midpoint, i + 1);
        });

        // Crea il marker del pulsante + al centro del tratto.
        const midMarker = new maplibregl.Marker({ element, anchor: 'center' })
            .setLngLat([midpoint.lng, midpoint.lat])
            .addTo(map);
        midlineMarkers.push(midMarker);
    }
}

// Mostra un waypoint sulla mappa e gestisce il trascinamento delle sue coordinate.
function addWaypointMarker(waypoint) {
    const element = document.createElement('div');
    element.className = 'map-waypoint-marker';
    // Usa l'ID del waypoint come testo visibile del marker.
    element.textContent = String(waypoint.waypoint_id);
    // Tooltip: mostra anche quante azioni contiene il waypoint.
    element.title = `WP ${waypoint.waypoint_id}: ${waypoint.actions.length} actions`;
    element.setAttribute('aria-label', element.title);

    // draggable abilita lo spostamento manuale sulla mappa.
    const marker = new maplibregl.Marker({ element, anchor: 'center', draggable: true })
        .setLngLat([waypoint.lon, waypoint.lat])
        .addTo(map);

    marker.on('dragend', () => {  // Al rilascio aggiorna le coordinate anche nel backend.
        // Restituisce un oggetto con position.lat e position.lng.
        const position = marker.getLngLat();
        waypoint.lat = position.lat;
        waypoint.lon = position.lng;
        updateWaypoint(waypoint);
    });

    // Conserva il marker per poterlo eliminare al prossimo refresh.
    markers.push(marker);
}

// Ricostruisce sidebar, marker e percorso a partire dalla missione ricevuta in JSON.
function renderMissionToMap(data) {
    const globalParametersEl = byId('globalParameters');
    const waypointsListEl = byId('waypointsList');

    // Ricrea il contenuto: evita campi duplicati dopo ogni aggiornamento.
    globalParametersEl.innerHTML = '<strong>Parameters</strong>';
    waypointsListEl.innerHTML = '<strong>Waypoints</strong>';

    // Object.entries restituisce coppie [nomeProprietà, valore].
    Object.entries(data).forEach(([key, value]) => {  // Attraversa i campi globali ricevuti dal server.
        if (typeof value !== 'number' && typeof value !== 'string') {  // Esclude l'array dei waypoint.
            return;
        }

        // Ogni parametro globale viene trasformato in una riga HTML.
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
        // Imposta il valore appena ricevuto da Flask.
        input.value = value;
        input.classList.add('parameter-input');

        // Associa la modifica del campo alla chiamata POST.
        markInputDirtyAndCommit(input, (newValue) => {
            updateGlobalParameter(key, newValue);
        });

        paramElement.appendChild(label);
        paramElement.appendChild(input);
        globalParametersEl.appendChild(paramElement);
    });

    clearMapArtifacts();  // Elimina i vecchi elementi grafici prima di ricrearli.

    // Coordinate in ordine [lon, lat] per costruire la linea.
    const polylinePath = [];
    // Scorre tutti i waypoint della missione.
    data.waypoints.forEach((waypoint) => {
        addWaypointMarker(waypoint);
        addWaypointToSidebar(waypoint);
        polylinePath.push([waypoint.lon, waypoint.lat]);  // MapLibre usa l'ordine [longitudine, latitudine].
    });

    // Con un solo punto non si può disegnare un segmento.
    if (polylinePath.length > 1) {
        drawPolylineAndMidpoints(polylinePath);
    }
}


// =========================
// Sidebar UI
// =========================

// Riempie il menu a tendina del popup con i tipi di azione disponibili.
function populateActionSelect() {
    // Recupera la select del popup, non quella dei waypoint.
    const actionSelect = byId('actionSelect');
    actionSelect.innerHTML = '';

    const defaultOption = document.createElement('option');
    defaultOption.value = '';
    defaultOption.textContent = 'Select an action';
    actionSelect.appendChild(defaultOption);

    // Object.keys ricava i nomi delle azioni disponibili.
    Object.keys(availableActions).forEach((action) => {  // Un'opzione per ogni tipo di azione.
        const option = document.createElement('option');
        option.value = action;
        option.textContent = action;
        actionSelect.appendChild(option);
    });

    // Crea i campi per la prima opzione selezionata (se presente).
    updateParameters();
}

// Crea nel popup gli input richiesti dall'azione selezionata.
function updateParameters() {
    // Prende il tipo scelto nel menu a tendina.
    const selectedAction = byId('actionSelect').value;
    const container = byId('parametersContainer');
    container.innerHTML = '';

    // Se non c'è alcuna azione selezionata, il popup resta vuoto.
    if (!selectedAction) {
        return;
    }

    const parameters = availableActions[selectedAction]?.parameters || [];  // Usa [] se l'azione non ha parametri.

    parameters.forEach((param) => {
        const inputGroup = document.createElement('div');
        inputGroup.classList.add('form-group');

        const label = document.createElement('label');
        label.textContent = param;

        const input = document.createElement('input');
        input.type = 'text';
        input.name = param;

        // Alcuni parametri hanno un valore predefinito, altri restano vuoti.
        if (DEFAULT_ACTION_VALUES[param] !== undefined) {
            input.value = DEFAULT_ACTION_VALUES[param];
        }

        inputGroup.appendChild(label);
        inputGroup.appendChild(input);
        container.appendChild(inputGroup);
    });
}

// Legge i parametri inseriti nel popup e chiede al server di aggiungere l'azione.
function handleAddButtonClick(waypointId) {
    const selectedAction = byId('actionSelect').value;
    if (!selectedAction) {
        return;
    }

    // Oggetto che raccoglierà tutte le coppie parametro-valore.
    const params = {};
    const parameters = availableActions[selectedAction]?.parameters || [];

    parameters.forEach((param) => {
        // Cerca l'input del popup con l'attributo name corrispondente.
        const input = document.querySelector(`[name=${param}]`);
        if (input) {
            params[param] = input.value;  // Costruisce il dizionario dei parametri dell'azione.
        }
    });

    addAction(waypointId, selectedAction, params);
    // Chiude la finestra dopo aver richiesto l'aggiunta dell'azione.
    $('#popup').dialog('close');
}

// Abilita il riordino delle azioni con drag & drop tramite jQuery UI.
function enableActionSorting(actionItemsContainer, waypointId) {
    // Senza jQuery UI Sortable il trascinamento non sarebbe disponibile.
    if (typeof $ === 'undefined' || !$.fn.sortable) {
        return;
    }

    $(actionItemsContainer).sortable({
        // Seleziona soltanto le righe azione, non i loro campi interni.
        items: '> div[id^="action-"]',
        axis: 'y',
        tolerance: 'pointer',
        placeholder: 'action-sort-placeholder',
        // Trascinare un input o un link non deve riordinare l'azione.
        cancel: 'input, textarea, select, a, button',
        // Callback eseguita una volta terminato un riordinamento.
        update() {
            // querySelectorAll restituisce una NodeList; Array.from la rende un array.
            const orderedActionIds = Array.from(
                actionItemsContainer.querySelectorAll('div[id^="action-"]')
            )
                .map((el) => Number.parseInt(el.dataset.actionId, 10))  // Legge gli ID nell'ordine attuale del DOM.
                // Mantiene solo ID interi validi.
                .filter((id) => Number.isInteger(id));

            reorderActions(waypointId, orderedActionIds);
        }
    });
}

// Crea la sezione di un waypoint con coordinate, quota, velocità e azioni modificabili.
function addWaypointToSidebar(waypoint) {
    const waypointsListEl = byId('waypointsList');

    const waypointElement = document.createElement('div');
    waypointElement.id = `waypoint-${waypoint.waypoint_id}`;  // ID HTML univoco per questo waypoint.

    // Mostra 6 cifre decimali senza cambiare le coordinate originali.
    const latFixed = waypoint.lat.toFixed(6);
    const lonFixed = waypoint.lon.toFixed(6);

    // I valori sono quelli ricevuti dal backend, non numeri fissi.
    waypointElement.innerHTML = `<b>${waypoint.waypoint_id}: (${latFixed}, ${lonFixed})</b> <b><a href="#" class="remove-waypoint">del</a></b>
                                 <label>Speed: <input type="number" step="any" class="waypoint-speed" value="${waypoint.speed}"></label>
                                 <label>Quote: <input type="number" step="any" class="waypoint-quote" value="${waypoint.quote}"></label>  `;
    // Il link del cancella-waypoint richiama la relativa API.
    waypointElement.querySelector('.remove-waypoint').addEventListener('click', (event) => {
        event.preventDefault();  // Evita che il link '#' sposti la pagina.
        // Impedisce al clic di propagarsi ad altri gestori.
        event.stopPropagation();
        removeWaypoint(waypoint.waypoint_id);
    });

    // querySelector cerca SOLO all'interno del waypoint corrente.
    const inputSpeed = waypointElement.querySelector('.waypoint-speed');
    const inputQuote = waypointElement.querySelector('.waypoint-quote');

    // Registra la callback per la velocità di questo specifico waypoint.
    markInputDirtyAndCommit(inputSpeed, (newValue) => {
        updateSpeed(waypoint, newValue);
    });

    // La quota usa la stessa logica, ma una route Flask diversa.
    markInputDirtyAndCommit(inputQuote, (newValue) => {
        updateQuote(waypoint, newValue);
    });

    const actionsList = document.createElement('div');
    actionsList.classList.add('actions-list');
    actionsList.innerHTML = '<u><b>Actions</b></u> <b><a href="#" class="add-action">add</a></b>';
    // Contenitore separato: jQuery UI riordina queste righe.
    const actionItemsContainer = document.createElement('div');
    actionItemsContainer.classList.add('action-items');

    // Clic su add: recupera le azioni e apre il popup.
    actionsList.querySelector('.add-action').addEventListener('click', (event) => {
        event.preventDefault();
        event.stopPropagation();
        getAvailableActions(waypoint.waypoint_id);
    });

    // Ogni waypoint possiede un proprio array di azioni.
    waypoint.actions.forEach((action) => {
        const actionElement = document.createElement('div');
        actionElement.id = `action-${waypoint.waypoint_id}-${action.action_id}`;
        // data-action-id è un attributo HTML consultato da sortable.
        actionElement.dataset.actionId = `${action.action_id}`;
        actionElement.classList.add('action-draggable');
        actionElement.innerHTML = `<b>${action.action_id} - ${action.action_type}</b> <b><a href="#" class="remove-action">del</a></b>`;

        actionElement.querySelector('.remove-action').addEventListener('click', (event) => {
            event.preventDefault();
            event.stopPropagation();
            removeAction(waypoint.waypoint_id, action.action_id);
        });

        // Contenitore dei parametri dell'azione corrente.
        const parametersList = document.createElement('div');
        // Object.entries trasforma il dizionario parameters in coppie.
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

            // Ogni parametro usa il valore letto dal suo input.
            markInputDirtyAndCommit(input, (newValue) => {
                // "action-2-1" diventa ["action", "2", "1"]: scarta il primo.
                const [, waypointId, actionId] = actionElement.id.split('-');  // Estrae gli ID da action-WP-AZIONE.
                updateAction(waypointId, actionId, param, newValue);
            });

            // Assemblaggio dei nodi DOM: prima label e input nella riga.
            paramElement.appendChild(label);
            paramElement.appendChild(input);
            parametersList.appendChild(paramElement);
        });

        actionElement.appendChild(parametersList);
        actionItemsContainer.appendChild(actionElement);
    });

    // Inserisce tutte le azioni e abilita il loro riordino.
    actionsList.appendChild(actionItemsContainer);
    enableActionSorting(actionItemsContainer, waypoint.waypoint_id);
    waypointElement.appendChild(actionsList);
    waypointsListEl.appendChild(waypointElement);
}

// Gestisce Ctrl+Z, Ctrl+Y e Ctrl+Maiusc+Z fuori dai campi di testo.
function handleUndoRedoShortcuts(event) {
    const target = event.target;
    // Non intercetta Ctrl+Z mentre si scrive in un input.
    const isTypingField = target &&
        (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable);
    if (isTypingField) {
        return;
    }

    // metaKey rappresenta Cmd sui dispositivi Apple.
    const modifierPressed = event.ctrlKey || event.metaKey;
    if (!modifierPressed) {
        return;
    }

    const key = event.key.toLowerCase();
    // Ctrl+Z o Cmd+Z: annulla.
    if (key === 'z' && !event.shiftKey) {
        event.preventDefault();
        undoMission();
        return;
    }

    // Ctrl+Y oppure Ctrl+Maiusc+Z: ripristina.
    if ((key === 'z' && event.shiftKey) || key === 'y') {
        event.preventDefault();
        redoMission();
    }
}

// Crea i pulsanti Save, Load, Undo e Redo e associa le relative operazioni.
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

    // Il browser avvia direttamente il download della route Flask.
    saveButton.addEventListener('click', () => {
        window.location.href = '/save_mission';
    });

    // Il file picker è creato al momento, senza un input fisso nella pagina.
    loadButton.addEventListener('click', () => {
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.id = 'fileInput';
        fileInput.click();

        // change scatta dopo la scelta del file.
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

    // Aggiunge i pulsanti alla sidebar solo dopo aver associato gli eventi.
    optionsDiv.appendChild(saveButton);
    optionsDiv.appendChild(loadButton);
    optionsDiv.appendChild(undoButton);
    optionsDiv.appendChild(redoButton);
}


// =========================
// Bootstrap
// =========================

// Inizializza MapLibre, registra gli eventi e carica i dati della missione.
function initMap() {
    // La chiave MapTiler viene inserita da map_config.js servito da Flask.
    const apiKey = window.MAPTILER_WEB_API_KEY;
    if (!apiKey) {
        console.error('MapTiler key is missing. Set MAPTILER_WEB_API_KEY in the server environment.');
        showMapError('Map key missing. Set MAPTILER_WEB_API_KEY on the server.');
        // Senza chiave, la creazione della mappa non prosegue.
        return;
    }

    // Configura la mappa satellite e la posizione iniziale.
    map = new maplibregl.Map({
        container: byId('map'),
        // encodeURIComponent evita problemi se la chiave ha caratteri speciali.
        style: `https://api.maptiler.com/maps/satellite/style.json?key=${encodeURIComponent(apiKey)}`,
        center: [MAP_CENTER.lng, MAP_CENTER.lat],
        zoom: MAP_ZOOM,
        attributionControl: true
    });
    // Aggiunge i controlli di zoom/rotazione in alto a destra.
    map.addControl(new maplibregl.NavigationControl(), 'top-right');
    map.on('click', (event) => addWaypoint(event.lngLat));  // L'evento MapLibre contiene le coordinate cliccate.
    // "load" avviene quando la mappa è pronta a ricevere layer e marker.
    map.on('load', () => {
        document.addEventListener('keydown', handleUndoRedoShortcuts);
        refreshMission();
        addOptionsButtons();
    });
    // Stampa gli errori MapLibre nella console del browser.
    map.on('error', (event) => console.error('MapLibre error:', event.error));
}

// Avvia il planner dopo aver definito tutte le funzioni.
initMap();
