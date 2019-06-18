# Práctica 1

Javier Delgado del Cerro y Javier López Cano 

### Introducción

En esta práctica hemos implementado un servidor concurrente HTTP en C con los métodos *GET*, *POST*, *OPTIONS* y *HEAD*. Además, tenemos un GCI simplificado que permite la ejecución de scripts python o php en el servidor.

### Desarrollo técnico

Nuestro principal objetivo en el desarrollo del servidor era conseguir un equilibrio entre rendimiento, simplicidad y una estabilidad máxima, por lo que, tras sopesar las distintas opciones disponibles, decidimos emplear un esquema con un thread por cada petición, sin pools. De esta forma, la inicialización del servidor es más rápida y simple, con lo que tenemos menos posibilidad de errores y el servidor es más fiable. Obligamos a estos threads a ser independientes del proceso padre *(detached)* para evitar pérdidas de memoria al finalizar el proceso padre usando un *Ctrl+C*.

Así, en nuestro esquema, el proceso principal se encarga únicamente de inicializar el socket TCP al inicio del programa, y de aceptar todas las conexiones entrantes, inicializando un hilo para cada una de ellas, que es el encargado de interpretar y responder a la petición.

Como pretendíamos obtener la mayor estabilidadposible, finalmente decidimos no emplear la función de demonizar que creamos nosotros mismos, pues el profesor de teoría, Oscar, nos comentó que dicho requisito se iba a eliminar, dado que es más sencillo y fiable usar funciones propias del sistema operativo como puede ser *start-stop-daemon*. Aún así, se adjunta la función en *utils.c* en caso de que quiera verse.

#### Parseo de las peticiones

En nuestra búsqueda por conseguir el código lo más simple y óptimo posible, inicialmente valoramos el uso de la librería `PicoHTTPParser` para el parseo de las cabeceras HTTP. Sin embargo, finalmente decidimos implementarlo nosotros por nuestra cuenta, pues una vez comprendimos el funcionamiento del estándar HTTP, nos dimos cuenta que los datos que necesitábamos eran relativamente sencillos de obtener, y de esta forma evitamos dependencias innecesarias de código, y optimizamos el espacio ocupado por nuestro servidor, pues puede ser crítico si se quisiera usar en dispositivos del Internet of Things.

#### Métodos implementados

Hemos implementado únicamente los métodos *GET*, *POST* y *OPTIONS* pedidos, además del método *HEAD* que permite a los navegadores almacenar en caché los archivos y así agilizar las respuestas y disminuir la carga del servidor.

Sin embargo, dada la estructura usada, la implementación de nuevos métodos es extremadamente sencilla, y no requiere grandes modificaciones del servidor. Esto permite la reutilización del código en un futuro para obtener servidores más complejos. Para esto, hemos desarrollado en *http_module* una estructura denominada *method*, que almacena el nombre que caracteriza a method (*GET*, *PUT*, etc), y un puntero a una función del tipo *HTTPMethod*, que se caracteriza por tener la siguiente estructura:

```c
typedef void (*HTTPMethod)(int, char*, char*, extension*, int);

typedef struct {
	char *name;
	HTTPMethod function;
}method;
```

Un ejemplo de cabecera de una de estas funciones es la de GET:

```c
/*
* Funcion que prepara la respuesta HTTP a una peticion GET.
* Parametros:
* 	- fd: socket TCP por el que enviar el mensaje
* 	- path: path del archivo solicitado
* 	- body: cuerpo de la peticion
* 	- ext: extension del fichero del path de la peticion
*	- minor_version: version HTTP de la peticion
*/
void GETMethod(int fd, char *path, char *body, extension *ext, int minor_version);
```

De esta forma, tenemos un array de *method* con todos los métodos implementados en el servidor, con lo que cuando un thread procesa una petición, comprueba el método recibido, y si es uno de los implementados, llama a la función correspondiente, que se encarga de gestionar la petición y escribir la respuesta en el buffer. Si el método pedido no estuviera implementado, enviamos un error *501 Method Not Implemented*.

#### Extensiones de archivos implementados

Para las gestionar las distintas extensiones de archivos, hemos usado un esquema análogo al de los distintos métodos, de forma que definimos una estructura *extension* que incluye la extensión del archivo y el texto con el que se describe en HTTP.

Así, definimos un array con todas las extensiones soportadas, y durante el procesamiento de la petición, el thread se encarga de comprobar si la extensión está soportada, y continuar con la petición entonces, o de enviar un error *403 Forbidden* indicando que no se puede hacer uso de dicha extensión.

Las extensiones soportadas, mostradas como la estructura con la extensión y el *filetype* serían:

```c
extension extensions[] = {
    {"gif", "image/gif" },
    {"jpg", "image/jpg" },
    {"jpeg","image/jpeg"},
    {"png", "image/png" },
    {"ico", "image/ico" },
    {"zip", "image/zip" },
    {"gz",  "image/gz"  },
    {"tar", "image/tar" },
    {"htm", "text/html" },
    {"html","text/html" },
    {"txt","text/plain" },
    {"mpeg","video/mpeg" },
    {"mpg","video/mpg" },
    {"mp4","video/mp4" },
    {"doc","application/msword" },
    {"docx","application/msword" },
    {"pdf","application/pdf" },
    {"py","script" },
    {"php","script" },
    {0,0} };
```

#### Respuestas implementados

A la hora de implementar los errores, definimos definir una función *returnError* en *http_module* que se encarga de, dado un código de error, enviar la respuesta HTTP con un HTML simple. Además, como queríamos que dicha función nos permitiese visualizar correctamente toda la información sobre los errores, nos basamos en la implementación de *printf*, con lo que nos permite imprimir por pantalla, o por syslog (e incluso se podría implementar para completar la respuesta HTTP, aunque no se ha hecho pues daría información a un posible atacante) cadenas formateadas. Un ejemplo de ejecución sería:

