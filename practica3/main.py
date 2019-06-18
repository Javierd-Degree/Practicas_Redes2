from logging.handlers import RotatingFileHandler
from application import Application
from video_client import VideoClient
from control import ControlConnection
import logging
import utils

from user import getUserInfo

#
# Inicializa el logger, la conexión de control, la interfaz y el Application en sí.
# Lanza el Application.
#
if __name__ == '__main__':

	# Iniciamos un logger para obtener informacion ante posibles fallos
	logger = logging.getLogger(utils.NAME)
	logger.setLevel(logging.DEBUG)
	formatter = logging.Formatter(fmt='%(asctime)s %(levelname)-8s %(message)s',
	                                  datefmt='%Y-%m-%d %H:%M:%S')
	handler = RotatingFileHandler(utils.LOG_FILE, maxBytes=256000, backupCount=10)
	handler.setFormatter(formatter)
	handler.setLevel(logging.DEBUG)
	logger.addHandler(handler)

	vc = VideoClient(utils.WIN_SIZE, logger)
	cc = ControlConnection(10, logger)

	app = Application.getInstance(None, vc, cc, logger)
	# Inicializa la aplicación. Es bloqueante
	app.start()

	logging.shutdown()