import utils
import json

#################################################################################
# Clase representa un usuario de la aplicación.
# Objetos:
#	- nick: nick del usuario
#	- ip: ip de la conexion de control del usuario
#	- port: puerto de la conexion de control del usuario
#	- protocols: protocolos que soporta la aplicacion del usuario
#	- password: contraseña del usuario (solo si se loggea desde esta aplicacion)
#################################################################################
class User(object):

	#
	# Método instanciador de la clase
	# Entrada:
	#	- nick: nick del usuario
	#	- ip: ip de la conexion de control del usuario
	#	- port: puerto de la conexion de control del usuario
	#	- protocols: protocolos que soporta la aplicacion del usuario
	#	- password: contraseña del usuario (solo si se loggea desde esta aplicacion)
	# Salida:
	#	Objeto de tipo user
	#
	def __init__(self, nick, ip, port, protocols, password=None):
		super(User, self).__init__()
		self.nick = nick
		self.ip = ip
		self.port = port
		self.protocols = protocols
		self.password = password

	#
	# Devuelve un string que indentifica al usuario
	#
	def __str__(self):
		return self.nick+' '+self.ip+':'+str(self.port)+' '+str(self.protocols)

	#
	# Devuelve un string que indentifica al usuario
	#
	def __repr__(self):
		return self.__str__()

	#
	# Funcion que devuelve la lista de protocolos soportados por el usuario
	# Salida:
	# 	Lista de protocolos soportados por la aplicación del usuario
	#
	def getProtocols(self):
		if self.protocols != None:
			return self.protocols
		else:	# Si el usuario se ha obtenido de un list_users, no sabemos sus protocolos
			user = quertyUser(self.nick)
			if user != None:
				self.protocols = user.protocols
			return self.protocols


#
# Funcion que permite almacenar los datos de un usuario en el fichero utils.USER_CONFIG
# Salida:
# 	True si se han guardado correctamente, False en caso contrario
#
def saveUserInfo(user):
	data = {
		'nick' : user.nick,
		'ip' : user.ip,
		'port' : user.port
	}
	with open(utils.USER_CONFIG, 'w') as outfile:
		json.dump(data, outfile)
		return True
	return False

#
# Funcion que permite leer los datos de un usuario del fichero utils.USER_CONFIG
# Salida:
# 	Un User con los datos almacenados, None si ha habido algún problema
#
def getUserInfo():
	try:
		file = open(utils.USER_CONFIG)
	except IOError:
		return None

	with file:
		data = json.load(file)
		# En este caso, la aplicacion solo soporta los protocolos V0 y V1
		return User(data['nick'], data['ip'], int(data['port']), ['V0', 'V1'], None)
	return None
