La aplicación almacena la información sobre el último usuario que se ha loggeado, excepto la contraseña, para no tener que volver a pedir todos los datos de nuevo

https://hackernoon.com/synchronization-primitives-in-python-564f89fee732



Para el Audio:

```
sudo apt install libasound-dev portaudio19-dev libportaudiocpp0
sudo pip3 install pyaudio
```



Necesitamos:
	- Desde la conexión de control poder hacer llamadas a la interfaz, para mostrar que recibimos una llamada, que nos la han rechazado, etc.
	- Desde la interfaz poder hacer llamadas a la conexión de control para iniciar una llamada, colgar, etc.
	- Desde la conexión de control poder inicializar una nueva conexión UDP, y que la interfaz reciba esta nueva conexión UDP.
	- Desde la conexión poder finalizar una conexión UDP.
	- Desde la inerfaz poder enviar y recibir de una conexión UDP para enviar nuestro video y mostrar el del receptor.

Para esto:
	- Pool de conexiones UDP, cada una con un identificador único: el nick del usuario. Podemos pararlas y reanudarlas cuando queramos, eliminarlas o añadirlas al pool.
	- Convertimos la aplicación en un singleton, que tenga la conexión de control, el cliente de vídeo y el pool de UDP.
	- Al iniciar la aplicación iniciamos la conexión de control y el cliente de video en threads distintos. El pool de UDP sin ninguna conexión aún.
	- Es necesario usar semáforos de threads para evitar problemas, tanto en la aplicacion como en el pool de threads
	- Cada uno de los módulos accede a los otros mediante la aplicación, por ser esta Singleton
	- Establecemos en la interfaz las funciones para mostrar notificaciones de llamadas entrantes, etc, todas usando las colas de appJar.
	- Cuando la conexión de control tiene que iniciar una llamada, inicializa la conexión UDP dentro del pool, con el nick del usuario, y avisa a la interfaz de que ha iniciado una nueva conexión para que esta se muestre.

## Protocolo nuevo

Para el protocolo V1, añadimos únicamente llamadas con audio y video, de forma 

Comando CALLING_V1

Objetivo: Señalizar que un nodo quiere establecer una videollamada con audio con otro
Sintaxis: *CALLING_V1 nick srcUDPVideoPort srcUDPAudioPort *, donde srcUDPVideoPort es el puerto UDP en el que el llamante desea recibir el video del llamado, y srcUDPAudioPort donde se desea recibir el audio.
Posibles respuestas/errores:

CALL_ACCEPTED_V1 nick dstUDPVideoPort, donde dstUDPAudioPort es donde el llamado recibirá el video
CALL_DENIED nick 
CALL_BUSY, el llamado está en una llamada y no puede recibir la comunicación. 







==================

Podriamos haber añadido también, con mucha facilidad, llamadas únicamente con audio, pues ya esta implementado ese tipo de conexion, sin embargo preferimos  implementar filtros de video



Videollamadas con voxz muy primitivas, sin sincronización con el vídeo, y usando una simple funcion rms para determinar el silncio. Como no tenemos conocimientos de audio no hemos podido implementarlo correctamente y los valores deberían depender del micrófono, pero no tenemos tiempo para esto.

Filtros simples usando OpenCV





### Introducción

En esta tercera y última práctica de la asignatura Redes de Comunicaciones 2, se pedía el desarrollo de una aplicación de videollamadas basada en el uso de un servidor de descubrimiento para obtener la dirección del usuario receptor, una conexión TCP de control que permitiese recibir llamadas y comandos para controlar la videollamada, y el establecimiento de una conexión UDP para el envío de vídeo entre los dos usuarios. Además, hemos implementado distintos extras que se explicarán a lo largo de la documentación, como son filtros OpenCV y la adición de voz a las llamadas.

### Desarrollo técnico

Para facilitar el desarrollo de proyecto, lo hemos dividido en módulos bastante claros, algunos de ellos interrelacionados, que explicaremos a continuación. Además, han sido necesarios diferentes hilos, sincronizados entre ellos con eventos y semáforos para optimizar el funcionamiento de la aplicación.

#### Identity Gestion y User

Han sido los dos primeros módulos desarrollados, por ser los mas sencillos. El primero, *identityGestion.py* es el encargado de conectar con el servidor de descubrimiento para registrar/loggear al usuario, obtener la lista de usuarios registrados o buscar a un usuario concreto. El segundo, *user.py*, contiene la clase *User*, que describe a un usuario de la aplicación almacenando su nick, ip, puerto, protocolos soportados, etc, de forma que facilita el manejo de los usuarios dentro de la propia aplicación. Este último modulo contiene además dos funciones que permiten **almacenar información del último usuario loggeado, para facilitar los siguientes inicios de sesión**. Así, la aplicación recuerda toda la información del último usuario que la ha utilizado, de forma que al iniciarla ofrece la posibilidad de entrar directamente como dicho usuario introduciendo su contraseña únicamente.

#### Application

Es la clase principal de la aplicación, encargada de almacenar referencias al usuario que está loggeado en la aplicación, la interfaz que está siendo mostrada, la conexión de control usada, y, en caso de estar conectados a un usuario, la referencia de la conexión UDP usada.

Al usar un patrón *Singleton* nos permite simplificar las interacciones entre la interfaz y la conexión de control, por ejemplo, además de permitir, desde todas las clases, conocer la conexión UDP que está siendo usada, si la hay.

