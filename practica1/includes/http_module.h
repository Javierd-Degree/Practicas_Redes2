#ifndef HTTP_MODULE_H
#define HTTP_MODULE_H

#define ERROR_BAD_REQUEST			400
#define ERROR_FORBIDDEN     		403
#define ERROR_NOT_FOUND     		404
#define ERROR_INTERNAL      		500
#define ERROR_NOT_IMPLEMENTED		501

typedef struct {
    char *ext;
    char *filetype;
}extension;

typedef void (*HTTPMethod)(int, char*, char*, extension*, int);

typedef struct {
	char *name;
	HTTPMethod function;
}method;


/* Queremos poder acceder al nombre del servidor
	y a la ubicacion del sistema de archivos desde
	otros modulos*/
extern char* SERVER_ROOT;
extern char* SERVER_SIGN;
extern extension extensions[];
extern method methods[];

/*
* Funcion que devuelve una pagina web HTTP del error correspondiente e
* imprime por pantalla informacion sobre el error.
* Parametros:
* 	- errCode: codigo de error HTTP
* 	- socket: socket por el que enviar el mensaje
* 	- format: string que formatea la informacion a imprimir
* 	- ... argumentos a incluir en el formateo
*/
void returnError(int errCode, int socket, const char *format, ...);

/*
* Funcion que parsea una cabecera HTTP para obtener los cambos basicos
* Parametros:
* 	- buffer: buffer donde está almacenada la cabecera
* 	- method: puntero a string para almacenar el metodo HTTP de la cabecera
* 	- path: puntero a string para almacenar el path HTTP de la cabecera
* 	- minor_version: puntero a entero para almacenar la version HTTP de la cabecera
* 	- body: puntero a string para almacenar el body HTTP de la cabecera
* Return: 0 si ha funcionado correctamente, -1 en caso contrario
*/
int parseRequest(char *buffer, char **method, char **path, int *minor_version, char** body);

/*
* Funcion que prepara la respuesta HTTP a una peticion.
* Parametros:
* 	- fd: socket TCP por el que enviar el mensaje
* 	- path: path del archivo solicitado
* 	- method: metodo solicitado
* 	- body: cuerpo de la peticion
*	- minor_version: version HTTP de la peticion
*/
void HTTPResponse(int fd, char *path, char *method, char *body, int minor_version);

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

/*
* Funcion que prepara la respuesta HTTP a una peticion POST.
* Parametros:
* 	- fd: socket TCP por el que enviar el mensaje
* 	- path: path del archivo solicitado
* 	- body: cuerpo de la peticion
* 	- ext: extension del fichero del path de la peticion
*	- minor_version: version HTTP de la peticion
*/
void POSTMethod(int fd, char *path, char *body, extension *ext, int minor_version);

/*
* Funcion que prepara la respuesta HTTP a una peticion OPTIONS.
* Parametros:
* 	- fd: socket TCP por el que enviar el mensaje
* 	- path: path del archivo solicitado
* 	- body: cuerpo de la peticion
* 	- ext: extension del fichero del path de la peticion
*	- minor_version: version HTTP de la peticion
*/
void OPTIONSMethod(int fd, char *path, char *body, extension *ext, int minor_version);

/*
* Funcion que prepara la respuesta HTTP a una peticion HEAD.
* Parametros:
* 	- fd: socket TCP por el que enviar el mensaje
* 	- path: path del archivo solicitado
* 	- body: cuerpo de la peticion
* 	- ext: extension del fichero del path de la peticion
*	- minor_version: version HTTP de la peticion
*/
void HEADMethod(int fd, char *path, char *body, extension *ext, int minor_version);

#endif