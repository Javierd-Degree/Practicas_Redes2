#ifndef UTILS_H_
#define UTILS_H_

#include <sys/types.h>
#include <unistd.h>
#include <sys/stat.h>
#include <syslog.h>
#include <stdio.h>
#include <stdlib.h>

#define IOError 				-10
#define ParseError 				-11
#define RequestIsTooLongError 	-12

#define OUTPUT_SDTOUT			1
#define OUTPUT_SYSLOG			1

#define MAXBUF					4096

/*
* Funcion que demoniza el proceso que la ejecuta, inicializando syslog.
* Parametros:
* 	- servicio: nombre usado en el syslog.
* Return: 0 si no hay ningun error, -1 en caso contrario.
*/
int demonizar(char* servicio);

/*
* Funcion que lee los parametros de configuracion del servidor.
* Parametros:
* 	- src: direccion del archivo que contiene la configuracion.
* 	- clients: puntero a entero donde almacenar el numero maximo de clientes
* 	- port: puntero a entero donde almacenar el puerto del servidor
* 	- root: puntero a string donde almacenar la raiz de los archivos del servidor
* 	- name: puntero a string donde almacenar el nombre del servidor
* Return: 0 si no hay ningun error, -1 en caso contrario.
*/
int readServerConfig(char *src, int *clients, int *port, char **root, char **name);

/*
* Funcion que devuelve la fecha actual en el formato usado por HTTP
* Return: char* con memoria reservada que incluye la fecha actual.
*/
char* getCurrentDate();

/*
* Funcion que devuelve la fecha de ultima modificacion de un archivo 
* en el formato usado por HTTP
* Parametros:
* 	- path: direccion del archivo
* Return: char* con memoria reservada que incluye la fecha de ultima 
* modificacion del archivo path.
*/
char* getFileLastModifiedDate(char *path);

#endif
