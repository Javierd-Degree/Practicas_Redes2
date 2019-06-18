/**************************************************
*	Javier Delgado del Cerro
*	Javier Lopez Cano
*	Pareja 2
*
*	Servidor multihilo.
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

int MAX_CLIENTS;
int SERVER_PORT;

int sockfd;
int numThread = 0;
pthread_attr_t pthread_attr;


/*
* Manjeador de señales para finalizar el proceso cerrando el socket.
*/
void signal_handler(int signal_number) {
	syslog(LOG_INFO, "Cerramos el servidor\n");
    close(sockfd);
    closelog();
    free(SERVER_ROOT);
    free(SERVER_SIGN);
    pthread_attr_destroy(&pthread_attr);
    pthread_exit(0);
}

/*
* Funcion que inicializa un socket TCP con puerto SERVER_PORT
* y maximo numero de clientes MAX_CLIENTS.
* Return: 0 si no hay ningun error, -1 en caso contrario.
*/
int tcp_listen(){
	int sockfd;
	struct sockaddr_in server;

	/*Creamos el socket TCP*/
	if((sockfd = socket(AF_INET, SOCK_STREAM, 0)) == -1){
		syslog(LOG_ERR, "Error en la creación del socket\n");
		return -1;
	}

	/*Inicializamos la estructura de dirección y puerto*/
	server.sin_family = AF_INET;
	server.sin_port = htons(SERVER_PORT);
	server.sin_addr.s_addr = INADDR_ANY;

	/*Ligamos el puerto al socket creado*/
	if(bind(sockfd, (struct sockaddr*)&server, sizeof(server)) == -1){
		syslog(LOG_ERR, "Error al ligar el puerto al socket\n");
		return -1;
	}

	/*Empezamos a escuchar*/
	if(listen(sockfd, MAX_CLIENTS) == -1){
		syslog(LOG_ERR, "Error al comenzar a esuchar\n");
		return -1;
	}

	printf("Escuchando en [%s:%d]...\n", inet_ntoa(server.sin_addr), ntohs(server.sin_port));
	return sockfd;
}

/*
* Funcion que maneja una conexión TCP, respondiendo a una
* peticion HTTP.
* Parametros:
* 	- arg: puntero a un entero con el descriptor de fichero
* 		del socket de la conexión. Hay que liberarlo.
*/
void* socketThread(void *arg){
    int *pointer = (int *) arg;
    int fd = *pointer;
    free(pointer);

    int ret, minor_version;
    char buffer[MAXBUF+1];
    char *method, *path, *body;

    while ((ret = read(fd, buffer, MAXBUF)) == -1 && errno == EINTR);

    /*printf("%d socket %d\n", n, fd);*/

    if(ret == -1) {
        returnError(ERROR_BAD_REQUEST, fd, "Error al leer la peticion. ERROR: %s", strerror(errno));
        close(fd);
        pthread_exit(NULL);
    }else if(ret == 0){
    	returnError(ERROR_BAD_REQUEST, fd, "Error al leer la peticion. 0 bytes leidos. ERROR: %s\n", strerror(errno));
    	close(fd);
    	pthread_exit(NULL);
    }

    buffer[ret] = '\0';

    if(parseRequest(buffer, &method, &path, &minor_version, &body) == -1){
        returnError(ERROR_BAD_REQUEST, fd, "Error al intentar parsear la peticion.");
        close(fd);
        pthread_exit(NULL);
    }

    HTTPResponse(fd, path, method, body, minor_version);

    close(fd);
	pthread_exit(NULL);
}

int main(int argc, char **argv){
	/* Cargamos la configuracion del servidor */
	readServerConfig("server.conf", &MAX_CLIENTS, &SERVER_PORT, &SERVER_ROOT, &SERVER_SIGN);
	
	/* Arrancamos el syslog */
	setlogmask(LOG_UPTO(LOG_INFO));
    openlog(SERVER_SIGN, LOG_CONS | LOG_PID | LOG_NDELAY, LOG_LOCAL3);

	/* Configuramos el signal_handler */
    if ((signal(SIGTERM, signal_handler) == SIG_ERR) ||
    	(signal(SIGINT, signal_handler) == SIG_ERR)) {
        syslog(LOG_ERR, "Error al inicializar el signal_handler\n");
        exit(EXIT_FAILURE);
    }


    /* Hacemos que los hilos sean detached para no tener que hacer join */
    if (pthread_attr_init(&pthread_attr) != 0) {
        syslog(LOG_ERR, "Error al llamar a pthread_attr_init\n");
        exit(EXIT_FAILURE);
    }
    if (pthread_attr_setdetachstate(&pthread_attr, PTHREAD_CREATE_DETACHED) != 0) {
        syslog(LOG_ERR, "Error al llamar a pthread_attr_setdetachstate\n");
        exit(EXIT_FAILURE);
    }

    /* Inicializamos el socket TCP */
	if((sockfd = tcp_listen()) == -1){
		syslog(LOG_ERR, "Error al inicializar el socket TCP");
		free(SERVER_ROOT);
    	free(SERVER_SIGN);
		exit(EXIT_FAILURE);
	}

	syslog(LOG_INFO, "Servidor arrancado\n\tNombre: %s\n\tPuerto %d\n\tMaximo numero de clientes: %d\n\tRuta del servidor: %s\n", SERVER_SIGN, SERVER_PORT, MAX_CLIENTS, SERVER_ROOT);

	while(1){
		pthread_t tid;
		int  *clientfd, fd_aux;
		struct sockaddr_in client_addr;
		unsigned int addrlen = sizeof(client_addr);

		fd_aux = accept(sockfd, (struct sockaddr*)&client_addr, &addrlen);
		if(fd_aux == -1){
			syslog(LOG_ERR, "Error al aceptar la conexion TCP\n");
			continue;
		}

		clientfd = (int *)malloc(sizeof(int));
		if(clientfd == NULL){
			syslog(LOG_ERR, "Error al reservar memoria\n");
			continue;
		}

		*clientfd = fd_aux;
		if(pthread_create(&tid, &pthread_attr, socketThread, (void *)clientfd) == -1){
			syslog(LOG_ERR, "Error al crear el thread\n");
		}

		/*Como el programa corre en un bucle while, no es necesario hacer pthread_join*/
	}

	/* El socket se cierra en el signal_handler */
	exit(EXIT_SUCCESS);
}
