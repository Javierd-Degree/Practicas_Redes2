# Practica 2

Javier Delgado del Cerro y Javier López Cano



### Introducción

En esta práctica hemos implementado un sistema de almacenamiento de ficheros en red seguro en Python, empleando para ello la API que se nos ha proporcionado. Para asegurarnos de la seguridad y fiabilidad del sistema de ficheros, como se nos exigía, todos los ficheros que se suben al sistema son correctamente firmados por el emisor y encriptados con una clave simétrica que se concatena al mensaje cifrada con la clave pública del receptos. De este modo nos aseguramos de que tan solo el receptor deseado puede descifrar el mensaje, así como de la autenticidad del emisor y de la integridad del mensaje enviado.

Además hemos añadido un sistema de encriptado, desencriptado y gestión de firmas independiente del sistema de ficheros en red, es decir, que se puede cifrar y firmar ficheros (o descifrarlos y comprobar la firma) sin necesidad de subirlos al sistema en red.

### Desarrollo técnico

La meta a alcanzar al desarrollar este sistema ha sido la de conseguir que este sea totalmente fiable y compatible, es decir, que el encriptado y firma de ficheros funcionasen correctamente en todos los casos, y que el sistema pudiese descargar, descifrar y comprobar la firma de ficheros subidos por otros usuarios sin ningún tipo de problemas, así como que los demás usuarios pudiesen descargar ficheros subidos por nosotros con igual facilidad.

Para alcanzar estos objetivos hemos decidido emplear la librería `pycrypto` para Python, ya que esta contiene numerosos métodos ya implementados para el encriptado, desencriptado y firma de ficheros que funcionan ya de forma adecuada. Por el mismo motivo hemos decidido instalar `pycryptodome` para poder emplear los métodos de padding disponibles en la sub-librería `Crypto.Util.Padding` de `pycrypto` pues proporciona un método para asegurar que los ficheros pueden encriptarse correctamente convirtiéndolos en múltiplos de 16 bits si no lo son, pero a la vez proporciona una gran compatibilidad para que esto pueda ser soportado también por otros usuarios; además, el método `unpad` de esta librería permite que podamos "deshacer" el padding realizado tras desencriptar un fichero para asegurarnos de que el fichero se encuentra en exactamente el mismo estado que antes de subirlo al sistema y poder comprobar la firma digital de forma correcta. 

Por último, para asegurar que la ejecución se realizase exactamente del modo pedido, decidimos utilizar la librería `argparse` de Python para parsear los argumentos de entrada y asegurarnos de que estos se lean en el formato pedido y ejecuten las instrucciones necesarias correctamente.

#### Gestión de archivos

Para una mayor comodidad del usuario y una mejor organización de los archivos del programa, hemos decidido crear diversos directorios para organizar los distintos ficheros generados y necesarios para el programa. De este modo disponemos de la carpeta "Encriptado" donde se almacenarán los archivos encriptados que genere el programa, la carpeta "downloads", donde se almacenan los archivos descargados  de SecureBox una vez se han desencriptado y se ha comprobado su firma digital, y también la carpeta "ficheros_prueba" donde se dispone de algunos ficheros para probar el funcionamiento de SecureBox.

Para asegurarnos de que el programa puede emplear siempre estos directorios aunque no estén aún creados, el programa comprueba si los directorios existen con `os.stat()`, y, en caso de que no existan, los genera con `os.mkdir()` evitando así la posibilidad de que se de ningún error por directorio inexistente.

Esta gestión de archivos permite una mejor localización de los ficheros generados por el programa, a la vez que mantiene limpio el directorio principal del programa en sí, y facilita el uso de los ficheros por el propio programa, al saber en todo momento donde está el fichero al que se debe acceder.

#### Parseo de argumentos

En el archivo `read.py` es donde está implementada la función principal del programa `leer()`, que emplea la librería `argparse` para parsear los argumentos de entrada del programa. Para ello generamos las distintas instrucciones que se pueden ejecutar (`--upload, --download, --encrypt, ...`) como argumentos mediante la función `argparse.ArgumentParser.addArgument()`, y, para cada uno de ellos definimos los parámetros que deben recibir y establecemos una frase de ayuda y, en los casos que sea posible, hemos generado un "metavar" para ilustrar el "nombre" de los parámetros al ejecutar la función de ayuda (`-h`).

