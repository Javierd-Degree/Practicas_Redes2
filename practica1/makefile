########################################################
CC=gcc
CFLAGS= -g -Wall
LMFLAGS = -lm
LCONFUSEFLAGS = -lconfuse
THREADFLAGS = -pthread
EXS = server
DIRS = directorios
MKDIR_P = mkdir -p
########################################################
OBJECTSSERVER = utils.o http_module.o cgi.a
OBJECTSSERVERDIR = $(BUILD)/utils.o $(BUILD)/http_module.o $(LIB)/cgi.a
########################################################

SRC = ./src
SRCL = ./srclib
INCL = ./includes
LIB = ./lib
BUILD = ./builds

all: $(DIRS) $(EXS)

directorios: $(BUILD) $(LIB)

$(LIB):
	$(MKDIR_P) $(LIB)

$(BUILD):
	$(MKDIR_P) $(BUILD)

server: $(OBJECTSSERVER)
	$(CC) $(CFLAGS) -I./includes -o server $(SRC)/server.c $(OBJECTSSERVERDIR) $(LMFLAGS) $(THREADFLAGS) $(LCONFUSEFLAGS)

utils.o: $(SRC)/utils.c $(INCL)/utils.h
	$(CC) $(CFLAGS) -I./includes -c -o $(BUILD)/utils.o $(SRC)/utils.c $(LCONFUSEFLAGS)

http_module.o: $(SRC)/http_module.c $(INCL)/http_module.h
	$(CC) $(CFLAGS) -I./includes -c -o $(BUILD)/http_module.o $(SRC)/http_module.c

cgi.o: $(SRCL)/cgi.c $(INCL)/cgi.h
	$(CC) $(CFLAGS) -I./includes -c -o $(BUILD)/cgi.o $(SRCL)/cgi.c

# Libreria CGI propia
cgi.a: cgi.o
	ar rcs $(LIB)/cgi.a $(BUILD)/cgi.o


clear:
	@echo Eliminando ficheros .o
	if test -d $(BUILD); then rm -r $(BUILD); fi

clean:
	@echo Eliminando ficheros .o .a y $(EXS) 
	rm -rf $(EXS)
	if test -d $(BUILD); then rm -r $(BUILD); fi
	if test -d $(LIB); then rm -r $(LIB); fi