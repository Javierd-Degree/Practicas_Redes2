import socket
import time

# Url del servidor de descubrimiento
DS_URL = 'vega.ii.uam.es'
# Puerto del servidor de descubrimiento
DS_PORT = 8000

# Tamaño inicial de la ventana de interfaz
WIN_SIZE = '700x650'

# Nombre de la apliación
NAME = 'SKUPE'

# Nombre principal de los archivos de log (se irán añadiendo .i al final al ir aumentando)
LOG_FILE = 'log'
# Fichero donde almacenar la informacion del último usuario loggeado
USER_CONFIG = 'config.json'


#
# Determina si un Objeto representa o no un número entero.
# Entrada:
# 	- data: objeto a determinar si es un entero.
# Salida:
# 	True si data es un entero almacenado como String o Float, False en caso contrario.
#
def isInteger(data):
	if isinstance(data, str):
		return data.isdigit()
	elif isinstance(data, float):
		return data.is_integer()
	try:
		int(data)
		return True
	except ValueError:
		return False

#
# Determina si un string representa o no una dirección IPv4.
# Entrada:
# 	- string: string a determinar si es una dirección IPv4.
# Salida:
# 	True si string es una dirección IPv4, False en caso contrario.
#
def isIPv4(string):
	ip = string.split('.')
	if len(ip) != 4:
		return False
	for c in ip:
		if not isInteger(c):
			return False
		n = int(c)
		if n < 0 or n > 255:
			return False
	return True

#
# Funcion que determina si un string conforma una lista de protocolos válidos.
# Es decir, comprueba que es una lista de la forma Vi#Vj#Vk... con i, j, k numeros
# Entrada:
#	- string: string a determinar si conforma una lista de protocolos válidos.
# Salida:
#	True si string conforma una lista de protocolos válidos, False en caso contrario.
#
def isValidProtocols(string):
	protocols = string.split('#')
	for p in protocols:
		if (p[0] != 'V') or not isInteger(p[1:]):
			return False
	return True

#
# Funcion que envia un mensaje TCP y espera una respuesta
# Entrada:
#	- message: array de bytes a enviar por el socket TCP
#	- serverName: dirección ip o url del servidor
#	- serverPort: puerto del servidor
#	- timeout: tiempo en segundo durante el que esperar
#	- recvLen: longitud del mensaje respuesta esperado
# Salida:
#	Respuesta devuelta por el servidor TCP. None si hay un timeout
#
def sendTCPMessage(message, serverName, serverPort, timeout = 10, recvLen = 1024):
	try:
		client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		client_socket.settimeout(timeout)
		client_socket.connect((serverName, serverPort))
		client_socket.send(message.encode())
		result = client_socket.recv(recvLen).decode()
		client_socket.close()
		return result
	except socket.error as e:
		print('Error al connectar con {}:{}.{}'.format(serverName, serverPort, e))
		return None

#
# Funcion que envia un mensaje TCP sin esperar respuesta
# Entrada:
#	- message: array de bytes a enviar por el socket TCP
#	- serverName: dirección ip o url del servidor
#	- serverPort: puerto del servidor
#	- timeout: tiempo en segundo durante el que esperar
#	- recvLen: longitud del mensaje respuesta esperado
#
def sendTCPMessageOnly(message, serverName, serverPort, timeout = 10, recvLen = 1024):
	try:
		client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		client_socket.settimeout(timeout)
		client_socket.connect((serverName, serverPort))
		client_socket.send(message.encode())
		client_socket.close()
	except socket.error as e:
		print('Error al connectar con {}:{}.{}'.format(serverName, serverPort, e))

#
# Funcion que devuelve un numero nports de puertos libres
# Entrada:
#	- ip: ip para la cual se quieren los puertos
#	- nports: numero de puertos a recibir
# Salida:
# 	Lista con los ids de los puertos libres, o el id del puerto libre si nports = 1
#
def getAvailablePort(ip, nports = 1):
	ports = []
	sockets = []
	for i in range(nports):
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.bind((ip,0))
		ports.append(s.getsockname()[1])
		sockets.append(s)

	for s in sockets:
		s.close()

	if len(ports) == 1:
		# Si solo hay uno, lo devolvemos como un elemento
		return ports[0]
	return ports

#
# Funcion que devuelve un numero de miliseguntos como un string formateado: hh:mm:ss o mm:ss
# Entrada:
#	- data: numero de milisegundos
# Salida:
# 	String con los milisegundos formateados como hh:mm:ss o mm:ss
#
def timedeltaToStr(data):
	hours = int(data//3600)
	minutes = int(data//60)%60
	secs = int(data)%60

	if hours == 0:
		return '{:02}:{:02}'.format(minutes, secs)

	return '{:02}:{:02}:{:02}'.format(hours, minutes, secs)
	

#print(sendTCPMessage('LIST_USERS', DS_URL, DS_PORT))