Tras definir cuales son los posibles parámetros, parseamos la entrada con la función `parse_args()` que genera un array por cada uno de los argumentos generados con `addArgument()`, cuyos elementos son los parámetros que se han pasado a los argumentos, para, empleando esos, llevar a cabo la acción requerida.

Tras esto comprobamos qué argumentos se han introducido, y si todos los parámetros que son requeridos para llevar a cabo las acciones correspondientes al argumento, y, si todo ha sido introducido de forma correcta, llevamos a cabo la acción necesaria (descargar de secureBox, subir un fichero, crear un usuario...).

Las distintas acciones posibles que se han implementado son:

- Crear usuarios nuevos.
- Buscar usuarios mediante un nombre o cadena de caracteres que contenga el usuario.
- Eliminar un usuario.
- Subir ficheros a SecureBox (Encriptados y firmados).
- Descargar ficheros de SecureBox (Descifrándolos y comprobando la firma).
- Ver los archivos subidos por el usuario propio.
- Borrar ficheros que estén subidos a SecureBox.
- Firmar ficheros (Sin subirlos).
- Encriptar ficheros (Sin subirlos).
- Descifrar ficheros (En el propio ordenador, sin descargarlos).
- Comprobar la firma de ficheros (En el propio ordenador, sin descargarlos).
- Firmar y encriptar ficheros (En una misma instrucción).
- Descifrar y comprobar la firma de ficheros (En una misma instrucción).

#### Crear usuarios nuevos

Generamos un nuevo usuario en SecureBox cuando se emplea el argumento `--create_id`, para realizar eta acción se deben pasar al menos 2 parámetros que son el nombre y el correo electrónico, y se puede añadir un tercero (alias) opcionalmente.

Al generar un nuevo usuario en primer lugar generamos su par de claves pública u privada mediante la función `create_RSA_keys()` implementada en el archivo `crypt.py`. Esta función genera una clave digital de 2048 bits mediante la función `generate()` de módulo RSA de `pycrypto`, tras lo cual la exporta como privada `exportKey()` obteniendo la clave privada, y como pública `publicKey().exportKey()` obteniendo la clave pública. La clave privada se almacena en la carpeta privada `.files` situada en el directorio del programa en el ordenador del usuario (que es el único que puede acceder a ella), y la pública se almacena en la Api de SecureBox junto con el nombre y el correo del usuario que se genera. Esto último lo realiza la función `generateUser()` del archivo `identityGestion.py` , que realiza una petición a la API mediante `genericRequest()` con la función `/users/register` que almacena los datos del usuario en la API generando además un ID para este.

#### Buscar usuarios

La acción de buscar usuarios se utiliza junto con el argumento `--search_id` donde se indica la string a usar para buscar al usuario.

Para esto, se utiliza la función `userSearch` de `identityGestion.py` que se encarga básicamente de hacer una petición a la API Rest mediante `genericRequest()`. Una vez obtenido el resultado, parseamos el Json recibido y formamos un string con todos los usuarios devueltos por el servidor.

#### Eliminar usuarios

La acción de eliminar un usuario se realiza cunado se introduce el argumento `--delete_id` , y esta acción requiere que se le pase un parámetro indicando el ID del usuario que se desea eliminar.

Para realizar esta acción, la función `userDelete()` de `identityGestion.py` realiza una petición a la API mediante `genericRequest()` con la función `/users/delete` pasándole como parámetro el ID del usuario a eliminar. De este modo la API elimina los datos del usuario eliminado.

Al implementar esta funcionalidad nos planteamos si deberíamos o no eliminar el archivo que contiene la clave privada del usuario. Sin embargo, decidimos no hacerlo puesto que al crear un nuevo usuario este fichero se sobrescribe, luego eliminarlo es innecesario.

#### Firmar ficheros

Para firmar un fichero se debe introducir el argumento `--sign`, o bien `--sign_files` si se desea firmar varios archivos en una misma instrucción. En el primer caso se debe introducir por parámetro la dirección del fichero a firmar, y en el segundo varios parámetros (cada uno con la dirección de uno de los ficheros que se quieren firmar). También se firman ficheros antes de subir ficheros a SecureBox, pues deben subirse firmados y cifrados.

