import numpy as np
import cv2
import random
import glob
import math

#
# Añade canal alpha de un frame OpenCV
# Salida:
#   frame con canal alpha añadido si no lo tenía, mismo frame si sí lo tenía.
#
def verify_alpha_channel(frame):
    try:
        frame.shape[3] # looking for the alpha channel
    except IndexError:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)
    return frame

#
# Modifica la saturación hue de un frame OpenCV
# Entrada:
#   - frame: frame a modificar
#   - alpha: valor alpha a establecer
# Salida:
#   Frame modificado
#
def apply_hue_saturation(frame, alpha):
    hsv_image = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv_image)
    s.fill(199)
    v.fill(255)
    hsv_image = cv2.merge([h, s, v])

    out = cv2.cvtColor(hsv_image, cv2.COLOR_HSV2BGR)
    frame = verify_alpha_channel(frame)
    out = verify_alpha_channel(out)
    cv2.addWeighted(out, 0.25, frame, 1.0, .23, frame)
    return frame

#
# Sobrepone un color a un frame OpenCV
# Entrada:
#   - frame: frame a modificar
#   - intensidad: intensidad del color a establecer
#   - blue: valor del color azul de 0 a 255
#   - green: valor del color verde de 0 a 255
#   - red: valor del color rojo de 0 a 255
# Salida
#   Frame modificado
#
def apply_color_overlay(frame, intensity=0.5, blue=0, green=0, red=0):
    frame = verify_alpha_channel(frame)
    frame_h, frame_w, frame_c = frame.shape
    sepia_bgra = (blue, green, red, 1)
    overlay = np.full((frame_h, frame_w, 4), sepia_bgra, dtype='uint8')
    cv2.addWeighted(overlay, intensity, frame, 1.0, 0, frame)
    return frame

#
# Aplica un filtro sepia a un frame OpenCV
# Entrada:
#   - frame: frame a modificar
#   - intensidad: intensidad del filtro sepia a establecer
# Salida
#   Frame modificado
#
def apply_sepia(frame, intensity=0.5):
    frame = verify_alpha_channel(frame)
    frame_h, frame_w, frame_c = frame.shape
    sepia_bgra = (20, 66, 112, 1)
    overlay = np.full((frame_h, frame_w, 4), sepia_bgra, dtype='uint8')
    cv2.addWeighted(overlay, intensity, frame, 1.0, 0, frame)
    return frame

#
# Función auxiliar que combina dos frames OpenCV mediante una máscara
# Entrada:
#   - frame_1: frame 1 a combinar
#   - frame_2: frame 2 a combinar
#   - mask: mascara a usar para combinar
# Salida
#   Frame modificado
#
def alpha_blend(frame_1, frame_2, mask):
    alpha = mask/255.0 
    blended = cv2.convertScaleAbs(frame_1*(1-alpha) + frame_2*alpha)
    return blended

#
# Función que aplica un desenfoque a todo el frame excepto al centro.
# Entrada:
#   - frame: frame a modificar
#   - intensidad: intensidad del desenfoque a aplicar
# Salida
#   Frame modificado
#
def apply_circle_focus_blur(frame, intensity=0.2):
    frame = verify_alpha_channel(frame)
    frame_h, frame_w, frame_c = frame.shape
    y = int(frame_h/2)
    x = int(frame_w/2)

    mask = np.zeros((frame_h, frame_w, 4), dtype='uint8')
    cv2.circle(mask, (x, y), int(y/2), (255,255,255), -1, cv2.LINE_AA)
    mask = cv2.GaussianBlur(mask, (21,21),11 )

    blured = cv2.GaussianBlur(frame, (21,21), 11)
    blended = alpha_blend(frame, blured, 255-mask)
    frame = cv2.cvtColor(blended, cv2.COLOR_BGRA2BGR)
    return frame

#
# Función que invierte los colores de un frame OpenCV.
# Entrada:
#   - frame: frame a modificar
# Salida
#   Frame modificado
#
def apply_invert(frame):
    return cv2.bitwise_not(frame)

#
# Filtro que devuelve el frame sin modificar.
# Salida:
#   Frame modificado
#
def apply_none(frame):
    return frame

#
# Estructura que define los filtros disponibles para la aplicación.
#
FILTERS = {'Ninguno' : apply_none,
            'Sepia' : apply_sepia,
            'Invertido' : apply_invert,
            'Borroso' : apply_circle_focus_blur,
            'Verde' : lambda x: apply_color_overlay(x, green=255),
            'Azul' : lambda x: apply_color_overlay(x, blue=255),
            'Rojo' : lambda x: apply_color_overlay(x, red=255)}