#### UDP

A la hora de definir las clases usadas para establecer una conexión UDP para enviar vídeo entre dos usuarios, queríamos que fuesen los más genéricas posibles, de forma que pudiesen ser fácilmente reutilizables para futuros proyectos, o para implementar conexiones multimedia de distintos tipos, como puede ser audio. Para esto desarrollamos en *udp.py* la clase principal, **UDPConnection**.

Esta clase, gestiona una conexión UDP con intercambio continuo de datos entre dos sistemas. Para ello, a partir de los pares ip y puerto, orgen y destino, se encarga de inicializar las conexiones UDP pertinentes entre ambos.

Se utiliza un buffer de recepción y uno de salida para almacenar los paquetes recibidos y enviados, de forma que un hilo se encarga de leer los paquetes del socket de llegada e introducirlos en el buffer, mientras que otro hilo, se encarga de leer los paquetes del buffer de salida  y dos hilos: el primero se encarga de leer continuamente los paquetes y almacenarlos en el buffer, el segundo se encarga de leer los paquetes del buffer de salida e introducirlos en la red. Ambos hilos están sincronizados mediante eventos, para permitir parar la conexión, reanudarla, y optimizar el uso de CPU.

De esta forma nos aseguramos de que podemos enviar y recibir paquetes desde la interfaz o la conexión de control sin ser bloqueantes.

A partir de esta conexión, hemos desarrollado tres variantes: 

La primera, **VideoConnection**, es una UDPConnection que obtiene de cada datagrama la información del frame de vídeo que contiene (su identificador, timestamp, resolución, fps y la imagen en sí), y los guarda de forma ordenada en el buffer de recepción. Esta clase es la usada para transmitir una videollamada sin voz, de forma que puede ser usada fácilmente desde la interfaz.

La segunda clase, **AudioConnection**, es muy similar, con la única diferencia de que en este caso, se utiliza para enviar fragmentos de audio que van acompañados únicamente de un identificador númerico que permite ordenar los fragmentos.

La tercera clase, **VideoAudioCallConnection**, implementa simultáneamente una conexión de vídeo y otra de audio, y se encarga además de la creación de dos nuevos hilos que permiten enviar el audio recogido del micrófono principal del ordenador, e interpretar los datos recibidos por la conexión de audio para reproducirlos en el altavoz del ordenador. De esta forma, conseguimos simplificar las videollamadas con voz.

#### ControlConnection

Es la clase que representa una conexión de control. Se encarga de, una vez loggeado el usuario, iniciar un servidor TCP iterativo, de forma que evitamos posibles errores al recibir dos llamadas simultáneas, por ejemplo.

Es además el encargado de elegir el protocolo para la conexión con un usuario, y de inicializar, pausar, reanudar y cerrar definitivamente la conexión UDP (independientemente de si es de vídeo o de audio y vídeo) abierta con un usuario según se indique desde la interfaz, y notificando de las llamadas entrantes o las acciones realizadas mediante llamadas a esta misma interfaz.

#### Video client

Es la clase utilizada para representar la interfaz.
En primer lugar, se encarga de mostrar una ventana donde el usuario puede registrarse y/o loggearse, permitiendo además un loggeo rápido al almacenar los datos del último usuario, como hemos explicado anteriormente. Una vez el usuario se ha loggeado, se encarga de notificar a *Application*, y de iniciar la ventana principal y la conexión de control con la que está ampliamente relacionada.

Desde esta ventana principal el usuario puede conectar con otro usuario para llamarle (por video, o por video y voz si el usuario utiliza este mismo cliente con el protocolo V1, como se explicará a continuación), aplicar filtros a la imagen, o cargar un video y reproducir/enviar dicho video.
Desde esta ventana principal se lanzan además sub ventanas que permiten visualizar las videollamadas entrantes, aceptarlas, colgarlas, pausarlas, etc.

Además, según las acciones realizadas, se utiliza la clase *Application* (que es un singleton como comentábamos anteriormente) para acceder a la conexión de control y notificar al destinatario de la conexión sobre dichas acciones.

#### Utils y Filters
Por último, mencionar los módulos secundarios *utils.py*, que implementa funciones auxiliares como la comprobación de si un string se corresponde a una dirección IPv4, el envío de mensajes TCP simples, y permite, por ejemplo, obtener un número $n$ de puertos libres en el sistema, para usarlos posteriormente al iniciar una conexión.

El módulo *filters.py* por su parte implementa algunas funciones que modifican un frame de los devueltos por OpenCV para variar su color, por ejemplo, de forma que permiten añadir filtros muy simples a las videollamadas, e independientes del cliente usado por el receptor. Con este tipo de funciones, se podrían implementar filtros considerablemente más complejos, usando incluso reconocimiento facial, sin embargo, no era el objetivo de la práctica, y se han implementado los incluidos simplemente como ejemplo.

### Protocolo V1

Instalacion de pyaudio, explicacion de sincronizacion, etc 

Las llamadas solo son compatibles con nuestro protocolo donde está establecido por defecto la frecuencia del audio etc, para simplificar.

### Envio de videos

Solo hemos añadido los formatos .mp4 y avi por ser los más conocidos

En este caso no modificamos las dimensiones de la imagen para no distorsionar el video. 

Hasta que no se acaba de enviar el video no se puede volver a enviar webcam

### Filtros