La firma de un fichero se realiza mediante la función `firmar()` implementada en el archivo `crypt.py`. Esta función genera un resumen hash (SHA256) del fichero que se quiere firmar con la función `create_hash()` implementada en el mismo archivo. Tras generar este resumen hash lee la clave privada del usuario del fichero `key.priv` situado en la carpeta `.files`, y genera la firma de este fichero mediante la función `sign()` del módulo `PKCS1_v1_5`, que firma el hash del fichero con la clave privada. Esta firma se concatena al inicio del fichero, generando así el fichero firmado, que se imprime en un archivo `.unchecked`.



#### Comprobar firmas

La verificación de las firmas digitales de ficheros se realiza necesariamente siempre que se descarga un fichero de SecureBox  tanto para garantizar la integridad del fichero como para autentificar al usuario emisor del fichero. Sin embargo también puede comprobarse la firma de uno o varios ficheros manualmente introduciendo el argumento `--check_sign` (para 1 fichero) o `--check_sign_files` pasándoles las direcciones de los ficheros a verificar e indicando el ID del usuario emisor con `--source_id`.

La función `check_signature()` implementada en `crypt.py` verifica la firma de los ficheros. Para ello en primer lugar lee los 256 primeros bits del fichero pues son los correspondientes a la fira, tras lo cual lee la parte restante del fichero y la imprime en el fichero destino en la carpeta `downloads`. Una vez obtenida la firma y generado el fichero final, genera un resumen hash (SHA256) del fichero final (que es  idéntico al que se firmó antes de encriptarlo, y, por tanto, los resúmenes hash serán iguales); se obtiene la clave pública del emisor mediante una petición a la API con `genericRequest()` pasándole la ID del emisor, y, una vez la tenemos, verificamos la firma con la función `verify()` del módulo `PKCS1_v1_5` de `pycrypto`, a la que le pasamos como argumentos el hash del fichero y la clave pública del emisor.

Si la función `verify()` devuelve `true`, la firma habrá sido verificada correctamente, y en caso contrario, implicará que o bien el archivo ha sido modificado, o bien el emisor no es el especificado, por lo que eliminamos el fichero resultante con `os.remove()`.

#### Encriptar ficheros

Al igual que la firma de ficheros, el encriptado de ficheros se realiza antes de subirlos a SecureBox, y también sin necesidad de subir ficheros, introduciendo el argumento `--encrypt` que recibe como parámetro la dirección del fichero a encriptar, o con el argumento `--encrypt_files` en caso de que se quieran encriptar varios. En ambos casos se debe especificar el ID del usuario receptor del fichero pues se debe emplear su clave pública para cifrar la clave simétrica, esta ID se especifica con el argumento `--dest_id.`

Para encriptar un fichero empleamos la función `encriptar()` implementada en `crypt.py`. Esta función genera una clave simétrica para cifrar el archivo. Para generar esta clave y asegurarnos de que sea  aleatoria, cogemos la hora y concatenamos el `dest_id`,  tras esto pasamos la string resultante a bytes con `encode()` y generamos un hash (SHA256) para asegurarnos de que la clave tiene 256 bits.

Esta clave tendremos que enviarla también al receptor para que este pueda descifrar el fichero, para ello debemos cifrarla con un algoritmo RSA empleando la clave pública del receptor. Obtenemos la clave pública del receptor mediante una `genericRequest()` a la api (empleando su ID), y generamos el cifrador RSA con `PKCS1_0AEP.new(clave-pública)` de la librería `pycrypto`, y ciframos la clave con la función `encrypt()` del cifrador.

Para poder cifrar el fichero, además de la clave necesitamos un vector de inicialización que generamos aleatoriamente con `Random.new().read(tam)` del módulo `Random` de `pycrypto`, donde `tam` es el tamaño de bloque del algoritmo `AES` que es el que emplearemos para el cifrado.

Una vez tenemos tanto la clave como el vector de inicialización, generamos el cifrador AES con `AES.new(clave-sim, AES.MODE_CBC, vector)`, función del módulo `AES` de `pycrypto`. Tras generar el cifrador leemos el fichero y lo ciframos, asegurándonos de que el fichero es múltiplo de 16 bytes (para lo que utilizamos la función `pad()`), e imprimimos en el fichero resultado en primer lugar  el vector de inicialización, seguido de la clave simétrica cifrada con `RSA`, y por último el fichero cifrado.

Por último guardamos el archivo resultante en la carpeta `Encriptado`, como ya hemos explicado en el apartado de gestión de archivos.

#### Descifrar ficheros

