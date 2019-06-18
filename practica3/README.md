## Introducción

En esta tercera y última práctica de la asignatura Redes de Comunicaciones 2, se pedía el desarrollo de una aplicación de videollamadas basada en el uso de un servidor de descubrimiento para obtener la dirección del usuario receptor, una conexión TCP de control que permitiese recibir llamadas y comandos para controlar la videollamada, y el establecimiento de una conexión UDP para el envío de vídeo entre los dos usuarios. Además, hemos implementado distintos extras que se explicarán a lo largo de la documentación, como son filtros OpenCV y la adición de voz a las llamadas.

## Desarrollo técnico

Para facilitar el desarrollo de proyecto, lo hemos dividido en módulos bastante claros, algunos de ellos interrelacionados, que explicaremos a continuación. Además, han sido necesarios diferentes hilos, sincronizados entre ellos con eventos y semáforos para optimizar el funcionamiento de la aplicación.

### Instalación y uso

Hemos implementado, como explicaremos posteriormente, llamadas de vídeo y audio, para lo que hemos tenido que usar la librería *pyaudio*, que depende a su vez de *alsaaudio*, por tanto, es necesario instalar las siguientes librerías antes de ejecutar la práctica:
```bash
sudo apt install libasound-dev portaudio19-dev libportaudiocpp0
sudo pip3 install pyaudio
```

A la hora de usar la aplicación, no es necesario introducir ningún parámetro, basta con ejecutar, una vez situados en el directorio principal del programa:

```bash
python3 main.py
```

### Módulos de la aplicación

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

Utilizamos también el status bar de la ventana AppJar para mostrar información como la resolución y fps del audio recibido, el retraso calculado de llegada (que depende del timestamp enviado con los frames recibidos, con lo que si los dos ordenadores no tienen exactamente la misma hora, no es preciso, pero era la única forma de implementarlo con el protocolo dado), y la duración de la llamada.

Además, según las acciones realizadas, se utiliza la clase *Application* (que es un singleton como comentábamos anteriormente) para acceder a la conexión de control y notificar al destinatario de la conexión sobre dichas acciones.

#### Utils y Filters
Por último, mencionar los módulos secundarios *utils.py*, que implementa funciones auxiliares como la comprobación de si un string se corresponde a una dirección IPv4, el envío de mensajes TCP simples, y permite, por ejemplo, obtener un número $n$ de puertos libres en el sistema, para usarlos posteriormente al iniciar una conexión.

El módulo *filters.py* por su parte implementa algunas funciones que modifican un frame de los devueltos por OpenCV para variar su color, por ejemplo, de forma que permiten añadir filtros muy simples a las videollamadas, e independientes del cliente usado por el receptor. Con este tipo de funciones, se podrían implementar filtros considerablemente más complejos, usando incluso reconocimiento facial, sin embargo, no era el objetivo de la práctica, y se han implementado los incluidos simplemente como ejemplo.



Una vez comentados los distintos módulos usados en la aplicación, y su estructura, vamos a comentar algunos otros detalles de los hechos en la implementación.

### Llamadas de vídeo y voz: Protocolo V1

Una vez completados los requisitos de la aplicación, decidimos implementar audio a las videollamadas. 

Para esto, nos hemos basado en la librería de manejo y captura de audio **pyaudio**, de forma que es necesario instalarla, y que reconozca correctamente el micrófono conectado al ordenador (cosa que debería hacer por defecto dicha librería), de lo contrario, estas llamadas no funcionarán.

En este caso, hemos realizado una implementación muy primitiva de las llamadas con voz mediante la clase **VideoAudioCallConnection** explicada anteriormente, sin ninguna sincronización implícita entre audio y vídeo, con lo que puede haber cierto desfase, y con una función *rms* que calcula la media de los valores recogidos por el micrófono para "detectar" momentos de silencio. 

Con el fin de simplificar esta nueva versión del protocolo, iniciamos la captura de audio con los mismos valores independientemente del micrófono, ordenador, etc, pues no tenemos conocimientos avanzados de cómo modificar dichos valores, y tampoco era el objetivo de la práctica. Esto provoca que la calidad del sonido no sea óptima, y al haber establecido un *threshold* genérico para detectar el silencio, dependiendo del micrófono es necesario elevar el nivel de voz para que no detecte la entrada como silencio.

La forma en la que hemos implementado estas videollamadas con voz nos permitiría añadir con mucha facilidad llamadas únicamente de audio, sin embargo, decidimos dejar de lado esta implementación a favor de los filtros OpenCV explicados posteriormente, que al ser algo independiente a lo implementado hasta el momento consideramos que podría ser más interesante.

#### Protocolo V1

Para poder usar estas llamadas por voz hemos definido una pequeña modificación del protocolo V0, y lo hemos llamado protocolo V1. La idea es que, en este caso, las videollamadas incluyen audio, de forma que cuando dos aplicaciones compatibles con dicho protocolo se conectan entre sí (de momento solo nuestro cliente es compatible con dicho protocolo, pues hemos establecido unos valores por defecto en la captura y reproducción de audio que tienen que ser iguales en emisor y receptor), se utilizan estas llamadas para la comunicación.

