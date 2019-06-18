from appJar import gui
from user import getUserInfo, saveUserInfo
import utils
import identityGestion
import threading

#################################################################################
# Metaclass usada para definir un singleton
#################################################################################
class Singleton(type):
	_instances = {}
	def __call__(cls, *args, **kwargs):
		if cls not in cls._instances:
			cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
		return cls._instances[cls]


#################################################################################
# Clase Singleton que reune los componentes principales de la aplicación.
# Objetos:
#	· __instance: instancia ya inicializada de la apliacion. Usada para aplicar
#		el patrón singleton
# 	· protocols: protocolos implementados por la aplicación
#	- user: usuario que está utilizando la aplicación
# 	- interface: objeto del tipo VideoClient que representa la interfaz usada.
#	- controlConnection: conexión de control utilizada por la aplicación.
# 	- logger: logger usado para almacenar información sobre la ejecución y 
# 		posibles errores de la aplicación
#	- connection: conexión establecida con un usuario. Tiene que heredar
# 		de UDPConnection.
#################################################################################

class Application(object, metaclass = Singleton):
	__instance = None
	protocols = ['V0', 'V1']

	#
	# Método instanciador de la clase
	# Entrada:
	#	- user: usuario que está utilizando la aplicación
	# 	- interface: objeto del tipo VideoClient que representa la interfaz usada.
	#	- controlConnection: conexión de control utilizada por la aplicación.
	# 	- logger: logger usado para almacenar información sobre la ejecución y 
	# 		posibles errores de la aplicación
	#	- connection: conexión UDP establecida con un usuario. Tiene que heredar
	# 		de UDPConnection.
	# Salida:
	# 	Objeto único del tipo Application, al ser Singleton
	#
	def __init__(self, user, interface, controlConnection, logger):
		super(Application, self).__init__()
		self.user = user
		self.interface = interface
		self.controlConnection = controlConnection
		self.logger = logger
		self.connection = None


	#
	# Método que devuelve la instancia de la clase si ya está creada, o la inicializa en caso contrario.
	# Entrada:
	#	- user: usuario que está utilizando la aplicación
	# 	- interface: objeto del tipo VideoClient que representa la interfaz usada.
	#	- controlConnection: conexión de control utilizada por la aplicación.
	# 	- logger: logger usado para almacenar información sobre la ejecución y 
	# 		posibles errores de la aplicación
	#	- connection: conexión UDP establecida con un usuario. Tiene que heredar
	# 		de UDPConnection.
	# Salida:
	# 	Objeto único del tipo Application, al ser Singleton
	#
	def getInstance(user = None, interface = None, controlConnection = None, logger = None):
		if not Application.__instance:
			Application.__instance = Application(user, interface, controlConnection, logger)

		return Application.__instance

	#
	# Devuelve el usuario del Application.
	# Salida:
	# 	Usuario loggeado del Application.
	#
	def getUser(self):
		return self.user

	#
	# Devuelve la interfaz del Application.
	# Salida:
	# 	Interfaz del Application.
	#
	def getInterface(self):
		return self.interface

	#
	# Devuelve la conexión de control del Application.
	# Salida:
	# 	Conexión de control del Application.
	#
	def getControlConnection(self):
		return self.controlConnection

	#
	# Devuelve los protocolos del Application.
	# Salida:
	# 	Protocolos del Application.
	#
	def getProtocols(self):
		return self.protocols

	#
	# Devuelve la interfaz del Application.
	# Salida:
	# 	Interfaz del Application.
	#
	def getConnection(self):
		return self.connection

	#
	# Cambia el objeto Connection del Application.
	# Entrada:
	#	- conn: conexión con UDP con un usuario.
	#
	def setConnection(self, conn):
		self.connection = conn

	#
	# Cambia el objeto User del Application. Se llama únicamente al inicio, una vez el usuario se loggea.
	# Entrada:
	#	- conn: conexión con UDP con un usuario.
	#
	def setUser(self, user):
		self.user = user

	#
	# Inicializa la Application
	#
	def start(self):
		self.logger.debug('Starting Application')
		# Iniciamos la interfaz
		self.interface.start()

	#
	# Inicializa la conexión de control del Application en un nuevo hilo
	# Entrada:
	#	- ip: dirección IP en la que iniciar la conexión de control
	#	- port: puerto en el que iniciar la conexión de control
	#
	def startControlConnection(self, ip, port):
		# Iniciamos la conexion de control
		self.controlConnection.setIPPort(ip, port)
		t = threading.Thread(target=self.controlConnection.start)
		t.start()
