import utils
from datetime import datetime
import socket
from user import User, saveUserInfo, getUserInfo
		
#
# Función usada para registrar un usuario en el servidor de descubirmiento
# Entrada:
#	- nick: nick del usuario a registrar
#	- ip: ip de la conexión de control del usuario a registrar.
#	- port: puerto de la conexión de control del usuario a registrar.
#	- password: contraseña del usuario a registrar.
#	- protocol: protocolos soportados por la aplicación del usuario a registrar.
# Salida:
# 	User registrado o None si ha habido algún error.
#
def registerUser(nick, ip, port, password, protocol):
	message = 'REGISTER {} {} {} {} {}'.format(nick, ip, str(port), password, protocol)
	r = utils.sendTCPMessage(message, utils.DS_URL, utils.DS_PORT)
	if r == None:
		return None
	result = r.split(' ')
	if result[0] == 'OK':
		return User(nick, ip, port, protocol.split('#'), password)
	else:
		# La contraseña es incorrecta
		return None

#
# Función usada para buscar un usuario por su nick en el servidor de descubirmiento.
# Entrada:
#	- nick: nick del usuario a buscar.
# Salida:
# 	User registrado o None si el usuario no existe.
#
def quertyUser(nick):
	message = 'QUERY {}'.format(nick)
	r = utils.sendTCPMessage(message, utils.DS_URL, utils.DS_PORT)
	if r == None:
		return None
	result = r.split(' ')
	if result[0] == 'OK':
		return User(result[2], result[3], int(result[4]), result[5].split('#'))
	else:
		return None

#
# Función usada para listar todos los usuarios del servidor de descubirmiento.
# Salida:
# 	Lista de User registrados
#
def listUsers():
	# En este caso, necesitamos establecer la coneción aquí porque no sabemos cuantos
	# usuarios vamos a tener que leer
	client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	client_socket.connect((utils.DS_URL, utils.DS_PORT))
	client_socket.send('LIST_USERS'.encode())

	result = client_socket.recv(30).decode()
	result = result.split(' ')
	if result[0] != 'OK':
		return None

	numUsers = int(result[2])
	# Eliminamos los tres primeros datos iniciales y nos quedamos solo con los usuarios
	r = ' '.join(result[3:])
	rawUsers = None
	while True:
		rawUsers = r.split('#')
		# Tenemos que tener un usuario mas de los indicados,
		# pues la cadena acaba con un # que se reconoce como
		# otro elemento al hacer el split
		if len(rawUsers) > numUsers:
			break
		else:
			result = client_socket.recv(2048).decode()
			r += result

	client_socket.close()

	users = []
	for user in rawUsers[:-1]:	#El ultimo esta vacio
		info = user.split(' ')
		try:
			users.append(User(info[0], info[1], int(info[2]), None))
		except ValueError as e:
			# En el caso de que el puerto del usuario no sea un numero
			continue
		except IndexError as e:
			# Hay algunos usuarios que no tienen todos los datos necesarios
			continue

	return users

#print("Registramos el usuario con nombre HELLO_WORLD")
#user = registerUser('HELLO_WORLD', '0.0.0.0', 8888, 'contraseña', 'V1#V2')
#print(user)

#print("\n\nBuscamos el usuario con nombre HELLO_WORLD")
#print(quertyUser('HELLO_WORLD'))

#print("\n\nLista de usuarios")
#print(listUsers())
