#ifndef CGI_H_
#define CGI_H_

/*
* Funcion que se encarga de ejecutar un script php o python 
* en un proceso auxiliar, comunicándose con él mediante pipes,
* y devolviendo la salida del script como una cadena de caracteres.
* Parametros:
* 	- path: dirección del archivo a ejecutar
* 	- args: argumentos a pasar al script
* 	- ext: extensión del script a ejecutar, py o php
* Return: Salida del script
*/
char* exec_script(char* path, char* args, char* ext);

#endif
