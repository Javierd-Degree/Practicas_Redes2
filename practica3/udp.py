from logging.handlers import RotatingFileHandler
from threading import Lock, Thread, Event
from application import Application
from PIL import Image, ImageTk
import numpy as np
import logging
import socket
import utils
import queue
import time
import cv2

import struct
import math

######################################################################################
# Clase que gestiona una conexion UDP, con posibilidad de parar y reanudar, 
# leyendo continuamente en un buffer simple, que se trata en este caso de una lista
# Para enviar, introducimos en una cola y se envian continuamente desde dicha cola
# Objetos:
#	- buffer: buffer donde almacenamos los paquetes leidos desde la red
#	- outputBuffer: buffer donde almacenamos los paquetes a enviar a la red
#	- orIP: ip origen de la conexión (ip en la que recibimos)
#	- dstIP: ip destino de la conexión
#	- orPort: puerto origen de la conexion (puerto en el que recibimos)
#	- dstPort: puerto destino de la conexión
# 	- logger: logger usado para almacenar información sobre la ejecución y 
# 		posibles errores de la conexión
#	- maxTimeout: tiempo de timeout para la conexión. Puede tardar hasta
#		maxTimeout al cerrarse.
#	- rcvDataLen: tamaño máximo a leer de golpe. En este caso es un datagrama UDP
#	- pausedEvent: evento que indica si la conexion está pausada (cleared) o no (setted)
#	- closedEvent: evento que indica si la conexión está cerrada o no
# 	- rcvThread: variable que almacena el thread dedicado a recibir
#	- sendThread: variable que almacena el thread dedicado a enviar
#####################################################################################
class UDPConnection(object):

	#
	# Método instanciador de la clase
	# Objetos:
	#	- orIP: ip origen de la conexión (ip en la que recibimos)
	#	- dstIP: ip destino de la conexión
	#	- orPort: puerto origen de la conexion (puerto en el que recibimos)
	#	- dstPort: puerto destino de la conexión
	# 	- logger: logger usado para almacenar información sobre la ejecución y 
	# 		posibles errores de la conexión
	#	- maxTimeout: tiempo de timeout para la conexión. Puede tardar hasta
	#		maxTimeout al cerrarse.
	#	- rcvDataLen: tamaño máximo a leer de golpe. En este caso es un datagrama UDP
	#
	def __init__(self, orIP, dstIp, orPort, dstPort, logger, maxTimeout = 2, rcvDataLen = 65535):
		super(UDPConnection, self).__init__()
		self.buffer = []
		self.outputBuffer = queue.Queue(maxsize=120)
		self.orIP = orIP
		self.dstIp = dstIp
		self.orPort = orPort
		self.dstPort = dstPort
		self.maxTimeout = maxTimeout
		self.logger = logger
		self.rcvDataLen = rcvDataLen

		self.pausedEvent = Event()
		self.closedEvent = Event()
		self.rcvThread = None
		self.sendThread = None

	#
	# Método que inicializa la conexión, iniciando los hilos de enviar y recibir
	# y las dos conexiones UDP pertinentes.
	# Salida:
	# 	False si ha habido algún problema, True en caso contrario
	#
	def start(self):
		# Evento que indica que la conexion debe estar cerrada
		self.closedEvent.clear()
		# Inicializamos para que no se detengan los hilos
		self.pausedEvent.set()

		self.sendSocket = None
		self.rcvSocket = None
		# Receive socket - To receive information
		try:
			self.rcvSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			self.rcvSocket.bind((self.orIP, self.orPort))
			self.rcvSocket.settimeout(self.maxTimeout)
		except socket.error as e:
			self.logger.exception('UDPConnection - Receive socket {}:{}.'.format(self.orIP, self.orPort))
			return False

		time.sleep(2)
		self.logger.debug('UDPConnection - Escuchando en {}:{}'.format(self.orIP, self.orPort))

		self.rcvThread = Thread(target=self._rcvData)
		self.rcvThread.start()

		self.sendThread = Thread(target=self._sendData)
		self.sendThread.start()


		# Send socket - To send information
		try:
			self.sendSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			self.sendSocket.connect((self.dstIp, self.dstPort))
			self.sendSocket.settimeout(self.maxTimeout)
		except socket.error as e:
			self.logger.exception('UDPConnection - Send socket {}:{}.'.format(self.dstIp, self.dstPort))
			return False

		self.logger.debug('UDPConnection - Enviando en {}:{}'.format(self.orIP, self.orPort))
		return True

	#
	# Método que pausa la conexión
	#
	def pause(self):
		self.pausedEvent.clear()

	#
	# Método que reanuda la conexión
	#
	def resume(self):
		self.pausedEvent.set()

	#
	# Método que cierra la conexión. Puede tardar hasta maxTimeout en acabar.
	#
	def quit(self):
		# En caso de que la conexion este parada, evitamos que se bloquee
		self.pausedEvent.set()
		# Marcamos la conexion como acabada
		self.closedEvent.set()
		time.sleep(self.maxTimeout) # Los hilos pueden tardar hasta self.maxTimeout en acabar
		self.sendSocket.close()
		self.rcvSocket.close()
		return True

	#
	# Método que informa sobre si la conexión está o no cerrada.
	# Salida:
	#	True si la conexión está cerrada, False en caso contrario
	#
	def isClosed(self):
		return self.closedEvent.is_set()

	#
	# Método que informa sobre si la conexión está o no pausada.
	# Salida:
	#	True si la conexión está pausada, False en caso contrario
	#
	def isPaused(self):
		return not self.pausedEvent.is_set()

	#
	# Método que informa sobre si la conexión está o no funcionando.
	# La conexion esta funcionando si no esta cerrada ni parada.
	# Salida:
	#	True si la conexión está funcionando, False en caso contrario
	#
	def isRunning(self):
		return self.pausedEvent.is_set() and not self.closedEvent.is_set()

	#
	# Función auxiliar que introduce un objeto en el buffer de recepción
	# Entrada:
	# 	- data: objeto a almacenar en el buffer de recepción
	#
	def _bufferPush(self, data):
		self.buffer.append(data)

	#
	# Función auxiliar que extrae un elemento del buffer de recepción.
	# Salida:
	#	Elemento extraido del buffer de recepción
	#
	def _bufferPop(self):
		r = self.buffer[0]
		del self.buffer[0]

	#
	# Función auxiliar que informa del tamaño del buffer de recepción.
	# Salida:
	#	Tamaño del buffer de recepción
	#
	def _bufferLen(self):
		bufLen = len(self.buffer)
		return bufLen

	#
	# Funcion que se encarga de vaciar el buffer de envío
	#
	def _emptyOutputBuffer(self):
		while True:
			try:
				self.outputBuffer.get(False)
			except queue.Empty:
				break

	#
	# Función usada por el hilo sendSocket.
	# Se encarga de envíar por la conexión UDP de salida los paquetes almacenados en el buffer de salida.
	# Si en algún momento la conexión UDP se pausa, vacía el buffer de salida y se detiene hasta que sea reanudada.
	# Cuando la conexión se cierra, se finaliza automáticamente.
	#
	def _sendData(self):
		while not self.isClosed():
			if self.isPaused():
				# Si la conexion esta parada, vaciamos el buffer, no queremos
				# enviar esos datos
				self._emptyOutputBuffer()

			# Esperamos a que la conexion se reanude para enviar datos de nuevo
			self.pausedEvent.wait()
			try:
				data = self.outputBuffer.get(True, self.maxTimeout) # Como hemos establecido un timeout, sabemos que
													# no se va a quedar bloqueado indefinidamente y por tanto la conexion cerrara con exito
				self.sendSocket.send(data)
			except queue.Empty as e:
				continue
			except socket.error as e:
				# Socket timeout, perdemos el frame.
				# Vaciamos el buffer de envío, de forma que aunque perdamos algunos frames, la comunicación sigue
				# siendo en tiempo real
				self._emptyOutputBuffer()
				continue

	#
	# Función usada por el hilo rcvSocket.
	# Se encarga de leer los datos recibidos por la conexión UDP de entrada y almacenarlos en el
	# buffer de recepción usado _bufferPush.
	# Si en algún momento la conexión UDP se pausa, se detiene hasta que sea reanudada.
	# Cuando la conexión se cierra, se finaliza automáticamente.
	#
	def _rcvData(self):
		while not self.isClosed():
			# Comprobamos si la conexion esta o no parada
			self.pausedEvent.wait()

			try:
				request = self.rcvSocket.recv(self.rcvDataLen) 	# Leemos como maximo un datagrama UDP
				# Como hemos establecido un timeout, sabemos que no se va a quedar bloqueado indefinidamente
				# y por tanto la conexion cerrara con exito
				self._bufferPush(request)
			except socket.error as e:
				continue
	
	#
	# Función que introduce un dato en el buffer de envío para que el hilo
	# de envío se encarge de introducirlo en la red.
	# Si la conexión no está funcionando o el buffer de salida está lleno (120 elementos), se desecha.
	# Entrada:
	#	- data: array de bytes a enviar por la red
	#
	def send(self, data):
		# Si la conexion no esta cerrada ni esta parada, metemos en el buffer.
		# Si no, descartamos los datos
		if self.isRunning():
			if not self.outputBuffer.full():
				# Si el buffer esta lleno, perdemos el paquete, no pasa nada
				self.outputBuffer.put_nowait(data)

	#
	# Función que lee un elemento del buffer de recepción mediante una llamada a _bufferPop.
	# Entrada:
	#	- timeout: segundos a esperar como máximo.
	# Salida:
	#	Elemento leído si lo había antes de pasar el timeout o excepción BlockingIOError.
	#
	def rcv(self, timeout=5):
		start = time.time()
		# El rcv es bloqueante hasta que pase timeout segundos
		bufLen = 0
		while (time.time()-start) < timeout:
			bufLen = self._bufferLen()
			if bufLen != 0:
				break

		if bufLen == 0:
			raise BlockingIOError('Timeout passed.')

		return self._bufferPop()


