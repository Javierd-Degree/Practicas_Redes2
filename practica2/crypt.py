#import pycrypto
from Crypto import Random
from Crypto.Hash import SHA256
from Crypto.Cipher import AES
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Util.Padding import pad, unpad
import identityGestion as ig
import os
import utils
import time
import sys

# Funcion que lee e importa la clave privada del usuario a partir del fichero que la contiene.
# Return: clave privada importada.
#
def getPrivateKey():
	priv_key = "./.files/key.priv"
	key = RSA.importKey(open(priv_key).read())
	return key


# Funcion que genera un par de claves pública y privada llamando a create_RSA_keys y solicita
# la creación de un usuario llamando a generateUser.
# Parámetros:
#	name: nombre del usuario.
#	email: correo del usuario.
# Return: resultado de la petición a la API.
#
def userRegister(name, email):

    publicKey = create_RSA_keys('./.files/key')
    return ig.generateUser(name, email, publicKey)


# Funcion que encripta un fichero destinado a un usuario determinado.
# Parámetros:
#	file: dirección del fichero que se quiere encriptar.
#	dest_id: id en SecureBox del detinatario del fichero.
# Return: dirección del fichero encriptado.
#
def encriptar (file, dest_id):

	outputF = './encriptado/' + file.split('/')[-1].split('.unchecked')[0]
	read_s = 16

	key = str(time.time()) + dest_id
	key = key.encode(encoding = 'UTF-8')
	dest_key = RSA.importKey(ig.userGetPublickey(dest_id))
	key = SHA256.new(key).digest()

	print('Cifrando fichero')

	tam_iv = AES.block_size
	iv = Random.new().read(tam_iv)
	cipher = PKCS1_OAEP.new(dest_key)
	encrypted_key = cipher.encrypt(key)

	

	aes = AES.new(key, AES.MODE_CBC, iv)

	with open(file, 'rb') as inp:
		with open(outputF, 'wb') as outp:

			outp.write(iv)

			outp.write(encrypted_key)

			buf = inp.read(read_s)

			while len(buf) != 0:
				if(len(buf) < 16):
					buf = pad(buf, 16)
				outp.write(aes.encrypt(buf))
				buf = inp.read(read_s)
	print('OK')
	return outputF


# Función que descifra un fichero encriptado.
# Parámetros:
#	file: dirección del fichero encriptado.
# Return: dirección del fichero descifrado.
#
def desencriptar(file):

	print('Descifrando fichero')

	outputF = './downloads/' + file.split('/')[-1] + '.unchecked'
	read_s = 16

	with open(file, 'rb') as inp:

		iv = inp.read(AES.block_size)

		priv_key = getPrivateKey()
		cipher = PKCS1_OAEP.new(priv_key)
		key = inp.read(256)
		key = cipher.decrypt(key)

		aes = AES.new(key, AES.MODE_CBC, iv)

		with open(outputF, 'wb') as outp:

			buf = inp.read(read_s)

			while len(buf) != 0:
				aux = inp.read(read_s)
				if len(aux) == 0:
					outp.write(unpad(aes.decrypt(buf), 16))
				else:
					outp.write(aes.decrypt(buf))
				buf = aux

	os.remove(file)
	print('OK')
	return outputF


# Funcion que genera el resumen hash de un fichero con SHA256.
# Parámetros:
#	file: fichero del que se quiere hacer el hash.
# Return: resumen hash del fichero.
#
def create_hash(file):

	read_s = 1024
	hash_code = SHA256.new()

	with open(file, 'rb') as inp:
		buf = inp.read(read_s)

		while len(buf) != 0:
			hash_code.update(buf)
			buf = inp.read(read_s)

	return hash_code


# Funcion que genera un par de claves pública y privada y guarda la prvada en la dirección dada.
# Parámetros:
#	file: dirección para guardar la clave privada.
# Return: clave pública
#
def create_RSA_keys(file):

	print('Generando un par de claves RSA')

	private_keyF = file + '.priv'

	key = RSA.generate(2048)
	private_key = key.exportKey()
	public_key = key.publickey().exportKey()

	with open(private_keyF, 'wb') as priv:
		priv.write(private_key)

	print('OK')

	return public_key.decode()


# Funcion que firma un fichero con la clave privada del usuario.
# Parámetros:
#	file: dirección del fichero que se quiere firmar.
# Return: dirección del fichero firmado.
#
def firmar(file):
	read_s = 1024
	key = getPrivateKey()
	hash_code = create_hash(file)
	outputF = file + '.unchecked'

	print('Firmando fichero')

	try:
		signature = PKCS1_v1_5.new(key).sign(hash_code)

	except:
		print('Error: se debe crear un usuario primero para recibir una clave privada.')
		os.remove(outputF)
		sys.exit(0)

	with open(outputF, 'wb') as outp:
		outp.write(signature)

		with open(file, 'rb') as inp:
			buf = inp.read(read_s)
			while len(buf) != 0:
				outp.write(buf)
				buf = inp.read(read_s)

	print('OK')

	return outputF


# Funcion que verifica la firma digital de un fichero determinado.
# Parámetros:
#	file: dirección del fichero del que se quiere verificar la firma.
#	source_id: id en SecureBox del usuario emisor del fichero.
# Return: True si la firma es correcta o False en caso contrario.
#
def check_signature(file, source_id):

	public_key = ig.userGetPublickey(source_id)
	print('Verificando firma')

	with open(file, 'rb') as inp:
		signature = inp.read(256)
		filetext = inp.read()

	dest = './downloads/' + file.split('/')[-1].split('.unchecked')[0]
	os.remove(file)
	with open(dest, 'w') as outp:
		outp.write(filetext.decode())

	hash_code = create_hash(dest)

	key = RSA.importKey(public_key)

	if PKCS1_v1_5.new(key).verify(hash_code, signature):
		return True
	else:
		os.remove(dest)
		return False

# Funcion que firma y encripta un fichero llamando a las funciones "firmar" y "encriptar".
# Parámetros:
#	file: dirección del fichero que se quiere encriptar y firmar.
#	dest_id: id en SecureBox del destinatario del mensaje.
# Return: dirección del fichero encriptado y firmado.
#
def cifrar_firmar(file, dest_id):

	file = firmar(file)
	file2 = encriptar(file, dest_id)
	os.remove(file)
	return file2
