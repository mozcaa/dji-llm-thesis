
import math


# Funzione principale che richiama il validatore corretto.
def validatorFun(action_name, parameters):

    if not isinstance(parameters, dict):
        return False, "I parametri dell'azione devono essere un dizionario"

    if action_name == "focus":
        return validateFocus(parameters)

    elif action_name == "takePhoto":
        return validatetakePhoto(parameters)

    elif action_name == "gimbalRotate":
        return validategimbalRotate(parameters)

    elif action_name == "rotateYaw":
        return validaterotateYaw(parameters)

    elif action_name == "hover":
        return validatehover(parameters)

    elif action_name == "zoom":
        return validatezoom(parameters)

    else:
        return False, f"Azione sconosciuta: {action_name}"
    
# Controlla che un valore sia numerico, finito e compreso nell'intervallo indicato.
# Questa funzione viene riutilizzata per coordinate, quota e velocità.
def validateRange(value, minimum, maximum, name):

    # In Python True e False sono convertibili in 1 e 0:
    # li rifiutiamo perché non vogliamo booleani nei campi numerici.
    if isinstance(value, bool):
        return False, f"{name} non può essere un booleano"

    try:
        value = float(value)  

    except (ValueError, TypeError, OverflowError):
        return False, f"{name} deve essere un numero"

    # math.isfinite() rifiuta NaN e Infinity.
    if not math.isfinite(value):
        return False, f"{name} deve essere un numero finito"

    if not (minimum <= value <= maximum):
        return False, f"{name} deve essere tra {minimum} e {maximum}"

    return True, None


# Controlla che l'indice identifichi un waypoint già presente nella missione.
# waypointnumber rappresenta il numero TOTALE di waypoint esistenti.
def validateExistingIndex(waypointindex, waypointnumber):

    # Accettiamo soltanto indici interi, escludendo float e booleani.
    if type(waypointindex) is not int:
        return False, "L'indice del waypoint deve essere un intero"

    if not (0 <= waypointindex < waypointnumber):
        return False, f"Waypoint inesistente: indice {waypointindex}"

    return True, None


# Controlla che latitudine e longitudine siano coordinate geografiche valide.
# Latitudine: da -90 a 90 gradi.
# Longitudine: da -180 a 180 gradi.
def validateCoordinates(lat, lon):

    validLat, errorLat = validateRange(lat, -90, 90, "Latitudine")
    validLon, errorLon = validateRange(lon, -180, 180, "Longitudine")

    return validLat and validLon, errorLat or errorLon


# Valida i dati di un nuovo waypoint da aggiungere alla FINE della missione.
# Non controlliamo l'indice perché add_waypoint() lo aggiunge automaticamente.
def validateNewWaypoint(lat, lon, speed, quote):

    validCoordinates, errorCoordinates = validateCoordinates(lat, lon)
    validSpeed, errorSpeed = validateRange(speed, 0.1, 100, "Velocità")
    validQuote, errorQuote = validateRange(quote, 0.1, 100, "Quota")

    return validCoordinates and validSpeed and validQuote, errorCoordinates or errorSpeed or errorQuote


# Valida un nuovo waypoint da inserire TRA due waypoint già esistenti.
# Controlla sia la posizione di inserimento sia i dati del nuovo waypoint.
def validateNewWaypointAt(lat, lon, speed, quote, waypointindex, waypointnumber):

    validIndex, errorIndex = validateExistingIndex(waypointindex, waypointnumber)
    validWaypoint, errorWaypoint = validateNewWaypoint(lat, lon, speed, quote)

    # Escludiamo l'indice 0, perché vogliamo un waypoint precedente.
    if validIndex and waypointindex == 0:
        return False, "Non puoi inserire un waypoint prima del primo con questa operazione"

    return validIndex and validWaypoint, errorIndex or errorWaypoint


# Valida la modifica delle COORDINATE di un waypoint già esistente.
# Prima controlla che il waypoint esista, poi verifica latitudine e longitudine.
def validateUpdateWaypoint(lat, lon, waypointindex, waypointnumber):

    validIndex, errorIndex = validateExistingIndex(waypointindex, waypointnumber)
    validCoordinates, errorCoordinates = validateCoordinates(lat, lon)

    return validIndex and validCoordinates, errorIndex or errorCoordinates


