import utils
import identityGestion as ig


# Funcion que sube un fichero cifrado y firmado a la API.
# Parámetros:
#	path: dirección del fichero que se quiere firmar, encriptar y subir.
#	dest_id: id en SecureBox del destinatario del fichero.
# Return: resultado de la petición a la API.
#
def uploadFile(path):
    print('Subiendo fichero al servidor')
    r = utils.binaryRequest('/files/upload', path)
    print(utils.requestResultInfo(r))
    print(r.json())
    return r


# Funcion que descarga un fichero de la API.
# Parámetros:
#	fileID: id del fichero en SecureBox.
#	source_id: id en SecureBox del emisor del fichero.
# Return: dirección del fichero descargado.
#
def fileDownload(fileID, source_id):
    print('Descargando fichero de SecureBox')
    r = utils.genericRequest('/files/download', {'file_id' : fileID})
    filename = r.headers['Content-Disposition'].split('\"')[-2]
    filename = './encriptado/' + filename
    with open(filename , 'wb') as file:
    	file.write(r.content)
    print(utils.requestResultInfo(r))
    print(r.headers['content-length'] + ' bytes descargados correctamente.')
    return filename


# Funcion que genera una lista con los ficheros propios subidos a SecureBox.
# Return: lista de los ficheros.
#
def fileList():
    print('Generando lista de ficheros')
    r = utils.genericRequest('/files/list', None)
    print(utils.requestResultInfo(r))
    nfiles = r.json()['num_files']
    result = 'Tienes ' + str(nfiles) + ' archivos guardados'
    if nfiles == 0:
        return result + "."

    result = result + ":"
    for file in r.json()['files_list']:
        result += "\n- " + str(file)
    return result


# Funcion que elimina un fichero subido a SecureeBox.
# Parámetros:
#	fileID: id del fichero en SecureBox.
# Return: resultado de la petición a la API.
#
def fileDelete(fileID):
    print('Eliminando fichero de ID ' + fileID)
    r = utils.genericRequest('/files/delete', {'file_id' : fileID})
    print(utils.requestResultInfo(r))
    return r