Del mismo modo que al subir ficheros a SecureBox los encriptamos, al descargarlos debemos descifrarlos para permitir al receptor poder leerlos. Además de en este caso particular, también se descifrarán ficheros al introducir los argumentos `--decrypt` (para 1 solo fichero), o `--decrypt_files` (para varios ficheros), que reciben como parámetro las direcciones de los ficheros a descifrar.

Los ficheros son descifrados mediante la función `desencriptar()` del archivo `crypt.py`.

Para poder descifrar correctamente un fichero se debe en primer lugar generar el mismo cifrador AES que se ha empleado para su encriptado, por tanto, será necesario obtener la clave simétrica y el vector de inicialización. El vector de inicialización se obtiene simplemente leyendo los primeros `AES.block_size` bytes del fichero a desencriptar, donde `AES.block_size` indica el tamaño de cada bloque empleado por el algoritmo AES, y, este es el tamaño del vector de inicialización. Tras esto, obtenemos la clave simétrica leyendo los siguientes 256 bits, sin embargo esta está cifrada con RSA, y, para poder descifrarla necesitamos generar el cifrador RSA con la clave privada del usuario (que es el receptor), mediante `PKCS1_0AEP.new(clave_priv)`, y desciframos la clave con el método `decrypt()` de este cifrador.

Ya tenemos todos los datos necesarios para generar el cifrador AES, y lo generamos del mismo modo que la encriptar. Leemos entonces el resto del fichero pro bloques y lo vamos descifrando con el método `decrypt()` del cifrador, imprimiendo los bloques resultantes en el fichero de salida (en la carpeta `downloads`), y, en el último bloque aplicamos `unpad()` para asegurarnos de que el fichero resultado es totalmente idéntico al fichero inicial antes de ser encriptado, pues de lo contrario no se podría comprobar la firma correctamente.

#### Firmar y encriptar, y descifrar y verificar

Se ha implementado también la opción de firmar y encriptar ficheros en una misma instrucción, o análogamente, descifrarlos y verificarlos en una sola instrucción. Para llevar a cabo estas acciones se emplean los argumentos `--enc_sign` y `--decrypt_check` (para 1 fichero) o bien `--enc_sign_files` y               `--decrypt_check_files` (para varios ficheros). Para estas funcionalidades se debe pasar por parámetro la dirección o direcciones de los ficheros que se quieren firmar y encriptar o descifrar y verificar, y, en el caso de encriptar y firmar se debe especificar el ID del receptor con `--dest_id`, y en el caso opuesto el ID del emisor con `--source_id`.

Para llevar a cabo estas acciones simplemente se llama a las funciones de las "sub-acciones" correspondientes.

Para encriptar y firmar:

1- Se firma

2- Se encripta

Para descifrar y verificar:

1- Se descifra

2- Se verifica la firma

#### Subir ficheros a SecureBox

Para subir ficheros a SecureBox se emplea el argumento `--upload` al que se le pasa la dirección del fichero a subir, también se pueden subir varios archivos con `--upload_files`. En ambos casos debe especificarse el ID del destinatario con `--dest_id`.

Cuando se lleva a cabo la acción de subir ficheros, el programa en primer lugar los firma y luego los encripta, del mismo modo que se ha explicado en los apartados de "Firmar ficheros" y "Encriptar ficheros". Tras esto, se solicita la subida del fichero a SecureBox con la función `uploadFile` del archivo `filesGestion.py`, que realiza una petición a la API con `genericRequest()` pasándole la función `/files/upload` de modo que la api almacena el fichero y genera un Id para él. Si se han subido más de los 21 ficheros permitidos por usuario (se obtiene el error 401) se muestra un mensaje indicando que se deben borrar algunos ficheros, de este modo el usuario puede tomar las medidas necesarias para poder subir el fichero que desea subir.

#### Ver archivos subidos

Para que un usuario pueda consultar todos los archivos subidos al servidor SecureBox mediante el comando `--list_files` empleamos la función `fileList` de `filesGestion.py` que se encarga básicamente de hacer una petición HTTP al servidor REST para, a partir de la respuesta, formatear un string con todos los archivos devueltos por el servidor.

#### Descargar archivos

Para descargar ficheros de SecureBox empleamos el argumento `--download` al que se le pasa el ID del fichero que se quiere descargar, también se pueden descargar varios archivos con `--download_files`. En ambos casos debe especificarse el ID del emisor con `--source_id`.

