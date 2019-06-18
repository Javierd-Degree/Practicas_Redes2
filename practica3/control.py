from application import Application
from threading import Event
import identityGestion
import socket
import utils
import time
import udp

######################################################################################
# Clase que gestiona una conexión TCP que actúa como conexión de control de 
# la aplicación, recibiendo llamadas, distintas peticiones etc.
# Objetos:
#	- ip: ip en la que iniciar el servidor TCP.
#	- port: ip en el que iniciar el servidor TCP.
#	- maxConnections: número maximo de conexiones simultáneas. En este caso es
#		un servidor iterativo, por lo que este parámetro es indiferente.
# 	- logger: logger usado para almacenar información sobre la ejecución y 
# 		posibles errores de la conexión
# 	- runningEvent: Event que permite indicar al hilo del servidor cuando parar
#	- waitEvent: Event que permite detener el hilo hasta que el usuario tome una 
#		decision en la interfaz. EJ: que acepte/rechaze la llamada.
#	- waitCallTimeout: Numero de segundos durante los cuales se espera a que el 
#		receptor acepte/rechace la llamada.
#	- interfaceResponse: Variable usada para almacenar respuestas pasadas
#		desde la interfaz como contestacion a algo.
#####################################################################################
class ControlConnection(object):

	#
	# Método instanciador de la clase.
	# Entrada:
	#	- ip: ip en la que iniciar el servidor TCP.
	#	- port: ip en el que iniciar el servidor TCP.
	#	- maxConnections: número maximo de conexiones simultáneas. En este caso es
	#		un servidor iterativo, por lo que este parámetro es indiferente.
	#
	def __init__(self, maxConnections, logger, ip = '0.0.0.0', port = 0):
		super(ControlConnection, self).__init__()
		self.ip = ip
		self.port = port
		self.maxConnections = maxConnections
		self.logger = logger

		self.runningEvent = Event()
		self.waitEvent = Event() 
		self.waitCallTimeout = 30
		self.interfaceResponse = None

	#
	# Método que permite establecer la IP y puerto del servidor.
	# Usado antes de iniciar la conexión, una vez el usuario se ha loggeado.
	#
	def setIPPort(self, ip, port):
		if not self.runningEvent.is_set():
			self.port = port
			self.ip = ip

	#
	# Método que inicializa la conexión TCP.
	#
	def start(self):
		# Creamos el socket
		self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		# Lo asociamos a la IP y puerto correctos
		try:
			self.server.bind((self.ip, self.port))
		except Exception as e:
			print('{}:{}'.format(self.ip, self.port))
			self.logger.info('ControlConnection - El puerto o la dirección IP de la conexion de control no son válidos.')
			Application.getInstance().getInterface().notify('Error al iniciar la conexión de control en la ip y puerto especificados.')
			Application.getInstance().getInterface().showControlConnectionError()
			return

		Application.getInstance().getInterface().showControlConnectionSuccess()

		# Indicamos el numero de conexiones
		self.server.listen(self.maxConnections)
		self.logger.debug('ControlConnection - Conexión de control inicializada en {}:{}'.format(self.ip, self.port))
		self.server.settimeout(1)

		# Establecemos el Event
		self.runningEvent.set()

		while self.runningEvent.is_set():
			try:
				client_sock, address = self.server.accept()
				self.logger.debug('ControlConnection - Aceptada conexion de {}:{}.'.format(address[0], address[1]))
				# Un único para así saber siempre quien es el usuario que nos llama, por ejemplo
				self.conexionHandler(client_sock)
			except socket.error as e:
				continue

	#
	# Método que notifica a la conexión TCP de la respuesta a una petición hecha a la intefaz.
	# Entrada:
	#	- answer: respuesta a la peticion
	#
	def answerRequest(self, answer):
		self.waitEvent.set()
		self.interfaceResponse = answer

	#
	# Método que gestiona una conexión entrante al servidor, interpretando el mensaje recibido
	# e interactuando con la interfaz de usuario para mostrar avisos, llamadas, etc.
	# Entrada:
	# 	- socket: socket en el que se recibe la conexión.
	#
	def conexionHandler(self, socket):
		try:
			request = socket.recv(1024).decode()
			self.logger.debug('ControlConnection -  Socket {}. Recibido: {}'.format(socket.getpeername(), request))
			request = request.split(' ')
			# Recibimos una llamada entrante
			if request[0] == 'CALLING':
				nick = request[1]
				dstUDPport = int(request[2])
				user = identityGestion.quertyUser(nick)
				if user == None:
					self.logger.error('ControlConnection - Usuario {} no encontrado. No se puede empezar la llamada.'.format(nick))
					return

				# Si ya estamos en una llamada, avisamos de que estamos ocupados y notificamos por la interfaz
				if Application.getInstance().getConnection() != None:
					socket.send('CALL_BUSY {}'.format(Application.getInstance().getUser().nick).encode())
					Application.getInstance().getInterface().notify('Llamada recibida del usuario {}'.format(nick))

				Application.getInstance().getInterface().showIncomingCall(user, True)				
				# Tenemos que esperar a que el usuario pulse el botón
				self.waitEvent.clear()
				self.waitEvent.wait(timeout = self.waitCallTimeout)

				if not self.waitEvent.is_set():
					# El usuario no ha respondido a la llamada
					Application.getInstance().getInterface().closeCallWindow()
					Application.getInstance().getInterface().notify('Llamada perdida del usuario {}'.format(nick))

				# El usuario decice aceptar la llamada
				if self.interfaceResponse == 'CALL_ACCEPTED':
					# Iniciamos la conexion UDP
					origPort = utils.getAvailablePort(self.ip)
					socket.send('CALL_ACCEPTED {} {}'.format(Application.getInstance().getUser().nick, origPort).encode())

					conn = udp.VideoConnection(self.ip, user.ip, origPort, dstUDPport, user, self.logger)
					if conn.start():
						Application.getInstance().setConnection(conn)
						Application.getInstance().getInterface().startCallWindow(user)
						Application.getInstance().getInterface().notify('Comenzando la llamada con el usuario {}'.format(nick))
					else:
						Application.getInstance().getInterface().notify('Error al comenzar la llamada con el usuario {}'.format(nick))

				# El usuario decice rechazar la llamada
				elif self.interfaceResponse == 'CALL_DENIED':
					# Colgamos la llamada
					socket.send('CALL_DENIED {}'.format(Application.getInstance().getUser().nick).encode())
				# El usuario indica que esta ocupado - De momento no se puede, no le vemos sentido
				elif self.interfaceResponse == 'CALL_BUSY':
					socket.send('CALL_BUSY {}'.format(Application.getInstance().getUser().nick).encode())
				else:
					self.logger.error('ControlConnection - Respuesta incorrecta por parte del usuario a CALLING: {}'.format(self.interfaceResponse))

			# Recibimos una llamada con audio entrante
			if request[0] == 'CALLING_V1':
				nick = request[1]
				dstVideoPort = int(request[2])
				dstAudioPort = int(request[3])
				user = identityGestion.quertyUser(nick)
				if user == None:
					self.logger.error('ControlConnection - Usuario {} no encontrado. No se puede empezar la llamada.'.format(nick))
					return

				# Si ya estamos en una llamada, avisamos de que estamos ocupados y notificamos por la interfaz
				if Application.getInstance().getConnection() != None:
					socket.send('CALL_BUSY {}'.format(Application.getInstance().getUser().nick).encode())
					Application.getInstance().getInterface().notify('Llamada recibida del usuario {}'.format(nick))

				Application.getInstance().getInterface().showIncomingCall(user, True)				
				# Tenemos que esperar a que el usuario pulse el botón
				self.waitEvent.clear()
				self.waitEvent.wait(timeout = self.waitCallTimeout)

				if not self.waitEvent.is_set():
					# El usuario no ha respondido a la llamada
					Application.getInstance().getInterface().closeCallWindow()
					Application.getInstance().getInterface().notify('Llamada perdida del usuario {}'.format(nick))

				# El usuario decice aceptar la llamada
				if self.interfaceResponse == 'CALL_ACCEPTED':
					# Iniciamos la conexion UDP
					ports = utils.getAvailablePort(self.ip, nports=2)
					origVideoPort, origAudioPort = ports[0], ports[1]

					socket.send('CALL_ACCEPTED_V1 {} {} {}'.format(Application.getInstance().getUser().nick, origVideoPort, origAudioPort).encode())

					conn = udp.VideoAudioCallConnection(self.ip, user.ip, origVideoPort, dstVideoPort, origAudioPort, dstAudioPort, user, self.logger)
					if conn.start():
						Application.getInstance().setConnection(conn)
						Application.getInstance().getInterface().startCallWindow(user)
						Application.getInstance().getInterface().notify('Comenzando la llamada con el usuario {}'.format(nick))
					else:
						Application.getInstance().getInterface().notify('Error al comenzar la llamada con el usuario {}'.format(nick))

				# El usuario decice rechazar la llamada
				elif self.interfaceResponse == 'CALL_DENIED':
					# Colgamos la llamada
					socket.send('CALL_DENIED {}'.format(Application.getInstance().getUser().nick).encode())
				# El usuario indica que esta ocupado - De momento no se puede, no le vemos sentido
				elif self.interfaceResponse == 'CALL_BUSY':
					socket.send('CALL_BUSY {}'.format(Application.getInstance().getUser().nick).encode())
				else:
					self.logger.error('ControlConnection - Respuesta incorrecta por parte del usuario a CALLING: {}'.format(self.interfaceResponse))

			# Si es una peticion sobre una conexion ya iniciada
			else:
				connection = Application.getInstance().getConnection()
				if connection == None:
					self.logger.error('ControlConnection - Recibido: {} cuando no habia conexion UDP iniciada'.format(request))
					return

				nick = request[1]
				if connection.dstUser.nick != nick:
					self.logger.error('ControlConnection - El usuario {} intenta infiltrarse en nuestra conexion con {}'.format(nick, connection.dstUser.nick))
					return

				# Recibimos una peticion para pausar la llamada
				if request[0] == 'CALL_HOLD':
					# Pausamos la conexion
					connection.pause()
					Application.getInstance().getInterface().setPauseResumeButton('Reanudar')
					Application.getInstance().getInterface().notify('El usuario {} ha pausado la conexion.'.format(nick))

				# Recibimos una peticion para reanudar la llamada
				elif request[0] == 'CALL_RESUME':
					# Reanudamos la conexion
					connection.resume()
					Application.getInstance().getInterface().setPauseResumeButton('Pausar')
					Application.getInstance().getInterface().notify('El usuario {} ha reanudado la conexion.'.format(nick))

				# Recibimos una peticion para detener definitivamente la llamada
				elif request[0] == 'CALL_END':
					# Eliminamos definitivamente la conexion
					Application.getInstance().getInterface().closeCallWindow()
					Application.getInstance().setConnection(None)
					connection.quit()
		finally:
			socket.close()

	#
	# Método que inicializa una llamada a un usuario, usando el protocolo más alto que tengan ambos en común.
	# Entrada:
	#	- dstUser: usuario al que queremos conectarnos
	#
	def connectWith(self, dstUser):
		# Se encarga de, según los protocolos soportados por dstUser, llamar a una funcion u a otra
		# En este caso la aplicacion solo soporta protocolo V0 o V1
		if 'V1' in dstUser.getProtocols():
			self.logger.debug('ControlConnection - Protocolo {} con usuario {}.'.format('V1', dstUser.nick))
			self.startCallV1(dstUser.nick, dstUser.ip, dstUser.port)
		# Si no, protocolo V0 que siempre deberia estar soportado
		else:
			self.logger.debug('ControlConnection - Protocolo {} con usuario {}.'.format('V0', dstUser.nick))
			self.startCallV0(dstUser.nick, dstUser.ip, dstUser.port)

	#
	# Método que inicializa una llamada del protocolo V0, es decir, videollamada sin audio
	# Entrada:
	#	- nick: usuario al que queremos conectarnos
	#	- ip: ip de la conexión de control del usuario al que queremos conectarnos
	#	- port: puerto de la conexión de control del usuario al que queremos conectarnos
	#
	def startCallV0(self, nick, ip, port):
		origPort = utils.getAvailablePort(self.ip)
		origUser = Application.getInstance().getUser()
		if origUser == None:
			self.logger.error('ControlConnection - Usuario origen no loggeado.')
			return

		message = 'CALLING {} {}'.format(origUser.nick, origPort)
		response = utils.sendTCPMessage(message, ip, port, timeout=self.waitCallTimeout)
		if response == None:
			self.logger.error('ControlConnection - Respuesta no recibida al contactar: {}-{}:{}.'.format(nick, ip, port))
			Application.getInstance().getInterface().closeCallWindow()
			Application.getInstance().getInterface().notify('El usuario {} no está disponible ahora mismo.'.format(nick))
			return

		response = response.split(' ')

		self.logger.debug('ControlConnection - {} \n\tGot response: {}'.format(message, response))
		if response[0] == 'CALL_ACCEPTED':
			nick = response[1]
			dstUDPport = int(response[2])
			user = identityGestion.quertyUser(nick)
			if user == None:
				self.logger.error('ControlConnection - Usuario {} no encontrado. No se puede aceptar la llamada entrante.'.format(nick))
				return

			conn = udp.VideoConnection(self.ip, user.ip, origPort, dstUDPport, user, self.logger)
			if conn.start():
				Application.getInstance().setConnection(conn)
				Application.getInstance().getInterface().startCallWindow(user)
				Application.getInstance().getInterface().notify('Comenzando la llamada con el usuario {}'.format(nick))
			else:
				Application.getInstance().getInterface().notify('Error al comenzar la llamada con el usuario {}'.format(nick))

		elif response[0] == 'CALL_DENIED':
			nick = response[1]
			self.logger.debug('ControlConnection - El usuario {} no encontrado ha denegado la llamada.'.format(nick))
			Application.getInstance().getInterface().closeCallWindow()
			Application.getInstance().getInterface().notify('El usuario {} ha colgado.'.format(nick))

		elif response[0] == 'CALL_BUSY':
			self.logger.debug('ControlConnection - El usuario {} está ocupado.'.format(nick))
			Application.getInstance().getInterface().closeCallWindow()
			Application.getInstance().getInterface().notify('El usuario {} está ocupado en estos momentos.'.format(nick))
		else:
			self.logger.error('ControlConnection - Respuesta incorrecta: {}.'.format(response))

	#
	# Método que inicializa una llamada del protocolo V1, es decir, videollamada con audio
	# Entrada:
	#	- nick: usuario al que queremos conectarnos
	#	- ip: ip de la conexión de control del usuario al que queremos conectarnos
	#	- port: puerto de la conexión de control del usuario al que queremos conectarnos
	#
	def startCallV1(self, nick, ip, port):
		ports = utils.getAvailablePort(self.ip, nports=2)
		origVideoPort, origAudioPort = ports[0], ports[1]

		origUser = Application.getInstance().getUser()
		if origUser == None:
			self.logger.error('ControlConnection - Usuario origen no loggeado.')
			return

		message = 'CALLING_V1 {} {} {}'.format(origUser.nick, origVideoPort, origAudioPort)
		response = utils.sendTCPMessage(message, ip, port, timeout=self.waitCallTimeout)
		if response == None:
			self.logger.error('ControlConnection - Respuesta no recibida al contactar: {}-{}:{} para llamada con audio.'.format(nick, ip, port))
			Application.getInstance().getInterface().closeCallWindow()
			Application.getInstance().getInterface().notify('El usuario {} no está disponible ahora mismo.'.format(nick))
			return

		response = response.split(' ')

		self.logger.debug('ControlConnection - {} \n\tGot response: {}'.format(message, response))
		if response[0] == 'CALL_ACCEPTED_V1':
			nick = response[1]
			dstVideoPort = int(response[2])
			dstAudioPort = int(response[3])
			user = identityGestion.quertyUser(nick)
			if user == None:
				self.logger.error('ControlConnection - Usuario {} no encontrado. No se puede aceptar la llamada con audio entrante.'.format(nick))
				return

			conn = udp.VideoAudioCallConnection(self.ip, user.ip, origVideoPort, dstVideoPort, origAudioPort, dstAudioPort, user, self.logger)
			if conn.start():
				Application.getInstance().setConnection(conn)
				Application.getInstance().getInterface().startCallWindow(user)
				Application.getInstance().getInterface().notify('Comenzando la llamada con audio con el usuario {}'.format(nick))
			else:
				Application.getInstance().getInterface().notify('Error al comenzar la llamada con audio con el usuario {}'.format(nick))

		elif response[0] == 'CALL_DENIED':
			nick = response[1]
			self.logger.debug('ControlConnection - El usuario {} no encontrado ha denegado la llamada con audio.'.format(nick))
			Application.getInstance().getInterface().closeCallWindow()
			Application.getInstance().getInterface().notify('El usuario {} ha colgado.'.format(nick))

		elif response[0] == 'CALL_BUSY':
			self.logger.debug('ControlConnection - El usuario {} está ocupado para una llamada con audio.'.format(nick))
			Application.getInstance().getInterface().closeCallWindow()
			Application.getInstance().getInterface().notify('El usuario {} está ocupado en estos momentos.'.format(nick))
		else:
			self.logger.error('ControlConnection - Respuesta incorrecta a llamada con audio: {}.'.format(response))

	#
	# Método que notifica al usuario con el que estamos conectados de que queremos finalizar 
	# la llamada, además de cerrar la conexión UDP correspondiente.
	#
	def endCall(self):
		origUser = Application.getInstance().getUser()
		if origUser == None:
			self.logger.error('ControlConnection - Usuario origen no loggeado.')
			return

		connection = Application.getInstance().getConnection()
		if connection == None:
			self.logger.error('ControlConnection - Connection is none on call end.')
			return

		dstUser = connection.dstUser

		message = 'CALL_END {}'.format(origUser.nick)
		response = utils.sendTCPMessageOnly(message, dstUser.ip, dstUser.port)
		# Cerramos la conexion
		connection.quit()
		Application.getInstance().setConnection(None)

	#
	# Método que notifica al usuario con el que estamos conectados de que queremos pausar 
	# la llamada, además de pausar la conexión UDP correspondiente.
	#
	def holdCall(self):
		origUser = Application.getInstance().getUser()
		if origUser == None:
			self.logger.error('ControlConnection - Usuario origen no loggeado.')
			return

		connection = Application.getInstance().getConnection()
		if connection == None:
			self.logger.error('ControlConnection - Connection is none on call hold.')
			return

		dstUser = connection.dstUser

		message = 'CALL_HOLD {}'.format(origUser.nick)
		response = utils.sendTCPMessageOnly(message, dstUser.ip, dstUser.port)
		# Pausamos la conexion
		connection = Application.getInstance().getConnection()
		if connection != None:
			connection.pause()

	#
	# Método que notifica al usuario con el que estamos conectados de que queremos reanudar 
	# la llamada, además de reanudar la conexión UDP correspondiente.
	#
	def resumeCall(self):
		origUser = Application.getInstance().getUser()
		if origUser == None:
			self.logger.error('ControlConnection - Usuario origen no loggeado.')
			return

		connection = Application.getInstance().getConnection()
		if connection == None:
			self.logger.error('ControlConnection - Connection is none on call resume.')
			return

		dstUser = connection.dstUser

		message = 'CALL_RESUME {}'.format(origUser.nick)
		response = utils.sendTCPMessageOnly(message, dstUser.ip, dstUser.port)
		# Reanudamos la conexion
		connection = Application.getInstance().getConnection()
		if connection != None:
			connection.resume()

	#
	# Método que ciera la conexión TCP.
	# Puede tardar hasta 1 segundo.
	#
	def quit(self):
		self.runningEvent.clear()
		self.server.close()
		time.sleep(1)
			

