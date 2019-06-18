import requests
import json

URL = 'http://vega.ii.uam.es:8080/api'


# Funcion que obtiene el token para la API.
# Return: token.
#
def getToken():
    return '0c1F4Ab3ED5C796f'

# Funcion que realiza una petición a la API (no de descarga).
# Parámetros:
#	function: acción ue se quiere que realice la API.
#	data: parámetros para la acción.
#   mainURL: URL de la API.
# Return: el resultado de la petición a la API
#
def genericRequest(function, data, mainUrl=URL):
    url = mainUrl+function
    return requests.post(url, json=data, headers={'Authorization': 'Bearer ' + getToken()})


# Funcion que realiza una petición a la API (de descarga).
# Parámetros:
#	function: acción ue se quiere que realice la API.
#	file_path: dirección del fichero descargado.
#   mainURL: URL de la API.
# Return: el resultado de la petición a la API
#
def binaryRequest(function, file_path, mainUrl=URL):
    url = mainUrl+function
    file = {'ufile': open(file_path,'rb')}

    return requests.post(url, files=file, headers={'Authorization': 'Bearer ' + getToken()})


# Funcion que comprueba el resultado de una petición a la API.
# Parámetros:
#	request: resultado de la petición.
# Return: OK si la petición ha sido completada correctamente.
#
def requestResultInfo(request):
    if request.status_code == 200:
        return 'OK'
    else:
        try:
            return request.json()
        except Exception:
            return request.status_code
