import utils

class User(object):
    def __init__(self, name, ID, email, publicKey):
        super(User, self).__init__()
        self.name = name
        self.ID = ID
        self.email = email
        self.publicKey = publicKey

    def str(self):
        return str(self.name) + ', ' + str(self.email) + ', ID: '+ str(self.ID)

    def __repr__(self):
        return str(self.name) + ', ' + str(self.email) + ', ID: '+ str(self.ID)


# Funcion que genera un usuario en SecureBox.
# Parámetros:
#	name: nombre del usuario.
#	email: correo del usuario.
#   publicKey: clave pública del usuario.
# Return: resultado de la petición a la API.
#
def generateUser(name, email, publicKey):
    print('Creando usuario en SecureBox')
    data = {
        'nombre' : name,
        'email' : email,
        'publicKey' : publicKey
    }
    r = utils.genericRequest('/users/register', data)
    print(utils.requestResultInfo(r))
    return r


# Funcion que obtiene la clave pública de un usuario de SecureBox.
# Parámetros:
#	userID: id del usuario en SecureBox.
# Return: clave pública del usuario.
#
def userGetPublickey(userID):
    print('Recuperando clave pública de ID ' + userID)
    r = utils.genericRequest('/users/getPublicKey', {'userID' : userID})
    print(utils.requestResultInfo(r))
    return r.json()['publicKey'].encode()


# Funcion que elimina un usuario de SecureBox.
# Parámetros:
#	userID: id del usuario en SecureBox.
# Return: resultado de la petición a la API.
#
def userDelete(userID):
    print('Borrando usuario de ID ' + userID)
    r = utils.genericRequest('/users/delete', {'userID' : userID})
    print(utils.requestResultInfo(r))
    return r


# Funcion que busca los usuarios de SecureBox con un dato determinado y genera una lista con ellos.
# Parámetros:
#	dataSearch: dato que deben contener los usuarios.
# Return: lista de usuarios.
#
def userSearch(dataSearch):
    print('Buscando usuario ' + dataSearch + ' en el servidor')
    r = utils.genericRequest('/users/search', {'data_search' : dataSearch})
    print(utils.requestResultInfo(r))
    if r.status_code != 200:
        return ''

    result = str(len(r.json())) + ' usuarios encontrados: \n'
    i = 1
    for entry in r.json():
        result += '[' + str(i) + '] ' + User(entry['nombre'], entry['userID'], entry['email'], entry['publicKey']).str() + '\n'
        i += 1

    return result
