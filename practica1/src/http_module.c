/**************************************************
*   Javier Delgado del Cerro
*   Javier Lopez Cano
*   Pareja 2
*
*   Modulo para procesar peticiones y respuestas
*   HTTP.
**************************************************/

#include <unistd.h>
#include <stdio.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <signal.h>
#include <stdarg.h>
#include <errno.h>
#include <syslog.h>

#include "utils.h"
#include "http_module.h"
#include "cgi.h"


char* SERVER_ROOT;
char* SERVER_SIGN;

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
    {"py","text/html" },
    {"php","text/html" },
    {0,0} };


method methods[] = {
    {"GET" , GETMethod},
    {"POST", POSTMethod},
    {"OPTIONS", OPTIONSMethod},
    {"HEAD", HEADMethod},
    {0, 0} };

/*
* Funcion que devuelve una pagina web HTTP del error correspondiente e
* imprime por pantalla informacion sobre el error.
* Parametros:
*   - errCode: codigo de error HTTP
*   - socket: socket por el que enviar el mensaje
*   - format: string que formatea la informacion a imprimir
*   - ... argumentos a incluir en el formateo
*/

void returnError(int errCode, int socket, const char *format, ...){
	va_list arg;
	va_start (arg, format);
	//vfprintf (stdout, format, arg);
    vsyslog(LOG_ERR, format, arg);
	va_end (arg);
    fflush(stdout);

    switch (errCode) {
    case ERROR_INTERNAL:
        write(socket, "HTTP/1.1 500 Internal Server Error\nContent-Length: 153\nConnection: close\nContent-Type: text/html\r\n\r\n<html><head>\n<title>500 Internal Server Error</title>\n</head><body>\n<h1>Server Error</h1>\nThere was an error while processing the request\n</body></html>\n", 253);
        break;
    case ERROR_FORBIDDEN:
        write(socket, "HTTP/1.1 403 Forbidden\nContent-Length: 166\nConnection: close\nContent-Type: text/html\r\n\r\n<html><head>\n<title>403 Forbidden</title>\n</head><body>\n<h1>Forbidden</h1>\nThe requested URL, file type or operation is not allowed on this webserver.\n</body></html>\n", 254);
        break;
    case ERROR_NOT_FOUND:
        write(socket, "HTTP/1.1 404 Not Found\nContent-Length: 138\nConnection: close\nContent-Type: text/html\r\n\r\n<html><head>\n<title>404 Not Found</title>\n</head><body>\n<h1>Not Found</h1>\nThe requested URL was not found on this server.\n</body></html>\n", 226);
        break;
    case ERROR_BAD_REQUEST:
    	write(socket, "HTTP/1.1 400 Bad Request\nContent-Length: 133\nConnection: close\nContent-Type: text/html\r\n\r\n<html><head>\n<title>400 Bad Request</title>\n</head><body>\n<h1>Bad Request</h1>\nThe requested URL was not well formed.\n</body></html>\n", 223);
    	break;
    case ERROR_NOT_IMPLEMENTED:
        write(socket, "HTTP/1.1 501 Method Not Implemented\nContent-Length: 156\nConnection: close\nContent-Type: text/html\r\n\r\n<html><head>\n<title>501 Method Not Implemented</title>\n</head><body>\n<h1>Method Not Implemented</h1>\nThe requested method is not implemented\n</body></html>\n", 257);
    	break;
    }
}

/*
* Funcion que parsea una cabecera HTTP para obtener los cambos basicos
* Parametros:
*   - buffer: buffer donde está almacenada la cabecera
*   - method: puntero a string para almacenar el metodo HTTP de la cabecera
*   - path: puntero a string para almacenar el path HTTP de la cabecera
*   - minor_version: puntero a entero para almacenar la version HTTP de la cabecera
*   - body: puntero a string para almacenar el body HTTP de la cabecera
* Return: 0 si ha funcionado correctamente, -1 en caso contrario
*/
int parseRequest(char* buffer, char** method, char **path,
    int* minor_version, char** body){
    int i;

    /*Cogemos el metodo de la peticion*/
    *method = buffer;
    for(i = 0; (i < MAXBUF) && (buffer[i] != ' '); i++);
    buffer[i] = '\0';

    /*Cogemos la direccion de la peticion*/
    i++;
    *path = buffer + i;
    for(; (i < MAXBUF) && (buffer[i] != ' '); i++);
    buffer[i] = '\0';

    /*Cogemos la version de HTTP*/
    i++;
    if(sscanf(buffer+i, "HTTP/1.%d", minor_version) != 1){
        syslog(LOG_ERR, "Error al obtener la version HTTP\n");
        syslog(LOG_ERR, "%s\n", buffer);
        return -1;
    }

    /*Cogemos el body de la peticion*/
    for(; (i < MAXBUF) && ((buffer[i] != '\n') || (buffer[i-1] != '\r')
    || (buffer[i-2] != '\n') || (buffer[i-3] != '\r')) ; i++);
    *body = buffer + i +1;

    return 0;
}