# Valida la modifica della VELOCITÀ di un waypoint esistente.
# La velocità appartiene al tratto che parte dal waypoint verso il successivo.
def validateUpdateWaypointSpeed(speed, waypointindex, waypointnumber):

    validIndex, errorIndex = validateExistingIndex(waypointindex, waypointnumber)
    validSpeed, errorSpeed = validateRange(speed, 0.1, 100, "Velocità")

    return validIndex and validSpeed, errorIndex or errorSpeed


# Valida la modifica della QUOTA di un waypoint esistente.
def validateUpdateWaypointQuote(quote, waypointindex, waypointnumber):

    validIndex, errorIndex = validateExistingIndex(waypointindex, waypointnumber)
    validQuote, errorQuote = validateRange(quote, 0.1, 100, "Quota")

    return validIndex and validQuote, errorIndex or errorQuote


# Controlla che siano presenti tutti e soli i parametri richiesti.
def validateRequiredParameters(parameters, required):

    missing = required - parameters.keys()
    extra = parameters.keys() - required

    if missing:
        return False, f"Parametri mancanti: {', '.join(sorted(missing))}"

    if extra:
        return False, f"Parametri sconosciuti: {', '.join(sorted(extra))}"

    return True, None


# Controlla i parametri dell'azione focus.
def validateFocus(parameters):

    required = {"payloadPositionIndex", "focusX", "focusY"}

    status, message = validateRequiredParameters(parameters, required)
    if not status:
        return False, message

    try:
        for key, value in parameters.items():

            if isinstance(value, bool):
              return False, f"{key} non può essere un booleano"

            if key == "payloadPositionIndex":
                if float(value) not in {0, 1, 2}:
                    return False, "payloadPositionIndex deve essere 0, 1 o 2"

            elif key == "focusX":
                if not (0 <= float(value) <= 1):
                    return False, "focusX deve essere tra 0 e 1"

            elif key == "focusY":
                if not (0 <= float(value) <= 1):
                    return False, "focusY deve essere tra 0 e 1"

            else:
                return False, f"Parametro sconosciuto: {key}"

    except (ValueError, TypeError, OverflowError):
        return False, f"Valore non numerico per {key}"

    return True, None


# Controlla i parametri dell'azione takePhoto.
def validatetakePhoto(parameters):

    required = {"payloadPositionIndex", "fileSuffix"}

    status, message = validateRequiredParameters(parameters, required)
    if not status:
        return False, message

    try:
        for key, value in parameters.items():

            if isinstance(value, bool):
              return False, f"{key} non può essere un booleano"
            
            if key == "payloadPositionIndex":
                if float(value) not in {0, 1, 2}:
                    return False, "payloadPositionIndex deve essere 0, 1 o 2"

            elif key == "fileSuffix":
                if not isinstance(value, str) or len(value) > 50:
                    return False, "fileSuffix deve essere una stringa di massimo 50 caratteri"

            else:
                return False, f"Parametro sconosciuto: {key}"

    except (ValueError, TypeError, OverflowError):
        return False, f"Valore non valido per {key}"

    return True, None