######################################################################################
# Clase que gestiona una conexion UDP para enviar frames de vídeo con el formato
# especificado en la práctica, con posibilidad de parar y reanudar, leyendo
# continuamente en un buffer simple, que se trata en este caso de una lista
# Para enviar, introducimos en una cola y se envian continuamente desde dicha cola.
# Implementa recepción ordenada de los frames en una cola de prioridad.
# Almacena en el buffer de recepción los frames ya formateados con id, resolucion, etc.
# Objetos:
# 	- dstUser: usuario al que corresponde la conexión destino.
#	- Todos los objetos heredados de UDPConnection
#####################################################################################
class VideoConnection(UDPConnection):

	#
	# Método instanciador de la clase
	# Objetos:
	#	- orIP: ip origen de la conexión (ip en la que recibimos)
	#	- dstIP: ip destino de la conexión
	#	- orPort: puerto origen de la conexion (puerto en el que recibimos)
	#	- dstPort: puerto destino de la conexión
	#	- dstUser: usuario al que corresponde la conexión destino.
	# 	- logger: logger usado para almacenar información sobre la ejecución y 
	# 		posibles errores de la conexión
	#	- maxTimeout: tiempo de timeout para la conexión. Puede tardar hasta
	#		maxTimeout al cerrarse.
	#
	def __init__(self, orIP, dstIp, orPort, dstPort, dstUser, logger, maxTimeout = 2):
		super(VideoConnection, self).__init__(orIP, dstIp, orPort, dstPort, logger, maxTimeout = maxTimeout)
		self.buffer = queue.PriorityQueue(maxsize=120)
		self.dstUser = dstUser
		self.logger.debug('Conexion de video. Recibo en: {}:{}. Envio a {}:{}.'.format(orIP, orPort, dstIp, dstPort))


	#
	# Función auxiliar que procesa e introduce un objeto leído de la red en el buffer de recepción.
	# A partir del paquete leído, interpretamos número de secuencia, resolución, timestamp,
	# fps y la imagen, los formateamos e introducimos en el buffer un diccionario con dicha informacion.
	# Entrada:
	# 	- data: array de bytes leído de la red
	#
	def _bufferPush(self, data):
		try:
			data2 = data.split(b'#')

			decData = list(map(lambda x: x.decode(), data2[:4]))
			i = int(decData[0])												# Numero de fotograma
			timestamp = float(decData[1])									# Timestamp formato linux
			res = tuple(map(int, decData[2].split('x')))					# Cogemos las dos resoluciones
			fps = int(decData[3])											# Numero de fps

			image = b'#'.join(data2[4:])									# Imagen guardada como bytes, no podemos pasarla a imagen directamente
			image = cv2.imdecode(np.frombuffer(image, np.uint8), 1)			# Almacenamos la imagen directamente en el buffer
			cv2_im = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
			image = Image.fromarray(cv2_im) 								# Solo queda llamar a ImageTk.PhotoImage(image), que tiene que hacerse en el hilo principal

			frame = {
				'id' : i,
				'timestamp' : timestamp,
				'resolution' : res,
				'fps' : fps,
				'image' : image
			}

			if not self.buffer.full():
				# Si esta lleno, descartamos el paquete
				self.buffer.put_nowait((i, frame))
		except Exception as e:
			self.logger.exception('VideoConnection - Error al interpretar el mensaje recibido {}'.format(data))

	#
	# Función auxiliar que extrae un elemento del buffer de recepción.
	# Salida:
	#	Elemento extraido del buffer de recepción
	#
	def _bufferPop(self):
		# Devuelve una tupla (i, data)
		return self.buffer.get(False)[1]

	#
	# Función auxiliar que informa del tamaño del buffer de recepción.
	# Salida:
	#	Tamaño del buffer de recepción
	#
	def _bufferLen(self):
		return self.buffer.qsize()

	#
	# Función que lee un elemento del buffer de recepción mediante una llamada a _bufferPop.
	# Entrada:
	#	- timeout: segundos a esperar como máximo.
	# Salida:
	#	Elemento leído si lo había antes de pasar el timeout o excepción BlockingIOError.
	#
	def rcv(self, timeout=5):
		try:
			# Devuelve una tupla (i, data)
			return self.buffer.get(True, timeout)[1]
		except queue.Empty as e:
			raise BlockingIOError('Timeout passed.')