/*
* Funcion que prepara la respuesta HTTP a una peticion GET.
* Parametros:
*   - fd: socket TCP por el que enviar el mensaje
*   - path: path del archivo solicitado
*   - body: cuerpo de la peticion
*   - ext: extension del fichero del path de la peticion
*   - minor_version: version HTTP de la peticion
*/
void GETMethod(int fd, char *path, char *body, extension *ext, int minor_version){
    int file_fd, ret, i;
    long len;
    char buffer[MAXBUF + 1];
    char *date, *lastModifiedDate, *aux;
    char *htmlStart = "<html><body>", *htmlEnd = "</body></html>\n";
    char *voidPath = "";

    date = getCurrentDate();
    if(date == NULL){
        returnError(ERROR_INTERNAL, fd, "Error al obtener las fechas de HTTP.\n");
        return;
    }

    /* Si se nos pide ejecutar un script */
    if((strcmp(ext->ext, "py") == 0) || strcmp(ext->ext, "php") == 0){
        for(i = 0; (path[i] != '?') && (path[i] != '\0'); i++);
        aux = (i == strlen(path)) ? voidPath : (path+i+1);
        path[i] = '\0';

        syslog(LOG_INFO, "Ejecutamos el  GET %s con los argumentos %s\n", path, aux);
        aux = exec_script(path, aux, ext->ext);

        if(aux == NULL){
            returnError(ERROR_INTERNAL, fd, "Error al ejecutar el script pedido\n");
            free(aux);
            free(date);
            return;
        }

        /* Si es un script, establecemos la fecha de modificación como la actual, pues la
        salida se genera en el momento, y depende de la entrada, no solo del contenido del script*/
        len = strlen(aux) + strlen(htmlStart) + strlen(htmlEnd);
        sprintf(buffer,"HTTP/1.%d 200 OK\nServer: %s\nContent-Length: %ld\nConnection: close\nContent-Type: %s\nDate: %s\nLast-Modified: %s\r\n\r\n", minor_version, SERVER_SIGN, len, ext->filetype, date, date);
        write(fd,buffer,strlen(buffer));

        /* Queremos enviar el resultado del script como HTML*/
        write(fd, htmlStart, strlen(htmlStart));

        /* Escribimos la respues entera en el socket */
        write(fd, aux, strlen(aux));

        write(fd, htmlEnd, strlen(htmlEnd));

        free(aux);
        free(date);
        return;
    }

    /* Si es un archivo normal y no un script */
    lastModifiedDate = getFileLastModifiedDate(path);
    if((lastModifiedDate == NULL) && (errno != 2)){
        /* Evitamos mandar el error 500 si falla porque el archivo no existe*/
        returnError(ERROR_INTERNAL, fd, "Error al obtener las fechas de HTTP.\n");
        free(date);
        return;
    }else if((lastModifiedDate == NULL) && (errno == 2)){
        /*Falla porque el archivo no existe*/
        returnError(ERROR_NOT_FOUND, fd, "El arhivo %s no existe\n", path);
        free(date);
        return;
    }

    /*Enviamos la respuesta*/
    if(( file_fd = open(path, O_RDONLY)) == -1) {
        returnError(ERROR_NOT_FOUND, fd, "El archivo %s no existe\n", path);
        free(date);
        free(lastModifiedDate);
        return;
    }

    len = (long)lseek(file_fd, (off_t)0, SEEK_END); /* Miramos la longitud del fichero */
    (void)lseek(file_fd, (off_t)0, SEEK_SET); /* Volvemos al principio */

    sprintf(buffer,"HTTP/1.%d 200 OK\nServer: %s\nContent-Length: %ld\nConnection: close\nContent-Type: %s\nDate: %s\nLast-Modified: %s\r\n\r\n", minor_version, SERVER_SIGN, len, ext->filetype, date, lastModifiedDate);
    write(fd,buffer,strlen(buffer));

    free(date);
    free(lastModifiedDate);

    while ((ret = read(file_fd, buffer, MAXBUF)) > 0 ) {
        write(fd, buffer, ret);
    }
}

