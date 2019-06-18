import filesGestion as fg
import crypt as cr
import identityGestion as ig
import argparse as arg
import os


# Funcion que lee los argumenos del terminal, los parsea y llama a las funciones necesarias
# para llevar a cabo la funcionalidad del programa.
#
def leer():

    parser = arg.ArgumentParser(description = 'Possible actions:')
    parser.add_argument("--create_id", nargs = '*',  help = 'Crear una nueva identidad y un par de claves en el servidor.')
    parser.add_argument("--search_id", nargs = 1, metavar = ('cadena'), help = 'Buscar el id de un usuario cuya informacion contenga una cadena determinada.')
    parser.add_argument("--delete_id", nargs = 1, metavar = ('user_id'), help = 'Borrar el usuario con el id especificado.')
    parser.add_argument("--upload", nargs = 1, metavar = ('fichero'), help = 'Subir un fichero.')
    parser.add_argument("--upload_files", nargs = '*', help = 'Subir varios ficheros para un mismo destinatario.')
    parser.add_argument("--list_files", action = 'store_true', help = 'Obtener una lista con todos los ficheros disponibles.')
    parser.add_argument("--download", nargs = 1, metavar = ('id_fichero'), help = 'Descargar el fichero con el id especificado, se debe especificar el id del emisor con --source_id.')
    parser.add_argument("--download_files", nargs = '*', help = 'Descargar varios ficheros con los ids especificados provenientes del mismo emisor cuyo id se especifica con --source_id.')
    parser.add_argument("--delete_file", nargs = 1, metavar = ('id_fichero'), help = 'Eliminar el fichero con el id especificado.')
    parser.add_argument("--delete_files", nargs = '*', help = 'Eliminar varios ficheros con los ids especificados.')
    parser.add_argument("--encrypt", nargs = 1, metavar = ('fichero'), help = 'Encriptar el fichero especificado, se debe especificar el id del destinatario con --dest_id.')
    parser.add_argument("--encrypt_files", nargs = '*', help = 'Encriptar varios ficheros para el mismo destinatario cuyo id es especificado con --dest_id.')
    parser.add_argument("--decrypt", nargs = 1, metavar = ('fichero'), help = 'Desencripta el fichero especificado.')
    parser.add_argument("--decrypt_files", nargs = '*', help = 'Desencripta los ficheros especificados.')
    parser.add_argument("--sign", nargs = 1, metavar = ('fichero'), help = 'Firmar un archivo con la clave privada.')
    parser.add_argument("--sign_files", nargs = '*', help = 'Firmar varios archivo con la clave privada.')
    parser.add_argument("--check_sign", nargs = 1, metavar = ('fichero'), help = 'Comprueba la firma de un archivo, debe indicarse el ID del emisor con --source_id.')
    parser.add_argument("--check_sign_files", nargs = '*', help = 'Comprueba la firma de varios archivos de un mismo emisor, debe indicarse el ID del emisor con --source_id.')
    parser.add_argument("--enc_sign", nargs = 1, metavar = ('fichero'), help = 'Encriptar y firmar un archivo, se debe especificar el id del receptor con --dest_id.')
    parser.add_argument("--enc_sign_files", nargs = '*', help = 'Encriptar y firmar varios archivos para el mismo receptor, se debe especificar el id del receptor con --dest_id.')
    parser.add_argument("--decrypt_check", nargs = 1, metavar = ('fichero'), help = 'desencripta y verifica la firma de un archivo, se debe especificar el id delemisor con --source_id.')
    parser.add_argument("--decrypt_check_files", nargs = '*', help = 'desencripta y verifica la firma de varios archivos de un mismo emisor, se debe especificar el id delemisor con --source_id.')
    parser.add_argument("--source_id", nargs = 1, metavar = ('user_id'), help = 'Id del emisor del fichero.')
    parser.add_argument("--dest_id", nargs = 1, metavar = ('user_id'), help = 'Id del receptor del fichero.')

    args = parser.parse_args()

    directorio = "./.files/"
    try:
      os.stat(directorio)
    except:
      os.mkdir(directorio)

    directorio = "./encriptado/"
    try:
      os.stat(directorio)
    except:
      os.mkdir(directorio)

    directorio = "./downloads/"
    try:
      os.stat(directorio)
    except:
      os.mkdir(directorio)


    if args.create_id:
        if args.create_id[0] and args.create_id[1]:
            print('Solicitando nuevo usuario a SecureBox.')
            cr.userRegister(args.create_id[0], args.create_id[1])
            print('Usuario creado correctamente.')
        else:
            print("Faltan argumentos, usa -h para ayuda.")

    if args.search_id:
        print(ig.userSearch(args.search_id[0]))

    if args.delete_id:
        ig.userDelete(args.delete_id[0])

    if args.upload:
        if args.dest_id:
            path = cr.cifrar_firmar(args.upload[0], args.dest_id[0])
            print('Solicitando subida de fichero a SecureBox')
            fg.uploadFile(path)
            print('Subida realizada correctamente.')
        else:
            print("Es necesario especificar el id del receptor con --dest_id.\n Usa -h para ayuda.")

    if args.upload_files:
        if args.dest_id:
            print('Solicitando subida de ficheros a SecureBox')
            for i in args.upload_files:
                print('Subiendo fichero ' + i)
                path = cr.cifrar_firmar(i, args.dest_id[0])
                fg.uploadFile(path)
            print('Subida realizada correctamente.')
        else:
            print("Es necesario especificar el id del receptor con --dest_id.\n Usa -h para ayuda.")

    if args.list_files:
        print(fg.fileList())

    if args.download:
        if args.source_id:
            file = fg.fileDownload(args.download[0], args.source_id[0])
            file = cr.desencriptar(file)
            if cr.check_signature(file,  args.source_id[0]):
                print('OK')
                print('Fichero descargado y verificado correctamente.')
            else:
                print("Error: El archivo ha sido modificado o no ha sido crado por el usuario especificado por --source_id, no se ha podido descargar correctamente.")

        else:
             print("Es necesario especificar el id del emisor con --source_id.\n Usa -h para ayuda.")

    if args.download_files:
        if args.source_id:
            for i in args.download_files:
                print('Fichero ' + i)
                file = fg.fileDownload(i, args.source_id[0])
                file = cr.desencriptar(file)
                if cr.check_signature(file,  args.source_id[0]):
                    print('OK')
                    print('Fichero descargado y verificado correctamente.')
                else:
                    print("Error: El archivo ha sido modificado o no ha sido crado por el usuario especificado por --source_id, no se ha podido descargar correctamente.")
        else:
            print("Es necesario especificar el id del emisor con --source_id.\n Usa -h para ayuda.")

    if args.delete_file:
        fg.fileDelete(args.delete_file[0])

    if args.delete_files:
        for i in args.delete_files:
            print('Fichero ' + i)
            fg.fileDelete(i)

    if args.encrypt:
        if args.dest_id:
            cr.encriptar(args.encrypt[0], args.dest_id[0])
        else:
            print("Es necesario especificar el id del receptor con --dest_id.\n Usa -h para ayuda.")

    if args.encrypt_files:
        if args.dest_id:
            for i in args.encrypt_files:
                print('Fichero ' + i)
                cr.encriptar(i, args.dest_id[0])
        else:
            print("Es necesario especificar el id del receptor con --dest_id.\n Usa -h para ayuda.")

    if args.decrypt:
        cr.desencriptar(args.decrypt[0])

    if args.decrypt_files:
        for i in args.decrypt_files:
            print('Fichero ' + i)
            cr.desencriptar(i)

    if args.sign:
        cr.firmar(args.sign[0])

    if args.sign_files:
        for i in args.sign_files:
            print('Fichero ' + i)
            cr.firmar(i)

    if args.check_sign:
        if args.source_id:
            if cr.check_signature(args.check_sign[0],  args.source_id[0]):
                print('OK')
                print('Fichero descargado y verificado correctamente.')
            else:
                print("Error: El archivo ha sido modificado o no ha sido crado por el usuario especificado por --source_id.")
        else:
            print("Es necesario especificar el id del emisor con --source_id.\n Usa -h para ayuda.")

    if args.check_sign_files:
        if args.source_id:
            for i in args.check_sign_files:
                print('Fichero ' + i)
                if cr.check_signature(i,  args.source_id[0]):
                    print('OK')
                    print('Fichero verificado correctamente.')
                else:
                    print("Error: El archivo ha sido modificado o no ha sido crado por el usuario especificado por --source_id.")
        else:
            print("Es necesario especificar el id del emisor con --source_id.\n Usa -h para ayuda.")

    if args.enc_sign:
        if args.dest_id:
            cr.cifrar_firmar(args.enc_sign[0], args.dest_id[0])
        else:
            print("Es necesario especificar el id del receptor con --dest_id.\n Usa -h para ayuda.")

    if args.enc_sign_files:
        if args.dest_id:
            for i in args.enc_sign_files:
                print('Fichero ' + i)
                cr.cifrar_firmar(i, args.dest_id[0])
        else:
            print("Es necesario especificar el id del receptor con --dest_id.\n Usa -h para ayuda.")

    if args.decrypt_check:
        if args.source_id:
            file = cr.desencriptar(args.decrypt_check[0])
            if cr.check_signature(file,  args.source_id[0]):
                print('OK')
                print('Fichero verificado correctamente.')
            else:
                print("Error: El archivo ha sido modificado o no ha sido crado por el usuario especificado por --source_id.")
        else:
            print("Es necesario especificar el id del emisor con --source_id.\n Usa -h para ayuda.")

    if args.decrypt_check_files:
        if args.source_id:
            for i in args.decrypt_check_files:
                print('Fichero ' + i)
                file = cr.desencriptar(i)
                if cr.check_signature(file, args.source_id[0]):
                    print('OK')
                    print('Fichero verificado correctamente.')
                else:
                    print("Error: El archivo ha sido modificado o no ha sido crado por el usuario especificado por --source_id.")
        else:
            print("Es necesario especificar el id del emisor con --source_id.\n Usa -h para ayuda.")




leer()
