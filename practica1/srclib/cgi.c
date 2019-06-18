
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <fcntl.h>
#include <unistd.h>
#include <syslog.h>

#define MAX_ARGS 20
#define MAX_RET 1024

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
char* exec_script(char* path, char* args, char* ext){

	int pipes[2][2], i, pid;

	/*Inicializamos los pipes*/
	for(i=0; i<2; i++){
		if(pipe(pipes[i]) == -1){
			syslog(LOG_ERR, "Error al inicializar los pipes.\n");
			return NULL;
		}
	}

	/*Creamos el proceso hijo*/
	pid = fork();

	if(pid == -1){
		syslog(LOG_ERR, "Error al crear el hijo\n");
		close(pipes[0][0]);
		close(pipes[0][1]);
		close(pipes[1][0]);
		close(pipes[1][1]);

		return NULL;
	}else if(pid == 0){

		/*PROCESO HIJO*/
		char** final_args;

		/*Cerramos escritura del padre*/
		close(pipes[1][1]);
		/*Cerramos lectura del padre*/
		close(pipes[0][0]);

		/*Redireccionamos el descriptor donde lee el hijo al stdin de modo que cuando el padre*/
		/*escriba en el descriptor de escritura del pipe, esto se escriba en el stdin del hijo*/
		dup2(pipes[1][0], STDIN_FILENO);

		/*Cerramos lectura del hijo pues este va a leer de stdin y no del pipe*/
		close(pipes[1][0]);

		/*Redireccionamos el descriptor donde escribe el hijo al stdout de modo que cuando el hijo*/
		/*escriba en el stdout, esto se escriba tambien en el pipe para que el padre lo pueda leer*/
		dup2(pipes[0][1], STDOUT_FILENO);

		/*Cerramos escritura del hijo pues este escribirá en stdout y no en el pipe*/
		close(pipes[0][1]);

		/*Creamos un char* donde introduciremos los argumentos que se deben pasar al execvp*/
		final_args=(char**)malloc(MAX_ARGS*sizeof(char*));
		if(final_args == NULL){

			exit(EXIT_FAILURE);
		}

		if(strcmp(ext, "php") == 0){
			/*Si el script es PHP*/

			/*Rellenamos las primeras posiciones de final_args con "php" (programa que ejecuta los scripts php),*/
			/* "-f" flag que indoca que el script viene dado como un fichero, y el "path" (fichero del script)*/
			final_args[0] = "php";
			final_args[1] = "-f";
			final_args[2] = path;
			
			/*Rellenamos el resto de final_args con los parametros del script*/

			final_args[3]= args;
			
			/*Completamos final_args con NULL pues debe ser un array terminado en NULL para que execvp se ejecute correctamente*/
			final_args[4] = NULL;

		}else if(strcmp(ext, "py") == 0){
			/*Si el script es Python*/

			/*Rellenamos las primeras posiciones de final_args con "python" (programa que ejecuta los scripts en python),*/
			/*y el "path" (fichero del script), en este caso no se necesita flag pues por defecto "python" espera un fichero*/
			final_args[0] = "python3";
			final_args[1] = path;

			/*Rellenamos el resto de final_args con los parametros del script*/

			final_args[2] = args;

			/*Completamos final_args con NULL pues debe ser un array terminado en NULL para que execvp se ejecute correctamente*/
			final_args[3] = NULL;
			
		}

		/*Ejecutamos execvp con el programa correspondiente para ejecutar el script y los argumentos de este*/
		execvp(final_args[0], final_args);

		/*Liberamos memoria*/
		free(final_args);

		/*El proceso hijo acaba*/
		exit(EXIT_SUCCESS);


	}else {
		/*PROCESO PADRE*/
		int len;
		char *ret, ret_aux[1];

		/*Reservamos memoria para un char* donde guardaremos la salida del script*/
		ret=(char*)malloc(MAX_RET*sizeof(char));
		if(ret == NULL){
			close(pipes[0][0]);
			close(pipes[0][1]);
			close(pipes[1][0]);
			close(pipes[1][1]);
			return NULL;
		}

		/*Cerramos lectura del hijo*/
		close(pipes[1][0]);
		/*Cerramos escritura del hijo*/
		close(pipes[0][1]);

		/*Escribimos en el pipe (y por tanto en el stdin del hijo) los parámetros del script*/
		
		write(pipes[1][1], args, strlen(args)+1);
		write(pipes[1][1], "\n", 1);

		
		/*Esperamos a que el hijo termine su ejecución*/
		wait(NULL);

		/*Creamos una variable para controlar el tamaño de la cadena que se va a retornar*/
		len = MAX_RET;

		/*Leemos del pipe (y por tanto del stdout del hijo) la salida del script y la guardamos en ret*/
		read(pipes[0][0], ret_aux, 1);
		strcpy(ret, ret_aux);
		while(read(pipes[0][0], ret_aux, 1) > 0){
			strcat(ret, ret_aux);

			if(strlen(ret)+1 >= len){
				len = 2*len;
				ret = (char*)realloc(ret, sizeof(char)*len);
			}
		}

		if(strlen(ret)+5 >= len){
			len = len+5;
			ret = (char*)realloc(ret, sizeof(char)*len);
		}

		strcat(ret, "\r\n\r\n");

		/*Cerramos lectura y escritura del padre pues ya no se usaran más*/
		close(pipes[0][0]);
		close(pipes[1][1]);

		/*Devolvemos la salida del script*/
		return ret;
	}
}

/*
* NO USADA
* Funcion auxiliar que, dado un path con los argumentos en el formato establecido,
* se encarga de separarlos en un array de cadenas de caracteres.
* Parametros:
* 	- srt: path con los argumentos
* Return: Array de strings con los argumentos
*/
char** get_args(char* str){

	char** args;
	int i;

	/*Reservamos memoria para el char** donde se almacenarán los argumentos*/
	args = (char**)malloc(MAX_ARGS * sizeof(char*));
	if(args == NULL){
		syslog(LOG_ERR, "Error al reservar memoria.");
		return NULL;
	}

	/*Troceamos el str por la ? haciendo que esta se sustituya por \0 de modo que str contiene ahora solo el path del script*/
	strtok(str, "?");

	/*Troceamos la cadena almacenando los argumentos en args*/
	strtok(NULL, "=&");
	args[0] = strtok(NULL, "=&");

	for(i=1; args[i-1] != NULL; i++){
		strtok(NULL, "=&");
		args[i]= strtok(NULL, "=&");
	}

	/*Devolvemos el char** con los argumentos*/
	return args;
}