Cuando se descarga un fichero, en primer lugar se llama a la función `fileDownload()` de `filesGestion.py`, que obtiene el fichero cifrado y firmado de la api mediante una `genericequiest()` con la función `/files/download` pasándole el ID del fichero a descargar, este fichero se guarda en la carpeta `downloads` con el nombre que tiene en la API. Tras esto se descifra el fichero, y se verifica la firma del mismo modo que se ha explicado en los apartados de "Descifrar ficheros" y "Comprobar firmas". De este modo acabamos obteniendo el fichero verificado y descifrado para que el receptor pueda acceder a él.

#### Delete files

Por último, el programa permite eliminar ficheros que estén subidos a la API de SecureBox mediante los argumentos `--delete_file` (1 fichero) y `--delete_files` (varios ficheros), a los que hay que pasarles como parámetros los IDs de los ficheros que se quieren eliminar.

Para esta última acción posible, se llama a la función `fileDelete()` de `filesGestion.py`, que simplemente realiza una `genericRequest()` a la API con la función `/files/delete` pasándole el ID del fichero que se quiere eliminar, de modo que la API elimina el fichero de su almacenamiento.



### Funcionalidad y Manual de usuario

Para esta práctica hemos implementado toda la funcionalidad pedida para el programa, pero además hemos añadido alguna funcionalidad, extra, como es el caso de subir, bajar, o eliminar varios archivos al mismo tiempo, o el hecho de poder descifrar y comprobar la firma digital de los fichero sin necesidad de que se descarguen de la API.

Para probar el correcto funcionamiento de todas las posibles acciones implementadas proporcionamos un breve manual de ejecución del programa.

Para ejecutar el programa se debe ejecutar el archivo `read.py` con `python3` pasándole los argumentos correspondientes a las acciones que se quieren realizar. Estos argumentos son:



#### Funcionalidad básica

| Argumento     | Parámetros                      | Funcionalidad                                                |
| ------------- | ------------------------------- | ------------------------------------------------------------ |
| --create_id   | nombre, email, (opcional) alias | Crea un usuario en SecureBox generando un ID para identificarlo y un par de claves pública y privada. |
| --search_id   | string                          | Busca en SecureBox todos los usuarios que contengan la "string" en alguno de los datos almacenados (nombre o email). |
| --delete_id   | userID                          | Elimina el usuario con la ID especificada de SecureBox.      |
| --upload      | filePath                        | Sube el fichero especificado a SecureBox firmado y encriptado. Para llevarlo a cabo se debe especificar el ID del receptor con --dest_id. |
| --download    | fileID                          | Descarga el fichero con el ID especificado de SecureBox, lo descifra y verifica la firma. Para poder llevarlo a cabo debe especificarse el ID del emisor con --source_id |
| --list_files  |                                 | Muestra una lista con todos los ficheros almacenados en la API que ha subido el usuario. |
| --delete_file | fileID                          | Elimina de SecureBox el fichero con la ID especificada.      |
| --encrypt     | filePath                        | Encripta el fichero especificado. Se debe especificar el ID del receptor con --dest_id. |
| --sign        | filePath                        | Firma el fichero especificado con la clave privada del usuario. |
| --enc_sign    | filePath                        | Encripta y firma el fichero especificado. Se debe indicar el ID del receptor con --dest_id. |
| --source_id   | userID                          | Indica el ID del usuario emisor.                             |
| --dest_id     | userID                          | Indica el ID del usuario receptor.                           |
| -h            |                                 | Ayuda.                                                       |



#### Funcionalidad extra

| Argumento             | Parámetros           | Funcionalidad                                                |
| --------------------- | -------------------- | ------------------------------------------------------------ |
| --upload_files        | path1, path2,...     | Sube varios ficheros a SecureBox firmados y encriptados para un mismo receptor. Para llevarlo a cabo se debe especificar el ID del receptor con --dest_id. |
| --download_files      | fileID1, fileID2,... | Descarga los ficheros de un mismo emisor con IDs especificados de SecureBox, los descifra y verifica las firmas. Para poder llevarlo a cabo debe especificarse el ID del emisor con --source_id |
| --delete_files        | fileID1, fileID2,... | Elimina de SecureBox los ficheros con las IDs especificadas. |
| --encrypt_files       | path1, path2,...     | Encripta los ficheros especificados para un mismo receptor. Se debe especificar el ID del receptor con --dest_id. |
| --decrypt             | filePath             | Descifra el fichero especificado.                            |
| --decrypt_files       | path1, path2,...     | Descifra los ficheros especificados.                         |
| --sign_files          | path1, path2,...     | Firma los ficheros especificados con la clave privada del usuario. |
| --check_sign          | filePath             | Verifica la firma digital del fichero especificado. Se debe indicar el ID del emisor con --source_id. |
| --check_sign_files    | path1, path2,...     | Verifica la firma digital de los ficheros especificados de un mismo emisor. Se debe indicar el ID del emisor con --source_id. |
| --enc_sign_files      | path1, path2,...     | Encripta y firma los ficheros especificados para un mismo receptor. Se debe indicar el ID del receptor con --dest_id. |
| --decrypt_check       | filePath             | Descifra y verifica la firma del fichero especificado. Se debe indicar el ID del emisor con --source_id. |
| --decrypt_check_files | path1, path2,...     | Descifra y verifica la firma de los ficheros especificados de un mismo emisor. Se debe indicar el ID del emisor con --source_id. |