######################################################################################
# Clase que gestiona una conexion UDP para enviar frames de audio con el formato
# "numeroSecuencia#frame" , con posibilidad de parar y reanudar, leyendo
# continuamente en un buffer simple, que se trata en este caso de una lista
# Para enviar, introducimos en una cola y se envian continuamente desde dicha cola.
# Implementa recepción ordenada de los frames en una cola de prioridad.
# Almacena en el buffer de recepción los frames ya formateados con su id.
# Objetos:
# 	- dstUser: usuario al que corresponde la conexión destino.
#	- chunk: chunk usado por la conexión de audio.
#	- channels: número de canales usados por la conexión de audio.
#	- Todos los objetos heredados de UDPConnection.
#####################################################################################
class AudioConnection(UDPConnection):

	#
	# Método instanciador de la clase
	# Objetos:
	#	- orIP: ip origen de la conexión (ip en la que recibimos)
	#	- dstIP: ip destino de la conexión
	#	- orPort: puerto origen de la conexion (puerto en el que recibimos)
	#	- dstPort: puerto destino de la conexión
	#	- dstUser: usuario al que corresponde la conexión destino.
	#	- chunk: chunk usado por la conexión de audio.
	#	- channels: número de canales usados por la conexión de audio.
	# 	- logger: logger usado para almacenar información sobre la ejecución y 
	# 		posibles errores de la conexión
	#	- maxTimeout: tiempo de timeout para la conexión. Puede tardar hasta
	#		maxTimeout al cerrarse.
	#
	def __init__(self, orIP, dstIp, orPort, dstPort, dstUser, chunk, channels, logger, maxTimeout = 2):
		super(AudioConnection, self).__init__(orIP, dstIp, orPort, dstPort, logger, maxTimeout = maxTimeout, rcvDataLen = (chunk*channels*2))
		self.buffer = queue.PriorityQueue(maxsize=120)
		self.chunk = chunk
		self.channels = channels
		self.dstUser = dstUser
		self.logger.debug('Conexion de audio. Recibo en: {}:{}. Envio a: {}:{}.'.format(orIP, orPort, dstIp, dstPort))

	#
	# Función auxiliar que procesa e introduce un objeto leído de la red en el buffer de recepción.
	# A partir del paquete leído, interpretamos número de secuencia y audio, los introducimos en un 
	# diccionario y almacenamos el diccionario en el buffer de recepción.
	# Entrada:
	# 	- data: array de bytes leído de la red
	#
	def _bufferPush(self, data):
		# Interpretamos el paquete del buffer, para leer numero,
		# timestamp, etc, y solo guardar la imagen en el buffer
		try:
			data2 = data.split('#'.encode())

			decData = list(map(lambda x: x.decode(), data2[:1]))
			i = int(decData[0])

			audio = b'#'.join(data2[1:])

			frame = {
				'id' : i,
				'audio' : audio
			}

			if not self.buffer.full():
				# Si esta lleno, descartamos el paquete
				self.buffer.put_nowait((i, frame))
		except Exception as e:
			self.logger.exception('AudioConnection - Error al interpretar el mensaje recibido {}'.format(data))
			print(e)

	#
	# Función auxiliar que extrae un elemento del buffer de recepción.
	# Salida:
	#	Elemento extraido del buffer de recepción
	#
	def _bufferPop(self):
		# Devuelve una tupla (i, data)
		return self.buffer.get(False)[1]

	#
	# Función auxiliar que informa del tamaño del buffer de recepción.
	# Salida:
	#	Tamaño del buffer de recepción
	#
	def _bufferLen(self):
		return self.buffer.qsize()

	#
	# Función que lee un elemento del buffer de recepción mediante una llamada a _bufferPop.
	# Entrada:
	#	- timeout: segundos a esperar como máximo.
	# Salida:
	#	Elemento leído si lo había antes de pasar el timeout o excepción BlockingIOError.
	#
	def rcv(self, timeout=5):
		try:
			# Devuelve una tupla (i, data)
			return self.buffer.get(True, timeout)[1]
		except queue.Empty as e:
			raise BlockingIOError('Timeout passed.')

