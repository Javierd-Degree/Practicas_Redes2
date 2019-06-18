#include <confuse.h>
#include <string.h>
#include <stdio.h>
#include <time.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>
#include <errno.h>
#include "utils.h"

/*
* Funcion que demoniza el proceso que la ejecuta, inicializando syslog.
* Parametros:
*   - servicio: nombre usado en el syslog.
* Return: 0 si no hay ningun error, -1 en caso contrario.
*/
int demonizar(char* servicio){
  /* Creamos un nuevo proceso y destruimos al padre.*/
    int pid = fork();
    if(pid < 0){
        printf("Error al crear el proceso hijo.\n");
        return -1;
    }else if(pid > 0){
        exit(EXIT_SUCCESS);
    }

    /* De nuevo, creamos un nuevo proceso y destruimos al padre.*/
    pid = fork();
    if(pid < 0){
        printf("Error al crear el proceso hijo.\n");
        return -1;
    }else if(pid > 0){
        exit(EXIT_SUCCESS);
    }

    /* Creamos una nueva sesión para el proceso hijo. */
    if(setsid() < 0){
        printf("Error al crear el nuevo SID.\n");
        return -1;
    }

    /* Cambiamos la máscara de permisos del hijo. */
    umask(0);

    /* Cambiamos el directorio de trabajo al directorio raíz. */
    if(chdir("/") < 0){
        printf("Error al cambiar el directorio de trabajo.\n");
        return -1;
    }

    /* Abrimos los logs. */
    setlogmask(LOG_UPTO(LOG_INFO));
    openlog(servicio, LOG_CONS | LOG_PID | LOG_NDELAY, LOG_LOCAL3);
    syslog(LOG_ERR, "Iniciando nuevo servidor.");
    syslog(LOG_INFO, "Cerrando descriptores de fichero.");

    /* Cerramos los descriptores. */
    close(STDIN_FILENO);
    close(STDOUT_FILENO);
    close(STDERR_FILENO);

    return 0;
}

/*
* Funcion que lee los parametros de configuracion del servidor.
* Parametros:
*   - src: direccion del archivo que contiene la configuracion.
*   - clients: puntero a entero donde almacenar el numero maximo de clientes
*   - port: puntero a entero donde almacenar el puerto del servidor
*   - root: puntero a string donde almacenar la raiz de los archivos del servidor
*   - name: puntero a string donde almacenar el nombre del servidor
* Return: 0 si no hay ningun error, -1 en caso contrario.
*/
int readServerConfig(char *src, int *clients, int *port, char **root, char **name){
  long int clients_aux, port_aux;

    cfg_opt_t opts[] = {
        CFG_SIMPLE_STR("server_root", root),
        CFG_SIMPLE_STR("server_signature", name),
        CFG_SIMPLE_INT("max_clients", &clients_aux),
        CFG_SIMPLE_INT("listen_port", &port_aux),
        CFG_END()
    };
    cfg_t *cfg;

    /* Set default value for the server option */
    *root = strdup("httpfiles/");
    *name = strdup("Redes2Server");
    port_aux = 8888;
    clients_aux = 10;


    cfg = cfg_init(opts, 0);
    cfg_parse(cfg, src);

    *clients = (int)clients_aux;
    *port = (int)port_aux;

    cfg_free(cfg);
    return 0;
}

/*
* Funcion auxiliar que formatea una estructura tm en un string.
* Return: la fecha y hora almacenada en la estructura tm con el
*           formato usado por html.
*/
char *formatGMTime(struct tm tm){
    char buf[1000];
    char *result;

    strftime(buf, sizeof(buf), "%a, %d %b %Y %H:%M:%S %Z", &tm);

    result = (char *)malloc(sizeof(char)*(strlen(buf)+1));
    strcpy(result, buf);
    return result;
}

/*
* Funcion que devuelve la fecha actual en el formato usado por HTTP
* Return: char* con memoria reservada que incluye la fecha actual.
*/
char* getCurrentDate() {
    time_t now;

    now = time(0);
    return formatGMTime(*gmtime(&now));
}


/*
* Funcion que devuelve la fecha de ultima modificacion de un archivo 
* en el formato usado por HTTP
* Parametros:
*   - path: direccion del archivo
* Return: char* con memoria reservada que incluye la fecha de ultima 
* modificacion del archivo path.
*/
char* getFileLastModifiedDate(char *path){
    struct stat attr;
    if(stat(path, &attr) == -1){
        return NULL;
    }

    return formatGMTime(*gmtime(&(attr.st_mtime)));
}