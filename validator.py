
import math


# Funzione principale che richiama il validatore corretto.
def validatorFun(action_name, parameters):

    if not isinstance(parameters, dict):
        return False

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
        return False


# Controlla i parametri dell'azione focus.
def validateFocus(parameters):

    required = {"payloadPositionIndex", "focusX", "focusY"}

    # Controlla che tutti e soli i parametri richiesti siano presenti.
    if set(parameters.keys()) != required:
        return False

    try:
        for key, value in parameters.items():

            if key == "payloadPositionIndex":
                if float(value) not in {0, 1, 2}:
                    return False

            elif key == "focusX":
                if not (0 <= float(value) <= 1):
                    return False

            elif key == "focusY":
                if not (0 <= float(value) <= 1):
                    return False

            else:
                return False

    except (ValueError, TypeError, OverflowError):
        return False

    return True


# Controlla i parametri dell'azione takePhoto.
def validatetakePhoto(parameters):

    required = {"payloadPositionIndex", "fileSuffix"}

    if set(parameters.keys()) != required:
        return False

    try:
        for key, value in parameters.items():

            if key == "payloadPositionIndex":
                if float(value) not in {0, 1, 2}:
                    return False

            elif key == "fileSuffix":
                if not isinstance(value, str) or len(value) > 50:
                    return False

            else:
                return False

    except (ValueError, TypeError, OverflowError):
        return False

    return True


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

    if set(parameters.keys()) != required:
        return False

    try:
        for key, value in parameters.items():

            if key == "payloadPositionIndex":
                if float(value) not in {0, 1, 2}:
                    return False

            elif key == "gimbalRotateMode":
                if value != "absoluteAngle":
                    return False

            elif key == "gimbalPitchRotateEnable":
                if float(value) not in {0, 1}:
                    return False

            elif key == "gimbalPitchRotateAngle":
                angle = float(value)
                if not math.isfinite(angle) or not (-180 <= angle <= 180):
                    return False

            elif key == "gimbalYawRotateEnable":
                if float(value) not in {0, 1}:
                    return False

            elif key == "gimbalYawRotateAngle":
                angle = float(value)
                if not math.isfinite(angle) or not (-180 <= angle <= 180):
                    return False

            else:
                return False

    except (ValueError, TypeError, OverflowError):
        return False

    return True


# Controlla i parametri dell'azione rotateYaw.
def validaterotateYaw(parameters):

    required = {"aircraftHeading"}

    if set(parameters.keys()) != required:
        return False

    try:
        for key, value in parameters.items():

            if key == "aircraftHeading":
                angle = float(value)

                if not math.isfinite(angle) or not (-180 <= angle <= 180):
                    return False

            else:
                return False

    except (ValueError, TypeError, OverflowError):
        return False

    return True


# Controlla i parametri dell'azione hover.
def validatehover(parameters):

    required = {"hoverTime"}

    if set(parameters.keys()) != required:
        return False

    try:
        for key, value in parameters.items():

            if key == "hoverTime":
                time = float(value)

                if not math.isfinite(time) or not (0 < time <= 100000):
                    return False

            else:
                return False

    except (ValueError, TypeError, OverflowError):
        return False

    return True


# Controlla i parametri dell'azione zoom.
def validatezoom(parameters):

    required = {"payloadPositionIndex", "focalLength"}

    if set(parameters.keys()) != required:
        return False

    try:
        for key, value in parameters.items():

            if key == "payloadPositionIndex":
                if float(value) not in {0, 1, 2}:
                    return False

            elif key == "focalLength":
                focal = float(value)

                if not math.isfinite(focal) or focal <= 0:
                    return False

            else:
                return False

    except (ValueError, TypeError, OverflowError):
        return False

    return True

# Controlla il payload globale della missione.
def validateGlobalParameter(parameter, value):

    if parameter == "payloadIndex":

        try:
            # Accettiamo soltanto numeri interi.
            if isinstance(value, bool):
                return False

            number = int(value)

            if str(number) != str(value):
                return False

            if number in {0, 1, 2}:
                return True

            return False

        except (ValueError, TypeError, OverflowError):
            return False

    # Parametro globale sconosciuto.
    return False

#print(validatorFun("hover", {"hoverTime": "ciao"}))
 #print(validatorFun("hover", {"hoverTime": 7}))
#print(validatorFun("rotateYaw", {"aircraftHeading": 999}))
##print(validatorFun("rotateYaw", {"aircraftHeading": -45}))
#print(validatorFun("focus", {
    #"payloadPositionIndex": 0,
   # "focusX": 0.5,
   ## "focusY": 8
#}))