/*
* Funcion que prepara la respuesta HTTP a una peticion POST.
* Parametros:
*   - fd: socket TCP por el que enviar el mensaje
*   - path: path del archivo solicitado
*   - body: cuerpo de la peticion
*   - ext: extension del fichero del path de la peticion
*   - minor_version: version HTTP de la peticion
*/
void POSTMethod(int fd, char *path, char *body, extension *ext, int minor_version){
    char buffer[MAXBUF + 1];
    char *date, *aux, *args;
    char *htmlStart = "<html><body>", *htmlEnd = "</body></html>\n";
    char *voidPath = "";
    int i, len;

    date = getCurrentDate();
    if(date == NULL){
        returnError(ERROR_INTERNAL, fd, "Error al obtener la fecha actual para HTTP.\n");
        return;
    }

    if((strcmp(ext->ext, "py") == 0) || strcmp(ext->ext, "php") == 0){
        /* Puede ser POST o GET/POST */
        for(i = 0; (path[i] != '?') && (path[i] != '\0'); i++);
        
        aux = (i == strlen(path)) ? voidPath : (path+i+1);
        path[i] = '\0';

        args = (char *)malloc((strlen(body)+strlen(aux)+2)*sizeof(char));
        if(args == NULL){
            returnError(ERROR_INTERNAL, fd, "Error al reservar memoria para los argumentos del script.\n");
            free(date);
            return;
        }

        sprintf(args, "%s %s", body, aux);

        /* Comprobamos si el archivo existe o no */
        if(access(path, F_OK) == -1 ) {
            returnError(ERROR_INTERNAL, fd, "Error al ejecutar el script pedido\n");
            free(date);
            return;
        }

        syslog(LOG_INFO, "Ejecutamos el script POST %s con los argumentos %s\n", path, args);
        aux = exec_script(path, args, ext->ext);

        if(aux == NULL){
            returnError(ERROR_NOT_FOUND, fd, "El archivo %s no existe\n", path);
            free(aux);
            free(args);
            free(date);
            return;
        }

        len = strlen(aux) + strlen(htmlStart) + strlen(htmlEnd);
        sprintf(buffer,"HTTP/1.%d 200 OK\nServer: %s\nContent-Length: %d\nConnection: close\nContent-Type: %s\nDate: %s\r\n\r\n", minor_version, SERVER_SIGN, len, ext->filetype, date);
        write(fd,buffer,strlen(buffer));

       /* Queremos enviar el resultado del script como HTML*/
        write(fd, htmlStart, strlen(htmlStart));

        /* Escribimos la respues entera en el socket */
        write(fd, aux, strlen(aux));

        write(fd, htmlEnd, strlen(htmlEnd));

        free(aux);
        free(args);
        free(date);
        return;
    }

    sprintf(buffer,"HTTP/1.%d 200 OK\nServer: %s\nContent-Length: 11\nConnection: close\nContent-Type: %s\nDate: %s\r\n\r\nPOST_METHOD", minor_version, SERVER_SIGN, ext->filetype, date);
    write(fd,buffer,strlen(buffer));
    free(date);
}

/*
* Funcion que prepara la respuesta HTTP a una peticion OPTIONS.
* Parametros:
*   - fd: socket TCP por el que enviar el mensaje
*   - path: path del archivo solicitado
*   - body: cuerpo de la peticion
*   - ext: extension del fichero del path de la peticion
*   - minor_version: version HTTP de la peticion
*/
void OPTIONSMethod(int fd, char *path, char *body, extension *ext, int minor_version){
    char buffer[MAXBUF + 1];
    char *date;

    date = getCurrentDate();
    if(date == NULL){
        returnError(ERROR_INTERNAL, fd, "Error al obtener la fecha actual para HTTP.\n");
        return;
    }

    sprintf(buffer,"HTTP/1.%d 200 OK\nServer: %s\nAllow: OPTIONS, GET, POST, HEAD\nContent-Length: 0\nConnection: close\nContent-Type: %s\nDate: %s\r\n\r\n", minor_version, SERVER_SIGN, ext->filetype, date);
    write(fd,buffer,strlen(buffer));

    free(date);
}