# Clase que implementa una conexion simultánea de audio y video,
# enviando y recibiendo el audio directamente mediante el uso de PyAudio

######################################################################################
# Clase que gestiona una conexion UDP de audio y vídeo de forma simultánea.
# A nivel de vídeo, es exactamente igual a usar una VideConnection, a nivel de 
# audio, la propia clase inicializa los hilos y streams de PyAudio necesarios
# para reproducir y enviar el audio independientemente de la conexión de vídeo,
# por tanto, no hay sincronización.
#
# Objetos:
#	- orIP: ip origen de la conexión (ip en la que recibimos)
#	- dstIP: ip destino de la conexión
#	- orVideoPort: puerto origen de la conexión de vídeo (puerto en el que recibimos)
#	- dstVideoPort: puerto destino de la conexión de vídeo
#	- orAudioPort: puerto origen de la conexión de audio(puerto en el que recibimos)
#	- dstAudioPort: puerto destino de la conexión de audio.
#	- dstUser: usuario al que corresponde la conexión destino.
# 	- logger: logger usado para almacenar información sobre la ejecución y 
# 		posibles errores de la conexión
#	- maxTimeout: tiempo de timeout para la conexión. Puede tardar hasta
#		maxTimeout al cerrarse.
#	- audioChunks: chunk usado por la conexión de audio.
#	- audioChannels: número de canales usados por la conexión de audio.
#	- threshold: threshold usado para detectar silencio.
#	- pausedEvent: evento que indica si la conexion está pausada (cleared) o no (setted)
#	- closedEvent: evento que indica si la conexión está cerrada o no
#	- videoConnection: VideoConnection usada para transmitir el vídeo.
#	- audioConnection: AudioConnection usada para transmitir el audio.
#	- inputAudioStream: Stream PyAudio usado para grabar el audio a enviar.
#	- outputAudioStream: Stream PyAudio usado para reproducir el audio recibido.
#
#####################################################################################
class VideoAudioCallConnection(UDPConnection):

	#
	# Método instanciador de la clase
	# Objetos:
	#	- orIP: ip origen de la conexión (ip en la que recibimos)
	#	- dstIP: ip destino de la conexión
	#	- orVideoPort: puerto origen de la conexión de vídeo (puerto en el que recibimos)
	#	- dstVideoPort: puerto destino de la conexión de vídeo
	#	- orAudioPort: puerto origen de la conexión de audio(puerto en el que recibimos)
	#	- dstAudioPort: puerto destino de la conexión de audio.
	#	- dstUser: usuario al que corresponde la conexión destino.
	# 	- logger: logger usado para almacenar información sobre la ejecución y 
	# 		posibles errores de la conexión
	#	- maxTimeout: tiempo de timeout para la conexión. Puede tardar hasta
	#		maxTimeout al cerrarse.
	#	- audioChunks: chunk usado por la conexión de audio.
	#	- audioChannels: número de canales usados por la conexión de audio.
	#	- threshold: threshold usado para detectar silencio.
	#
	def __init__(self, orIP, dstIp, orVideoPort, dstVideoPort, orAudioPort, dstAudioPort, dstUser, logger, maxTimeout = 2, audioChunks = 1024, audioChannels = 1, threshold = 0.6):
		self.orIP = orIP
		self.dstIp = dstIp
		self.orVideoPort = orVideoPort
		self.dstVideoPort = dstVideoPort
		self.orAudioPort = orAudioPort
		self.dstAudioPort = dstAudioPort
		self.dstUser = dstUser
		self.logger = logger
		self.maxTimeout = maxTimeout
		self.threshold = threshold
		self.audioChunks = audioChunks
		self.audioChannels = audioChannels

		self.closedEvent = Event()
		self.pausedEvent = Event()

		self.videoConnection = VideoConnection(orIP, dstIp, orVideoPort, dstVideoPort, dstUser, logger, maxTimeout = 2)
		self.audioConnection = AudioConnection(orIP, dstIp, orAudioPort, dstAudioPort, dstUser, audioChunks, audioChannels, logger, maxTimeout = 2)
		self.inputAudioStream = None
		self.outputAudioStream = None

		self.logger.debug('Conexion de video y audio. Recibo video en: {}:{}. Envio video a {}:{}. Recibo audio en: {}:{}. Envio audio a {}:{}.'.format(orIP, orVideoPort, dstIp, dstVideoPort, orIP, orAudioPort, dstIp, dstAudioPort))

	#
	# Método que inicializa la conexión, iniciando las conexiones de audio y vídeo
	# y los dos hilos encargados de grabar y reproducir audio.
	# Salida:
	# 	False si ha habido algún problema, True en caso contrario.
	#
	def start(self):
		# Evento que indica que la conexion debe estar cerrada
		# Usado para detener los hilos que envian/reciben audio
		self.closedEvent.clear()
		# Inicializamos para que no se detengan los hilos que envian/reciben audio
		self.pausedEvent.set()

		if not self.videoConnection.start():
			return False

		if not self.audioConnection.start():
			self.videoConnection.quit()
			return False

		try :
			import pyaudio
			import wave
		except ImportError as e: 
			self.logger.exception('VideoAudioCallConnection - Error al importar PyAudio')
			return False

		FORMAT = pyaudio.paInt16
		RATE = 48000

		p = pyaudio.PyAudio()
		self.inputAudioStream = p.open(format=FORMAT,
				channels=self.audioChannels,
				rate=RATE,
				input=True,
				frames_per_buffer=self.audioChunks)

		self.outputAudioStream = p.open(format=FORMAT,
				channels=self.audioChannels,
				rate=RATE,
				output=True,
				frames_per_buffer=self.audioChunks)
		
		T = Thread(target=self.sendAudio)
		T.start()

		T = Thread(target=self.rcvAudio)
		T.start()

		return True

	#
	# Funcion que calcula la media cuadratica de un frame de audio para determinar
	# si se puede considerar o no silencio.
	# Salida:
	#	Float con la media cuadrática del frame de audio
	#
	def rms(self, frame):
		SHORT_NORMALIZE = (1.0/32768.0)
		count = len(frame) / 2
		format = "%dh" % (count)
		shorts = struct.unpack(format, frame)

		sum_squares = 0.0
		for sample in shorts:
			n = sample * SHORT_NORMALIZE
			sum_squares += n * n
			rms = math.pow(sum_squares / count, 0.5)
			return rms * 1000

	#
	# Funcion encargada de grabar y enviar el audio por la conexión mientras no esté cerrada, 
	# solo si no se considera silencio.
	# Si se pausa la conexión, se detiene el envío de audio.
	#
	def sendAudio(self):
		i = 0   
		while not self.isClosed():
			# Aseguramos que la conexion no esta parada
			self.pausedEvent.wait()

			data = '{}#'.format(i)
			audio = self.inputAudioStream.read(self.audioChunks)
			if self.rms(audio) > self.threshold:
				self.audioConnection.send(data.encode()+audio)
			#print('Enviado '+str(packet))
			i += 1

	#
	# Funcion encargada de recibir y reproducir el audio mientras la conexión no esté cerrada, .
	# Si se pausa la conexión, se detiene la reproducción de audio.
	#
	def rcvAudio(self):
		silence = chr(0)*self.audioChunks*self.audioChannels*2 
		while not self.isClosed():
			# Aseguramos que la conexion no esta parada
			self.pausedEvent.wait()

			try:
				audio = self.audioConnection.rcv(timeout=0)
				self.outputAudioStream.write(audio['audio'], self.audioChunks)
			except Exception as e:
				self.outputAudioStream.write(silence, self.audioChunks)
	#
	# Método que pausa la conexión
	#
	def pause(self):
		self.pausedEvent.clear()
		self.videoConnection.pause()
		self.audioConnection.pause()

	#
	# Método que reanuda la conexión
	#
	def resume(self):
		self.pausedEvent.set()
		self.videoConnection.resume()
		self.audioConnection.resume()

	#
	# Método que cierra la conexión. Puede tardar hasta maxTimeout*3 en acabar.
	#
	def quit(self):
		self.pausedEvent.clear()
		self.closedEvent.set()
		# El hilo de recibir puede tardar hasta self.maxTimeout en acabar
		time.sleep(self.maxTimeout)

		self.videoConnection.quit()
		self.audioConnection.quit()
		return True

	#
	# Método que informa sobre si la conexión está o no cerrada.
	# Salida:
	#	True si la conexión está cerrada, False en caso contrario
	#
	def isClosed(self):
		return self.closedEvent.is_set()

	#
	# Método que informa sobre si la conexión está o no pausada.
	# Salida:
	#	True si la conexión está pausada, False en caso contrario
	#
	def isPaused(self):
		return not self.pausedEvent.is_set()

	#
	# Método que informa sobre si la conexión está o no funcionando.
	# La conexion esta funcionando si no esta cerrada ni parada.
	# Salida:
	#	True si la conexión está funcionando, False en caso contrario
	#
	def isRunning(self):
		return self.pausedEvent.is_set() and not self.closedEvent.is_set()

	#
	# Función usada para enviar datos por la conexión de vídeo.
	# Entrada:
	#	- data: array de bytes a enviar por la red
	#
	def send(self, data):
		self.videoConnection.send(data)

	#
	# Funcion usada para leer datos recibidos a traves de la conexion de video.
	# Entrada:
	#	- timeout: segundos a esperar como máximo.
	# Salida:
	#	Elemento leído si lo había antes de pasar el timeout o excepción BlockingIOError.
	#
	def rcv(self, timeout=5):
		try:
			return self.videoConnection.rcv(timeout)
		except BlockingIOError as e:
			raise BlockingIOError('Timeout passed.')
		