Para este protocolo, en comando *CALLING* pasa a ser *CALLING_V1* y su descripción sería:

- Objetivo: Señalizar que un nodo quiere establecer una videollamada con audio con otro.
- Sintaxis: *CALLING_V1 nick srcUDPVideoPort srcUDPAudioPort*, donde *srcUDPVideoPort* es el puerto UDP en el que el llamante desea recibir el vídeo del llamado, y *srcUDPAudioPort* donde se desea recibir el audio.
- Posibles respuestas/errores:
  - *CALL_ACCEPTED_V1 nick dstUDPVideoPort dstUDPAudioPort*, donde *dstUDPAudioPort* es el puerto donde el llamado recibirá el vídeo y *dstUDPAudioPort* donde recibirá el audio.
  - *CALL_DENIED nick*, el usuario rechaza la llamada entrante.
  - *CALL_BUSY*, el llamado está en una llamada y no puede recibir la comunicación. 

El resto de los comandos implementados son los mismos que en el protocolo V0 dado.

### Envío de vídeos

Otro de los requisitos pedidos en la práctica era la posibilidad de retransmitir un vídeo almacenado como archivo a través de la red. Para esto, hemos añadido un botón *Cargar vídeo* en la parte inferior de la web que abre una ventana del explorador de archivos y permite retransmitir archivos de vídeo *.mp4* y *.avi* (hemos añadido estos por ser los más populares, pero se podrían añadir más tipos de archivos siempre que sean compatibles con OpenCV). Además, en cualquier momento de la retransmisión del vídeo se puede cancelar y reanudar la retransmisión de la webcam, y en caso de finalizar el vídeo transmitido, se reanuda la webcam por defecto.

### Filtros

Otra de las funcionalidades extra implementadas es la posibilidad de aplicar filtros sobre el vídeo enviado, ya sea proveniente de la webcam o de un archivo, de forma completamente independiente al protocolo usado. Para esto, hemos desarrollado el módulo **filters** explicado anteriormente, que permite modificar cada uno de los frames OpenCV.

En este caso, hemos añadido un filtro *Sepia*, otro *Negativo* que invierte los colores de la imagen, un filtro *Borroso* que desenfoca toda la imagen excepto un círculo central, y un filtro por cada uno de los colores primarios, rojo, verde y azul. Como hemos mencionado anteriormente, esto abre un abanico enorme de posibilidades para desarrollar nuevos filtros. 

### Logger

Por último, mencionar que para facilitar la detección de posibles errores de la aplicación, hemos usado el módulo *logging* de Python para establecer en nuestras clases un logger propio, de forma que almacenamos en ficheros denominados *log.i* información sobre el funcionamiento de la aplicación, y sobre los posibles errores y/o excepciones que sucedan.

De esta forma, es muchísimo más sencillo conocer el origen de cualquier tipo de fallo y solucionarlo muy fácilmente.

## Conclusión técnica

Como conclusión, comentar que la práctica nos ha enseñado a comprender el funcionamiento de la transmisión de audio y vídeo al que tan acostumbrados estamos actualmente. 

Nos ha permitido además aprender a gestionar y sincronizar correctamente los hilos de la librería threading de Python, usando semáforos, eventos, etc. Esto ha sido justamente dónde más problemas hemos tenido, pues en un principio se producían interbloqueos y posteriormente un consumo exagerado de CPU.

Otra de las dificultades fue el envío de los frames de vídeo, junto con la información de número de frame, resolución, fps, etc. Acostumbrados a trabajar con lenguajes fuertemente tipados como C, en Python, donde todo parece mucho más "flexible", nos encontramos con múltiples fallos debidos a errores de concepto al convertir los datos entre distintos formatos. Una vez solucionados dichos fallos, y la sincronización de hilos, la práctica funcionaba sin problemas.

## Conclusión personal

A nivel personal, ha sido sin ninguna duda la práctica más desafiante del curso. Inicialmente no teníamos mucha idea de como comenzar la implementación de las conexiones ni de como dividirlas en módulos independientes para asignarnos cada uno una parte del trabajo, lo que nos ha llevado a ir haciendo todo entre los dos, con poca organización.
Sin embargo, la práctica en sí ha sido muy interesante, la única pega que podemos ponerle es la interfaz proporcionada:

AppJar de por sí está bastante limitada respecto a otras librerías de interfaz gráfica como GTK3, y sin emargo no hay mucha diferencia en la curva de aprendizaje o la dificultad entre ambas. Además, la versión proporcionada de AppJar es bastante antigua, lo que limita el uso de algunas funciones más nuevas.
Para el año que viene proponemos el uso de GTK3, que puede dar lugar a interfaces mucho más vistosas y es un entorno que realmente se utiliza en el desarrollo actual.