#### Ejemplos de ejecución

El programa debe ejecutarse desde la carpeta que contiene el archivo principal, que es `read.py`.

Algunos ejemplos de cómo se debe ejecutar el programa son:

```bash
## Crear un usuario.
python3 ./read.py --create_id Pedro pedro.perez@gmail.com
```

```bash
## Subir varios ficheros.
python3 ./read.py --upload_files ./ficheros/fichero1.txt ./ficheros/fichero2.jpg ./ficheros/fichero3.pdf --dest_id e367945
```

```bash
## Descifrar varios ficheros.
python3 ./read.py --decrypt_files ./ficheros/fichero1.enc ./ficheros/fichero2.enc ./ficheros/fichero3.enc
```

```bash
## Mostrar los ficheros subidos.
python3 ./read.py --list_files
```

```bash
## BUscar usuarios que contengan la palabra "pepe".
python3 ./read.py --search_id pepe
```

Las demás acciones se llevan a cabo de forma análoga.

Cabe destacar también que se pueden realizar varias acciones en una misma ejecución:

```bash
## Mostrar los ficheros subidos y los usuarios que contengan la palara "pepe".
python3 ./read.py --list_files --search_id pepe
```



### Conclusiones técnicas

Durante el desarrollo de la práctica nos hemos dado cuenta de lo complicado que es desarrollar plataformas de este tipo, tanto por la complejidad que tiene el encriptado y firma de archivos para garantizar la seguridad de los ficheros, como por las complicaciones que surgen a la hora de mejorar la compatibilidad de la plataforma con los archivos de otros usuarios, que, en este caso eran nuestros compañeros.

Esto último ha sido lo que nos ha resultado más complicado y nos ha dado más problemas ya que, no solo influía el hecho de que varias personas debíamos terminar toda la implementación de forma correcta para poder probar la compatibilidad entre nuestros usuarios, sino que además entran en juego otros factores, como que herramienta utiliza cada uno para llevar a cabo el "padding" y "unpadding" de los ficheros para que sean múltiplos de 16 bytes, puesto que si cada uno empleaba una herramienta diferente para ello, aunque ambas fuesen correctas, podían generar problemas de compatibilizar, pues el "padding" de una de ellas no siempre se podía revertir con el "unpad" de otro. Afortunadamente, conseguimos encontrar la herramienta de "padding" de `pycryptodome` que ofrece una gran compatibilidad que consiguió solucionar muchos de nuestros problemas en este aspecto.

### Conclusiones personales

Esta práctica ha supuesto un gran reto para ambos, sin embargo, consideramos que ha sido una actividad muy beneficiosa que nos ha ayudado mucho en nuestro aprendizaje, especialmente a la hora de encontrar documentación y herramientas útiles para solventar los problemas de nuestra implementación.

También nos ha resultado muy interesante debido a que hemos logrado aprender como se lleva a cabo (a pequeña escala) de forma práctica, la seguridad de los servidores de archivos en la nube mediante la encriptación de archivos y la firma digital. Aunque estamos seguros de que lo que hemos realizado en esta práctica es tan solo la superficie, y que queda muchísimo por aprender e investigar en este aspecto.

En cuanto a aspectos que mejorar en los próximos años nos gustaría proponer que se haga un mayor énfasis en las técnicas de encriptado en sí, quizás requiriendo que se realicen otros tipos de encriptado o encriptado AES en modos que no sean CBC. De este modo se podría profundizar más en el funcionamiento de los distintos algoritmos de encriptación y aprender en qué casos se debe usar cada uno de ellos.