`returnError(ERROR_NOT_FOUND, fd, "La peticion %d ha fallado al reservar memoria. %d son demasiados Bytes\n", n, nBytes);`

Usando esto, hemos implementado unas cuantas respuestas, además de las obligatorias, de forma que el cliente pueda detectar con mayor exactitud posibles errores:

| Respuesta              | Código | Significado                                                  |
| ---------------------- | ------ | ------------------------------------------------------------ |
| OK                     | 200    | La respuesta se ha completado con éxito.                     |
| Bad Request            | 400    | El servidor no pudo interpretar la petición correctamente, probablemente debido a un error de sintaxis. |
| Forbidden              | 403    | No se puede acceder al recurso solicitado, por ser una dirección o extensión no permitida. |
| Not Found              | 404    | El recurso solicitado no se encuentra en el servidor.        |
| Internal Server Error  | 500    | El servidor no ha sido capaz de procesar la petición por un error interno. Por ejemplo, un fallo al reservar memoria. |
| Method Not Implemented | 501    | El método pedido no está implementado en el servidor.        |

#### Fichero de configuración

Para implementar la configuración del servidor mediante fichero, hemos usado la librería `libconfuse` recomendada, de forma que nosotros simplemente tenemos que encargarnos de liberar la memoria de los parámetros que requieran. En este fichero se pueden configurar:

- El directorio raíz a partir del cual se encuentran los archivos del servidor.
- El número máximo de clientes simultáneos que es capaz de gestionar el servidor.
- El puerto TCP sobre el que funcionará el servidor.
- La *firma* del servidor, usada para los syslog y para las cabeceras de respuestas HTTP enviadas.

#### CGI

Para implementar el CGI con ejecución de scripts en primer lugar debemos determinar el tipo de petición GET, POST o GET/POST y obtener los argumentos o bien de la URL o del cuerpo de la petición o incluso de ambos en el caso de GET/POST; y, a partir de estos argumentos, hallar el path del script a ejecutar, los argumentos del script y la extensión, como se ha explicado en el apartado de "métodos implementados".

Una vez obtenidos estos parámetros, la función `exec_script` del fichero `cgi.c` se encarga de la ejecución del script. Para ello en primer lugar inicializa 2 pipes para comunicación entre procesos y realiza un `fork` para generar un proceso hijo que se encargará de la ejecución.

El proceso hijo emplea la función `dup2` para enlazar el extremo del lectura del pipe en el que escribe el padre con su STDIN, y el extremo de escritura del otro pipe con su STDOUT, tras lo cual mediante la función `execvp` ejecuta el script del path pasado por parámetro, bien con "php" si la extensión es `.php` o con "python3" si la extensión es `.py`.

Mientras tanto el proceso padre escribe los argumentos del script en el extremo de escritura del pipe enlazado con el STDIN del proceso hjo, de este modo, el script que se está ejecutando, al leer de STDIN recibirá los argumentos y podrá ejecutarse correctamente. Del mismo modo, la salida del script se imprimirá en el STDOUT del proceso hijo, que al estar enlazado con el extremo de escritura del otro pipe permite que, cuando el padree lee del extremo de lectura de este, obtiene la salida del script, que luego puede enviar como respuesta del script, obteniendo así la funcionalidad deseada.

Además de en estos dos lenguajes (python y php) hemos añadido como funcionalidad extra que se puedan ejecutar también scripts en bash cuando la extensión sea `.sh`, y, por el modo en el que está diseñado el código, sería muy sencillo ampliarlo a más lenjuajes como Ruby o JavaScript. Para ello, tan solo sería necesario añadir un condicional (equivalente al realizado para python, php y bash) que, dependiendo de la extensión que recibe la función `exec_script` lanza el programa adecuado para ejecutar el script en el lenguaje correcto.

Debido al hecho de que hemos añadido la ejecución de scripts en bash, hemos tenido que modificar el archivo `index.html` para que la página muestre los botones para ejecutar scripts en bash. Por este motivo nos hemos vito obligados a subir a GitLab la carpeta `htmlfiles`.

Como era necesario incluir una librería `.a` en la práctica, decidimos que fuese esta función, pues es posible que la podamos reutilizar en futuros proyectos.

### Conclusiones técnicas

Una vez finalizada la práctica, hemos observado como, un concepto simple como un servidor HTTP, requiere muchísimo más cuidado del que parece a simple vista, sobre todo para evitar fugas de memoria y errores que pueden llevar al servidor a caer ante posibles ataques.

Nos ha llevado bastante más tiempo del que pensábamos que sería necesario eliminar todas las fugas de memoria, y plantear el funcionamiento del código para que fuese óptimo y seguro, sin embargo, podemos afirmar que esta práctica nos ha permitido entender y manejar con soltura conceptos como los sockets TCP y estándares como el HTTP, comprendiendo muchos de los errores de desarrollo comunes que provocan caídas de páginas web ante diversos ataques, por ejemplo, el no prohibir el acceso a direcciones como `0.0.0.0:8000/../../privado`.

### Conclusiones personales

La práctica nos ha parecido bastante interesante a ambos. Es el primer proyecto de este tipo que realizamos que realmente tiene cierta utilidad para el mundo real, y nos ha permitido aprender a coordinarnos entre los dos para dividir la funcionalidad en módulos y trabajar simultáneamente gracias al uso de git.

La única sugerencia que podríamos tener para otros años es modificar la ejecución de scripts para usar en vez de un CGI simplificado como hemos hecho en esta práctica, un intérprete embebido simpificado, como se comenta en el enunciado que se utilizan actualmente.