# Controlla i parametri dell'azione gimbalRotate.
def validategimbalRotate(parameters):

    required = {
        "payloadPositionIndex",
        "gimbalRotateMode",
        "gimbalPitchRotateEnable",
        "gimbalPitchRotateAngle",
        "gimbalYawRotateEnable",
        "gimbalYawRotateAngle"
    }

    status, message = validateRequiredParameters(parameters, required)
    if not status:
        return False, message

    try:
        for key, value in parameters.items():

            if isinstance(value, bool):
              return False, f"{key} non può essere un booleano"

            if key == "payloadPositionIndex":
                if float(value) not in {0, 1, 2}:
                    return False, "payloadPositionIndex deve essere 0, 1 o 2"

            elif key == "gimbalRotateMode":
                if value != "absoluteAngle":
                    return False, "gimbalRotateMode deve essere absoluteAngle"

            elif key == "gimbalPitchRotateEnable":
                if float(value) not in {0, 1}:
                    return False, "gimbalPitchRotateEnable deve essere 0 o 1"

            elif key == "gimbalPitchRotateAngle":
                angle = float(value)
                if not math.isfinite(angle) or not (-180 <= angle <= 180):
                    return False, "gimbalPitchRotateAngle deve essere tra -180 e 180"

            elif key == "gimbalYawRotateEnable":
                if float(value) not in {0, 1}:
                    return False, "gimbalYawRotateEnable deve essere 0 o 1"

            elif key == "gimbalYawRotateAngle":
                angle = float(value)
                if not math.isfinite(angle) or not (-180 <= angle <= 180):
                    return False, "gimbalYawRotateAngle deve essere tra -180 e 180"

            else:
                return False, f"Parametro sconosciuto: {key}"

    except (ValueError, TypeError, OverflowError):
        return False, f"Valore non numerico per {key}"

    return True, None


# Controlla i parametri dell'azione rotateYaw.
def validaterotateYaw(parameters):

    required = {"aircraftHeading"}

    status, message = validateRequiredParameters(parameters, required)
    if not status:
        return False, message

    try:
        for key, value in parameters.items():

            if isinstance(value, bool):
              return False, f"{key} non può essere un booleano"

            if key == "aircraftHeading":
                angle = float(value)

                if not math.isfinite(angle) or not (-180 <= angle <= 180):
                    return False, "aircraftHeading deve essere tra -180 e 180"

            else:
                return False, f"Parametro sconosciuto: {key}"

    except (ValueError, TypeError, OverflowError):
        return False, f"Valore non numerico per {key}"

    return True, None


# Controlla i parametri dell'azione hover.
def validatehover(parameters):

    required = {"hoverTime"}

    status, message = validateRequiredParameters(parameters, required)
    if not status:
        return False, message

    try:
        for key, value in parameters.items():

            if isinstance(value, bool):
              return False, f"{key} non può essere un booleano"

            if key == "hoverTime":
                time = float(value)

                if not math.isfinite(time) or not (0 < time <= 100000):
                    return False, "hoverTime deve essere maggiore di 0 e minore o uguale a 100000"

            else:
                return False, f"Parametro sconosciuto: {key}"

    except (ValueError, TypeError, OverflowError):
        return False, f"Valore non numerico per {key}"

    return True, None


# Controlla i parametri dell'azione zoom.
def validatezoom(parameters):

    required = {"payloadPositionIndex", "focalLength"}

    status, message = validateRequiredParameters(parameters, required)
    if not status:
        return False, message

    try:
        for key, value in parameters.items():

            if isinstance(value, bool):
              return False, f"{key} non può essere un booleano"

            if key == "payloadPositionIndex":
                if float(value) not in {0, 1, 2}:
                    return False, "payloadPositionIndex deve essere 0, 1 o 2"

            elif key == "focalLength":
                focal = float(value)

                if not math.isfinite(focal) or focal <= 0:
                    return False, "focalLength deve essere un numero finito maggiore di 0"

            else:
                return False, f"Parametro sconosciuto: {key}"

    except (ValueError, TypeError, OverflowError):
        return False, f"Valore non numerico per {key}"

    return True, None


# Controlla il payload globale della missione.
def validateGlobalParameter(parameter, value):

    if parameter == "payloadIndex":

        try:
            # Accettiamo soltanto numeri interi.
            if isinstance(value, bool):
                return False, "payloadIndex non può essere un booleano"

            number = int(value)

            if str(number) != str(value):
                return False, "payloadIndex deve essere un numero intero"

            if number in {0, 1, 2}:
                return True, None

            return False, "payloadIndex deve essere 0, 1 o 2"

        except (ValueError, TypeError, OverflowError):
            return False, "payloadIndex deve essere un numero intero valido"

    # Parametro globale sconosciuto.
    return False, f"Parametro globale sconosciuto: {parameter}"