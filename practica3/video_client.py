from user import saveUserInfo, getUserInfo
from application import Application
from PIL import Image, ImageTk
from udp import UDPConnection
from threading import Event
from appJar import gui
import identityGestion
import numpy as np
import logging
import control
import filters
import signal
import utils
import time
import cv2
import sys

######################################################################################
# Clase que representa la interfaz de nuestro cliente de videollamadas.
# Se encarga de comunicarse con la conexión de control para iniciar/parar/reanudar/
# detener las llamadas con otros usuarios.
# Inicializa y finaliza los hilos encargados de enviar vídeo y de mostrar el
# recibido, etc.
# Se encarga de mostrar la ventana de loggeo del usuario.
# Objetos:
#	- sentFrames: entero que indica el número de frames enviados.
#		Se resetea a cero cada vez que empezamos una videollamada nueva.
#	- timeCallStarted: almacena un objeto Time de cuándo comenzó la videollamada
#		actual. Se reseta cada vez que empezamos otra videollamada.
# 	- logger: logger usado para almacenar información sobre la ejecución y 
# 		posibles errores de la conexión
#	- fpsOutput: numero de fps a los que estamos enviando.
#	- fpsInput: numero de fps a los que estamos recibiendo.
#	- imageFilter: filtro aplicado a la imagen enviada.
#	- outputResolution: resolución del video que enviamos.
#	- inputResolution: resolución del video que recibimos.
#	- usingCamera: Event que nos permite saber si estamos usando la cámara
#		o enviando vídeo almacenado.
#	- app: interfaz AppJar
#
#####################################################################################
class VideoClient(object):

	#
	# Método instanciador de la clase.
	# Entrada:
	#	- window_size: tamaño de la ventana inicial a mostrar.
	# 	- logger: logger usado para almacenar información sobre la ejecución y 
	# 		posibles errores de la conexión
	#
	def __init__(self, window_size, logger):
		self.sentFrames = 0
		self.timeCallStarted = None
		self.logger = logger
		self.fpsOutput = 24
		self.fpsInput = 24
		# Filtro a aplicar a la imagen capturada por la webcam
		self.imageFilter = filters.apply_none
		self.outputResolution = (640, 480)
		self.inputResolution = (640, 480)
		self.correctlyLogged = Event()
		self.correctlyLogged.clear()
		self.closedInterface = Event()
		self.closedInterface.clear()

		# Permite saber si se envia video de la camara (set) o de un archivo (cleared)
		self.usingCamera = Event()
		self.usingCamera.set()

		# Creamos una variable que contenga el GUI principal
		self.app = gui(utils.NAME, window_size)
		self.app.setGuiPadding(10,10)
		# Evitar warnings innecesarios como el que una imagen no se cambia
		self.app.setLogLevel(logging.ERROR)

		# Definimos la funcion de cierre de la aplicacion
		self.app.setStopFunction(lambda:self.app.thread(self.stop))

		# Preparación del interfaz
		self.app.addLabel('titleLabel', 'Cliente Multimedia P2P - Redes2' )
		self.app.addImage('video', 'imgs/webcam_off.gif')
		self.app.setImageWidth('video', self.outputResolution[0])
		self.app.setImageHeight('video', self.outputResolution[1])

		# Añadimos la caja para elegir el filtro
		self.app.addOptionBox('filtersOptionBox', filters.FILTERS.keys())
		self.app.setOptionBoxChangeFunction('filtersOptionBox', self.buttonsCallback)

		# Añadir los botones
		self.app.addButtons(['Conectar', 'Colgar', 'Cargar video', 'Salir'], self.buttonsCallback)
		# El boton de colgar solo debería estar activo mientras hacemos una llamada
		self.app.disableButton('Colgar')

		# Iniciamos la ventana secundaria para cuando hagamos una llamada
		self.app.startSubWindow('videoWindow', title='Received video')
		self.app.addLabel('incomingCallLabel', 'Llamada entrante')
		self.app.addImage('receivedVideoImage', 'imgs/user_icon.gif')
		self.app.setImageWidth('receivedVideoImage', self.inputResolution[0])
		self.app.setImageHeight('receivedVideoImage', self.inputResolution[1])
		self.app.addButtons(['Aceptar', 'Rechazar'], self.buttonsCallback)
		self.app.addNamedButton('Pausar', 'pauseResumeButton', self.buttonsCallback)
		self.app.hideButton('pauseResumeButton')
		self.app.stopSubWindow()

		# Barra de estado
		# Debe actualizarse con información útil sobre la llamada (duración, FPS, etc...)
		self.app.addStatusbar(fields=3)

		self.initLoginWindow()
		self.initSearchNickWindow()

	#
	# Función que inicializa la interfaz, mostrando la ventana de login.
	#
	def start(self):
		self.app.go(startWindow='loginWindow')

	#
	# Función auxliar llamada cada vez que el usuario pulsa la X de cerrar la aplicación.
	# Como tenemos nuestro propio manejador de Ctrl+C simplemente tiene que devolver True.
	#
	def auxStop(self):
		return True

	#
	# Funcion usada para terminar la aplicacion.
	# Es llamada desde un manejador de señales, por lo
	# que necesita dos parametros.
	# Si el usuario no se ha loggeado, no hacemos nada, se gestiona desde preLoginStop. 
	# Entrada:
	#	- signal: botón desde el cual se cierra la aplicación.
	#	- _: variable a ignorar.
	#
	def stop(self, signal=None, _=None):
		# Al hacer sys.exit(0), es posible que el manejador de Ctrl+C llame a la funcion
		# En ese caso, ya se habrá cerrado todo. Así evitamos fallos.
		if self.closedInterface.is_set():
			return True

		print('Cerramos la aplicacion')
		self.closedInterface.set()
		try:
			# Dejamos tiempo para que los hilos de mostrar video acaben
			self.notify('Cerrando la aplicación.')
			time.sleep(1)

			# Liberamos el archivo de video usado
			if not self.usingCamera.is_set():
				self.cap.release()

			connection = Application.getInstance().getConnection()
			if connection != None:
				user = connection.dstUser
				# Colgamos la llamada con el usuario
				self.notify('Finalizando la llamada.')
				Application.getInstance().getControlConnection().endCall()
				self.closeCallWindow()

			self.notify('Cerrando la conexión de control.')
			Application.getInstance().getControlConnection().quit()
			self.app.queueFunction(sys.exit, 0)
			return True
		except Exception as e:
			self.logger.exception('VideoClient - Error al cerrar: '+str(e))
			self.app.queueFunction(sys.exit, 0)

	#
	# Función que, dado un frame OpenCV, realiza la codificación necesaria
	# para enviar el paquete por la conexión activa.
	# Entrada:
	#	- frame: frame OpenCV a enviar por la red.
	#	- hres: resolución horizontal del frame.
	#	- vres: resolución horizontal del frame.
	#	- fps: fps a los que se envía el vídeo
	#
	def enviarFrame(self, frame, hres, vres, fps):
		connection = Application.getInstance().getConnection()
		if connection != None and connection.isRunning():

			encode_param = [cv2.IMWRITE_JPEG_QUALITY,50] #50% calidad. Cambiar mas adelante
			result,encimg = cv2.imencode('.jpg', frame, encode_param)
			if result == False:
				self.logger.error('VideoClient - Error al codificar la imagen a enviar')
				return

			imgData = encimg.tobytes() # Codificamos la imagen
			data = '{}#{}#{}#{}#'.format(str(self.sentFrames), str(time.time()), '{}x{}'.format(hres, vres), str(fps))
			data = data.encode()+imgData

			connection.send(data)
			self.sentFrames += 1

	#
	# Función que captura el frame de la webcam a mostrar en cada momento.
	# Corre en un hilo distinto al de la interfaz, mientras usingCamera esté activo.
	# Si hay una conexión UDP establecida, se envía el frame por la conexión UDP.
	#
	def capturaVideo(self):
		# Si se llama a la funcion, es porque vamos a usar la camara
		self.app.setImage('video', 'imgs/webcam_off.gif')
		self.cap = cv2.VideoCapture(0)
		self.setImageResolution('HIGH')
		self.fpsOutput = 24
		self.usingCamera.set()

		self.app.setButton('Cargar video', 'Cargar video')

		# Capturamos un frame de la cámara o del vídeo
		while not self.closedInterface.is_set() and self.usingCamera.is_set():
			start = time.time()
			frameTime = 1/self.fpsOutput

			frame = None
			try:
				ret, frame = self.cap.read()
				frame = cv2.resize(frame, (640,480))
				#frame = cv2.bitwise_not(frame)
				frame = self.imageFilter(frame)
				cv2_im = cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
				img_tk = ImageTk.PhotoImage(Image.fromarray(cv2_im))

				# Lo mostramos en el GUI
				self.app.setImageData('video', img_tk, fmt = 'PhotoImage')
				self.app.setImageWidth('video', self.outputResolution[0])
				self.app.setImageHeight('video', self.outputResolution[1])
			except Exception as e:
				# Si no hemos podido capturar la imagen de la webcam (por que no tiene por ejemplo)
				# no tiene sentido que intentemos enviar nada
				return

			# Enviamos el frame a la red
			self.enviarFrame(frame, self.outputResolution[0], self.outputResolution[1], self.fpsOutput)

			# Pausamos el tiempo necesario para cuadrar los fps
			pauseTime = frameTime - (time.time() - start)
			if pauseTime < 0:
				continue
			time.sleep(pauseTime)

	#
	# Función que captura el frame de un archivo de vídeo a mostrar en cada momento.
	# Corre en un hilo distinto al de la interfaz, mientras usingCamera esté inactivo.
	# Si hay una conexión UDP establecida, se envía el frame por la conexión UDP.
	# Una vez termina la reproducción del vídeo, se inicializa otro thread que vuelve 
	# a mostrar y/o enviar la webcam.
	# Entrada:
	#	- path: dirección del archivo a mostrar.
	#
	def capturaVideoArchivo(self, path):
		# Detenemos el hilo de la webcam, puede tardar un poco
		self.usingCamera.clear()
		time.sleep(0.2)

		self.app.setButton('Cargar video', 'Webcam')

		# Cargamos el path
		self.cap = cv2.VideoCapture(path)
		# Cargamos los fps del video
		(major_ver, minor_ver, subminor_ver) = (cv2.__version__).split('.')

		if int(major_ver)  < 3 :
			fps = self.cap.get(cv2.cv.CV_CAP_PROP_FPS)
			width = int(self.cap.get(cv2.cv.CV_CAP_PROP_FRAME_WIDTH))
			height = int(self.cap.get(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT))
		else:
			fps = self.cap.get(cv2.CAP_PROP_FPS)
			width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
			height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

		self.outputResolution = (width, height)
		self.fpsOutput = int(fps)
		self.logger.info('Reproduciendo video {} a {} fps.'.format(path, fps))

		frameTime = 1/self.fpsOutput

		while not self.closedInterface.is_set() and self.cap.isOpened() and not self.usingCamera.is_set():
			start = time.time()
			try:
				ret, frame = self.cap.read()
				if ret == False:
					# El video ya ha acabado
					break

				frame = self.imageFilter(frame)
				cv2_im = cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
				img_tk = ImageTk.PhotoImage(Image.fromarray(cv2_im))

				# Lo mostramos en el GUI
				self.app.setImageData('video', img_tk, fmt = 'PhotoImage')

				# Enviamos el frame a la red
				self.enviarFrame(frame, self.outputResolution[0], self.outputResolution[1], self.fpsOutput)
			except Exception as e:
				# Si ha habido algun error al cargar el frame, no enviamos nada
				pass

			# Pausamos el tiempo necesario para cuadrar los fps
			pauseTime = frameTime - (time.time() - start)
			if pauseTime < 0:
				continue
			time.sleep(pauseTime)

		# Una vez acaba la reproduccion del video,
		# volvemos a usar la webcam
		if not self.closedInterface.is_set():
			self.cap.release()
			self.app.thread(self.capturaVideo)

	#
	# Función encargada de leer los paquetes de la conexión UDP establecida y mostrar los
	# frames en la sub ventana de recepción. Corre en un hilo secundario.
	#
	def recibeVideo(self):
		connection = Application.getInstance().getConnection()
		while not self.closedInterface.is_set() and connection != None:
			start = time.time()
			frameTime = 1/self.fpsOutput

			if connection.isRunning():
				try: 
					msg = connection.rcv()
					frame = msg['image']
					self.fpsInput = msg['fps']
					self.inputResolution = msg['resolution']
					img_tk = ImageTk.PhotoImage(frame)
					# Lo mostramos en el GUI
					self.app.setImageData('receivedVideoImage', img_tk, fmt = 'PhotoImage')
					self.app.setImageWidth('receivedVideoImage', self.inputResolution[0])
					self.app.setImageHeight('receivedVideoImage', self.inputResolution[1])

					self.app.setStatusbar('Recibiendo a {}x{}/{} fps.'.format(self.inputResolution[0], self.inputResolution[1], msg['fps']), field=0)
					self.app.setStatusbar('Retraso de {:+.3f} segundos.'.format(time.time() - msg['timestamp']), field=1)
					self.app.setStatusbar('Duracion de la llamada: {} segundos'.format(utils.timedeltaToStr(time.time() - self.timeCallStarted)), field=2)

				except BlockingIOError as e:
					# No recibimos datos
					self.app.setImage('receivedVideoImage', 'imgs/user_icon.gif')
				except TypeError as e:
					# timeCallStarted es None por haber sido cambiado en otro hilo al cerrarse la llamada
					pass

			# Pausamos el tiempo necesario para cuadrar los fps
			pauseTime = frameTime + start - time.time() # frameTime - (time.time() - start)
			if pauseTime < 0:
				continue
			time.sleep(pauseTime)
			connection = Application.getInstance().getConnection()

	#
	# Función encargada de mostrar una llamada entrante de forma que el usuario pueda
	# aceptarla o rechazarla. Llamada desde la conexión de control al recibir una llamada.
	# Entrada:
	#	- user: Usuario que envía la llamada.
	#	- showButtons: Boolean que indica que botones mostrar: Aceptar y Rechazar / Pausar
	#
	def showIncomingCall(self, user, showButtons):
		if showButtons:
			self.app.queueFunction(self.app.showButton, 'Aceptar')
			self.app.queueFunction(self.app.showButton, 'Rechazar')
			self.app.queueFunction(self.app.hideButton, 'pauseResumeButton')
		else:
			self.app.queueFunction(self.app.hideButton, 'Aceptar')
			self.app.queueFunction(self.app.hideButton, 'Rechazar')
			self.app.queueFunction(self.app.showButton, 'pauseResumeButton')

		# Deshabilitamos el boton de conectar y habilitamos el de colgar

		self.app.queueFunction(self.app.setImage, 'receivedVideoImage', 'imgs/user_icon.gif')
		self.app.queueFunction(self.app.setLabel, 'incomingCallLabel', 'Recibiendo llamada de {}'.format(user))
		self.app.queueFunction(self.app.showSubWindow, 'videoWindow')

	#
	# Establece la resolución de la imagen capturada
	# Entrada: Código de la resolución a establecer: LOW, MEDIUM, HIGH, ULTRA
	#
	def setImageResolution(self, resolution):
		# Se establece la resolución de captura de la webcam
		# Puede añadirse algún valor superior si la cámara lo permite
		# pero no modificar estos
		self.logger.debug('VideoClient - Resolution set to {}.'.format(resolution))
		if resolution == 'LOW':
			self.outputResolution = (160, 120)
			self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 160)
			self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 120)
		elif resolution == 'MEDIUM':
			self.outputResolution = (320, 240)
			self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
			self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
		elif resolution == 'HIGH':
			self.outputResolution = (640, 480)
			self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
			self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
		elif resolution == 'ULTRA':
			self.outputResolution = (1920, 1080)
			self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920) 
			self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

	#
	# Función que inicializa la ventana de búsqueda de usuarios, para posteriormente
	# mostrarla y/o ocultarla.
	# Una vez elegido un usuario, llama a dicho usuario.
	#
	def initSearchNickWindow(self):
		self.app.startSubWindow('searchNickWindow', modal=True, title='Elige el usuario')
		
		# Lista de usuarios
		self.app.addLabel('Selecciona un usuario de la lista')

		self.app.addListBox('usersListBox', [])

		callbackListBox = lambda x: self.app.thread(self.connectTo, self.app.getListBox(x), 'ListBox')
		self.app.setListBoxChangeFunction('usersListBox', callbackListBox)
		self.app.setListBoxMulti('usersListBox', multi=False)

		# Entrada del nick del usuario a conectar
		self.app.addLabel('Buscar por nick')
		self.app.addEntry('searchNickEntry')
		self.app.setEntryDefault('searchNickEntry', 'Introduce el nick del usuario a buscar')

		callbackEntry = lambda x: self.app.thread(self.connectTo, self.app.getEntry('searchNickEntry'), 'Entry')
		self.app.addNamedButton('Buscar usuario','getNickButton', callbackEntry)

		self.app.stopSubWindow()

	#
	# Función encargada de cargar los usuarios a mostrar en updateListBox.
	#
	def populateSearchNickWindow(self):
		self.logger.debug('VideoClient - Populating search nick window.')
		users = identityGestion.listUsers()
		users = list(map(lambda u: u.nick, users))
		# Eliminamos nuestro usuario de la lista
		nick = Application.getInstance().getUser().nick
		if nick in users:
			users.remove(nick)

		self.app.queueFunction(self.app.updateListBox, 'usersListBox', users)

	# 
	# Función llamada al seleccionar un usuario de updateListBox o escribir su nick en searchNickEntry.
	# Utiliza la conexión de control para conectar con el usuario para iniciar una videollamada.
	# Entrada:
	#	- nick: nick del usuario a llamar
	#	- entry: entrada desde la que se ha llamado. Necesaria para determinar el formato 
	#		de nick
	#
	def connectTo(self, nick, entry):
		if nick == []:
			# Al iniciarse por primera vez
			return

		if entry == 'ListBox':
			nick = nick[0]

		self.app.queueFunction(self.app.hideSubWindow, 'searchNickWindow')
		self.notify('Buscando al usuario en el servidor')
		user = identityGestion.quertyUser(nick)

		if user == None:
			self.notify('Error al obtener los datos del usuario {}'.format(nick))
		else:
			# Comenzamos la llamada
			self.notify('Llamando al usuario {}'.format(user))
			# Deshabilitamos el boton de conectar hasta que se haya finalizado la llamada
			self.app.queueFunction(self.app.disableButton, 'Conectar')
			self.app.queueFunction(self.app.enableButton, 'Colgar')
			Application.getInstance().getControlConnection().connectWith(user)

	#
	# Muestra la pantalla de recepción de vídeo de la aplicación.
	# Llamada desde la conexión de control de la aplicación una vez se ha establecido la llamada.
	# Entrada:
	#	- dtsUser: User con el que hemos establecido la llamada
	#
	def startCallWindow(self, dstUser):
		self.app.queueFunction(self.showIncomingCall, dstUser, False)

		# Deshabilitamos el boton de conectar y habilitamos el de colgar
		self.app.queueFunction(self.app.disableButton, 'Conectar')
		self.app.queueFunction(self.app.enableButton, 'Colgar')

		self.sentFrames = 0
		self.timeCallStarted = time.time()

		# Iniciamos un hilo para recibir la informacion
		self.app.thread(self.recibeVideo)
		self.notify('En llamada con {}.'.format(dstUser.nick))

	#
	# Cierra la ventana de recepcion de video una vez ha acabado la conexion.
	# Llamada desde la conexion de control.
	#
	def closeCallWindow(self):
		self.logger.debug('VideoClient - Connection stopped.')
		self.sentFrames = 0
		self.timeCallStarted = None
		self.app.queueFunction(self.app.hideSubWindow, 'videoWindow')
		self.app.queueFunction(self.app.enableButton, 'Conectar')
		self.app.queueFunction(self.app.disableButton, 'Colgar')

		# Reseteamos la imagen de llamada entrante para futuras llamadas
		self.app.queueFunction(self.app.setImage, 'receivedVideoImage', 'imgs/user_icon.gif')

		# Reseteamos los campos de la statusbar
		self.app.queueFunction(self.app.setStatusbar, '', field=0)
		self.app.queueFunction(self.app.setStatusbar, '', field=1)
		self.app.queueFunction(self.app.setStatusbar, '', field=2)

		self.notify('Logeado correctamente como '+str(Application.getInstance().getUser().nick))

	#
	# Establece el texto deseado en el boton pauseResume
	# Entrada:
	#	- text: texto a mostrar en el botón pauseResumeButton
	def setPauseResumeButton(self, text):
		self.app.queueFunction(self.app.setButton, 'pauseResumeButton', text)

	#
	# Función que gestiona los callbacks de los botones.
	# Entrada:
	#	- button: botón que ha sido accionado.
	#
	def buttonsCallback(self, button):
		self.logger.debug('VideoClient - Pressed {} button.'.format(button))
		if button == 'Salir':
			# Salimos de la aplicación
			self.app.thread(self.stop)

		if button == 'Colgar':
			# Avisamos a la conexion de control, que se encarga automáticamente de cerrar la conexion
			# Como el proceso de detener la conexion puede tardar, lo hacemos en otro hilo
			self.app.thread(Application.getInstance().getControlConnection().endCall)
			self.closeCallWindow()
			self.app.enableButton('Conectar')
			self.app.disableButton('Colgar')

		elif button == 'Conectar':
			self.app.thread(self.populateSearchNickWindow)
			self.app.showSubWindow('searchNickWindow')

		elif button == 'Aceptar':
			Application.getInstance().getControlConnection().answerRequest('CALL_ACCEPTED')

		elif button == 'Rechazar':
			Application.getInstance().getControlConnection().answerRequest('CALL_DENIED')
			self.app.hideSubWindow('videoWindow')

		elif button == 'Cargar video':
			if self.usingCamera.is_set():
				path = self.app.openBox(title='Load video', fileTypes=[('video', '.mp4'), ('video', '.avi')], asFile=False, parent=None)
				if isinstance(path, str):
					# Si no se selecciona un archivo, devuelve una tupla
					self.app.thread(self.capturaVideoArchivo, path)
			else:
				# Al hacer set de usingCamera, la funcion de mandar el archivo termina e inicia la de la webcam
				self.usingCamera.set()

		elif button == 'pauseResumeButton':
			connection = Application.getInstance().getConnection()
			if connection == None:
				self.logger.error('VideoClient - Connection is none on Pause/Resume button click.')
				return

			if connection.isRunning():
				self.logger.debug('VideoClient - Paused connection with user {}'.format(connection.dstUser))
				self.app.queueFunction(Application.getInstance().getControlConnection().holdCall)
				self.setPauseResumeButton('Reanudar')

			elif connection.isPaused():
				self.logger.debug('VideoClient - Resumed connection with user {}'.format(connection.dstUser))
				self.app.queueFunction(Application.getInstance().getControlConnection().resumeCall)
				self.setPauseResumeButton('Pausar')

		elif button == 'filtersOptionBox':
			self.imageFilter = filters.FILTERS[self.app.getOptionBox('filtersOptionBox')]

	#
	# Cierra la aplicación si pulsamos antes de habernos loggeado, es decir, desde
	# la cruz X de la ventana loginWindow.
	# Usamos el evento de forma que evitamos cerrar la aplicación al ocultar
	# la ventana por haberse loggeado.
	#
	def preLoginStop(self):
		if not self.correctlyLogged.is_set():
			print('Cerramos la ventana login')
			sys.exit(0)
		return True

	#
	# Función que inicializa la sub ventana de loggeo y/o registro.
	#
	def initLoginWindow(self):
		self.app.startSubWindow('loginWindow', modal=True)
		self.app.addLabel('infoLabel', '', 1, 0, 2)
		# Si se cierra la ventana, tenemos que cerrar el programa entero
		self.app.setStopFunction(self.preLoginStop)

		# Preparación del interfaz
		with self.app.labelFrame('Register', 0, 0):
			self.app.addLabel('registerInfoLabel', 'Register as a new user on the system')
			# Nick
			self.app.addEntry('registerNickEntry')
			self.app.setEntryDefault('registerNickEntry', 'Nick')
			#Password
			self.app.addSecretEntry('registerPasswordEntry')
			self.app.setEntryDefault('registerPasswordEntry', 'Password')
			# IP
			self.app.addEntry('registerIPEntry')
			self.app.setEntryDefault('registerIPEntry', 'IP as: 192.168.1.40')
			# Port
			self.app.addEntry('registerPortEntry')
			self.app.setEntryDefault('registerPortEntry', 'Port as: 8000')
			
			self.app.addButton('Register user', lambda x: self.app.thread(self.register, x))
			self.app.setButtonSticky('Register user', 'right')

		with self.app.labelFrame('Login', 0, 1):
			self.app.addSecretEntry('loginPasswordEntry')
			self.app.setEntryDefault('loginPasswordEntry', 'Password')

			self.app.addButton('Login', lambda x: self.app.thread(self.login, x))
			self.app.setButtonSticky('Login', 'right')

		user = getUserInfo()
		if user == None:
			self.app.hideLabelFrame('Login')
		else:
			self.app.setLabelFrameTitle('Login', 'Login as {}'.format(user.nick))

		self.app.stopSubWindow()

	#
	# Función llamada desde la conexión de control para informar de que hay un error 
	# al intentar iniciarla en la ip y puerto especificados.
	# Muestra de nuevo la pantalla de loggeo impidiendo al usuario interactuar con la ventana principal.
	#
	def showControlConnectionError(self):
		self.correctlyLogged.clear()
		self.notifyLogin('Error. La ip o puertos establecidos no son válidos')
		self.app.queueFunction(self.app.hideLabelFrame, 'Login')
		user = getUserInfo()
		if user != None:
			self.app.queueFunction(self.app.setEntry, 'registerNickEntry', user.nick)
			self.app.queueFunction(self.app.setEntry, 'registerIPEntry', user.ip)
			self.app.queueFunction(self.app.setEntry, 'registerPortEntry', user.port)
			self.app.queueFunction(self.app.enableButton, 'Register user')
			self.app.queueFunction(self.app.enableButton, 'Login')


	#
	# Función llamada desde la conexión de control para informar de que se ha
	# iniciado correctamente, de forma que se muestra la interfaz principal
	# Oculta la pantalla de loggeo permitiendo al usuario interactuar con la ventana principal.
	#
	def showControlConnectionSuccess(self):
		self.correctlyLogged.set()
		user = Application.getInstance().getUser()
		if user == None:
			self.logger.error('Una vez iniciada la conexion de control User is None')
			return
		self.notify('Logeado correctamente como '+str(user.nick))
		self.app.queueFunction(self.app.hideSubWindow, 'loginWindow')
		# Iniciamos la captura de video una vez estamos logeados.
		self.app.thread(self.capturaVideo)
		self.app.queueFunction(self.app.show)

	#
	# Notifica en la pantalla de login de posibles errores
	# Entrada:
	#	- text: texto a mostrar
	#
	def notifyLogin(self, text):
		self.app.queueFunction(self.app.setLabel, 'infoLabel', text)

	
	#
	# Notifica en la pantalla principal
	# Entrada:
	#	- text: texto a mostrar
	#
	def notify(self, text):
		self.app.queueFunction(self.app.setLabel, 'titleLabel', text)

	#
	# Función llamada al ser pulsado el botón loggear.
	# Lee los datos introducidos por el usuario e intenta loggearlo en el servidor de descubrimiento.
	# Entrada:
	#	- button: botón desde el que ha sido llamada.
	#
	def login(self, button):
		# Nos registramos / logeamos en el servidor de descubrimiento
		password = self.app.getEntry('loginPasswordEntry')
		if not password:
			self.notifyLogin('Es necesario que introduzcas una contraseña.')
		
		self.notifyLogin('Consultando información con el servidor.')
		# Deshabilitamos los botones mientras consultamos en el servidor para evitar 
		# posibles errores al pulsar varias veces
		self.app.queueFunction(self.app.disableButton, 'Register user')
		self.app.queueFunction(self.app.disableButton, 'Login')

		user = getUserInfo()
		if user == None:
			self.notifyLogin('Ha habido un error, el usuario no esta almacenado. Es necesario que se registre')
			self.app.queueFunction(self.app.hideLabelFrame, 'Login')
			return
			
		tmp = identityGestion.registerUser(user.nick, user.ip, user.port, password, '#'.join(user.protocols))
		if tmp != None:
			# La contraseña es correcta, acabamos
			Application.getInstance().setUser(tmp)
			Application.getInstance().startControlConnection(tmp.ip, tmp.port)
			# La conexión de control se encarga de mostrar o no la pantalla principal
		else:
			# Volvemos a habilitar los botones
			self.app.queueFunction(self.app.enableButton, 'Register user')
			self.app.queueFunction(self.app.enableButton, 'Login')
			self.notifyLogin('La contraseña es incorrecta o el usuario ya no existe.')

	#
	# Función llamada al ser pulsado el botón de registrarse.
	# Lee los datos introducidos por el usuario e intenta registrarlo en el servidor de descubrimiento.
	# Entrada:
	#	- button: botón desde el que ha sido llamada.
	#
	def register(self, button):
		# Nos registramos / logeamos en el servidor de descubrimiento
		nick = self.app.getEntry('registerNickEntry')
		if not nick:
			self.notifyLogin('Es necesario que introduzcas un nick.')
			return

		password = self.app.getEntry('registerPasswordEntry')
		if not password:
			self.notifyLogin('Es necesario que introduzcas una contraseña.')
			return

		ip = self.app.getEntry('registerIPEntry')
		if not ip or not utils.isIPv4(ip):
			self.notifyLogin('Es necesario que introduzcas una IPv4 válida.')
			return

		port = self.app.getEntry('registerPortEntry')
		if not port or not utils.isInteger(port) or int(port)<0 or int(port)>65535:
			self.notifyLogin('Es necesario que introduzcas un puerto válido.')
			return

		self.notifyLogin('Registrandote en el servidor.')
		# Deshabilitamos los botones mientras consultamos en el servidor para evitar 
		# posibles errores al pulsar varias veces
		self.app.queueFunction(self.app.disableButton, 'Register user')
		self.app.queueFunction(self.app.disableButton, 'Login')

		tmp = identityGestion.registerUser(nick, ip, int(port), password, '#'.join(Application.protocols))
		if tmp != None:
			# La contraseña es correcta, acabamos
			saveUserInfo(tmp)
			Application.getInstance().setUser(tmp)
			Application.getInstance().startControlConnection(tmp.ip, tmp.port)
			# La conexión de control se encarga de mostrar o no la pantalla principal
		else:
			# Volvemos a habilitar los botones
			self.app.queueFunction(self.app.enableButton, 'Register user')
			self.app.queueFunction(self.app.enableButton, 'Login')
			self.notifyLogin('Ya hay un usuario con este nick.')