/*
* Funcion que prepara la respuesta HTTP a una peticion HEAD.
* Parametros:
*   - fd: socket TCP por el que enviar el mensaje
*   - path: path del archivo solicitado
*   - body: cuerpo de la peticion
*   - ext: extension del fichero del path de la peticion
*   - minor_version: version HTTP de la peticion
*/
void HEADMethod(int fd, char *path, char *body, extension *ext, int minor_version){
    int file_fd;
    long len;
    char buffer[MAXBUF + 1];
    char *date, *lastModifiedDate;

    date = getCurrentDate();
    if(date == NULL){
        returnError(ERROR_INTERNAL, fd, "Error al obtener la fecha actual para HTTP.\n");
        return;
    }

    lastModifiedDate = getFileLastModifiedDate(path);
    if((lastModifiedDate == NULL) && (errno != 2)){
        /* Evitamos mandar el error 500 si falla porque el archivo no existe*/
        returnError(ERROR_INTERNAL, fd, "Error al obtener las fechas de HTTP.\n");
        free(date);
        return;
    }else if((lastModifiedDate == NULL) && (errno == 2)){
        /*Falla porque el archivo no existe*/
        free(date);
        returnError(ERROR_NOT_FOUND, fd, "El arhivo %s no existe\n", path);
        return;
    }


    /*Enviamos la respuesta*/
    if(( file_fd = open(path, O_RDONLY)) == -1) {
        returnError(ERROR_NOT_FOUND, fd, "El archivo %s no existe\n", path);
        free(date);
        free(lastModifiedDate);
        return;
    }

    len = (long)lseek(file_fd, (off_t)0, SEEK_END); /* Miramos la longitud del fichero */
    (void)lseek(file_fd, (off_t)0, SEEK_SET); /* Volvemos al principio */

    sprintf(buffer,"HTTP/1.%d 200 OK\nServer: %s\nContent-Length: %ld\nConnection: close\nContent-Type: %s\nDate: %s\nLast-Modified: %s\r\n\r\n", minor_version, SERVER_SIGN, len, ext->filetype, date, lastModifiedDate);
    write(fd,buffer,strlen(buffer));

    free(date);
    free(lastModifiedDate);
}

/*
* Funcion que prepara la respuesta HTTP a una peticion.
* Parametros:
*   - fd: socket TCP por el que enviar el mensaje
*   - path: path del archivo solicitado
*   - method: metodo solicitado
*   - body: cuerpo de la peticion
*   - minor_version: version HTTP de la peticion
*/
void HTTPResponse(int fd, char *path, char *method, char *body, int minor_version){
    char *aux, *path_aux;
    extension *ext;
    HTTPMethod method_funct;
    long len;
    int i;

    path_aux = path;
    if((strcmp(path, "/") == 0) || (path == NULL)){
        path_aux = "/index.html";
    }

    len = strlen(path_aux) + strlen(SERVER_ROOT) + 1;

    aux = (char *)malloc(len*sizeof(char));
    if(aux == NULL){
        returnError(ERROR_INTERNAL, fd, "Error al reservar memoria.");
        return;
    }
    if((SERVER_ROOT[strlen(SERVER_ROOT) - 1] == '/') && (path_aux[0] == '/')){
        /* Evitamos que haya / dobles */
    	path_aux = path_aux + 1;
    }

    sprintf(aux, "%s%s", SERVER_ROOT, path_aux);

    /* Comprobamos que no se intente acceder a direcciones no permitida */
    for(i = 0;i < strlen(aux) - 1; i++){
        if(aux[i] == '.' && aux[i+1] == '.') {
            returnError(ERROR_FORBIDDEN, fd, "Intenta acceder a una dirección no permitida.");
            free(aux);
            return;
        }
    }

    /* Comprobamos el formato del archivo, y si lo soportamos */
    ext = NULL;
    for(i = 0; (i < strlen(aux)) && (aux[i] != '?'); i++);
    int extEnd = i;
    for(i=0; extensions[i].ext != 0; i++) {
        len = strlen(extensions[i].ext);
        if( !strncmp(&aux[extEnd-len], extensions[i].ext, len)) {
            ext = &extensions[i];
            break;
        }
    }

    /*printf("Extension de fichero: %s\n", ext->filetype);*/
    if(ext == NULL) {
        returnError(ERROR_FORBIDDEN, fd, "Extension de fichero no permitida");
        free(aux);
        return;
    }

    /*Cogemos el metodo http usado*/
    method_funct = NULL;
    for(i=0; methods[i].name != 0; i++) {
        len = strlen(methods[i].name);
        if( !strncmp(method, methods[i].name, len)) {
            method_funct = methods[i].function;
            break;
        }
    }

    /* Metodo no soportado */
    if(method_funct == NULL) {
        returnError(ERROR_NOT_IMPLEMENTED, fd, "Metodo HTTP no permitido");
        free(aux);
        return;
    }

    syslog(LOG_INFO, "Peticion HTTP/1.%d %s, con path %s, extension %s y body %s. Socket %d", minor_version, method, aux, ext->ext, body, fd); 

    method_funct(fd, aux, body, ext, minor_version);

    /* Esperamos a que se envíen los datos. */
    free(aux);
    sleep(1);
}
