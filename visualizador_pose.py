import cv2
import mediapipe as mp
import csv
import math
import numpy as np
import os

VIDEO_PATH = "video.mp4"
CSV_OUTPUT = "analisis_completo.csv"

mp_pose = mp.solutions.pose

def get_screen_resolution():
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    w = root.winfo_screenwidth()
    h = root.winfo_screenheight()
    root.destroy()
    return w, h

SCREEN_W, SCREEN_H = get_screen_resolution()

def escalar_frame(frame):
    h, w = frame.shape[:2]
    scale = min(SCREEN_W / w, SCREEN_H / h)
    new_w = int(w * scale)
    new_h = int(h * scale)
    frame_resized = cv2.resize(frame, (new_w, new_h))
    return frame_resized, scale

scale_global = 1.0
puntos_agua = []
linea_agua = None

NOMBRES = {
    11: "Hombro_Izq", 12: "Hombro_Der",
    13: "Codo_Izq",   14: "Codo_Der",
    15: "Mano_Izq",   16: "Mano_Der",
    23: "Cadera_Izq", 24: "Cadera_Der",
    25: "Rodilla_Izq", 26: "Rodilla_Der",
    27: "Tobillo_Izq", 28: "Tobillo_Der"
}

def ajustar_linea(puntos, ancho):
    pts = np.array(puntos, dtype=np.float32)
    [vx, vy, x, y] = cv2.fitLine(pts, cv2.DIST_L2, 0, 0.01, 0.01)
    vx, vy, x, y = float(vx), float(vy), float(x), float(y)
    if abs(vx) < 1e-6:
        return (int(x), 0), (int(x), ancho)
    lefty  = int((-x * vy / vx) + y)
    righty = int(((ancho - x) * vy / vx) + y)
    return (0, lefty), (ancho, righty)

# ===== DISTANCIA CORREGIDA =====
# Ahora devuelve píxeles reales perpendiculares a la línea de agua.
# El valor es positivo cuando la mano está por encima de la línea,
# negativo cuando está por debajo, y CERO cuando la toca exactamente.
def distancia_signo(p, a, b):
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    longitud = math.sqrt(dx*dx + dy*dy)
    if longitud == 0:
        return 0.0
    # Producto vectorial normalizado → distancia en píxeles reales
    dist = -((dx * (p[1] - a[1])) - (dy * (p[0] - a[0]))) / longitud
    return dist

def calcular_angulo_vector_linea(p1, p2, a, b):
    v1 = (p2[0]-p1[0], p2[1]-p1[1])
    v2 = (b[0]-a[0],   b[1]-a[1])
    dot  = v1[0]*v2[0] + v1[1]*v2[1]
    mag1 = math.sqrt(v1[0]**2 + v1[1]**2)
    mag2 = math.sqrt(v2[0]**2 + v2[1]**2)
    if mag1 == 0 or mag2 == 0:
        return -1
    cos_val = max(-1.0, min(1.0, dot / (mag1 * mag2)))
    ang = math.degrees(math.acos(cos_val))
    return ang if ang <= 90 else 180 - ang

def elegir_lado(landmarks):
    vis_der = landmarks[16].visibility + landmarks[24].visibility
    vis_izq = landmarks[15].visibility + landmarks[23].visibility
    return (16, 24) if vis_der >= vis_izq else (15, 23)

def clamp(v, minv, maxv):
    return max(minv, min(maxv, v))

def mouse(event, x, y, flags, param):
    global puntos_agua, scale_global
    if event == cv2.EVENT_LBUTTONDOWN:
        real_x = int(x / scale_global)
        real_y = int(y / scale_global)
        puntos_agua.append((real_x, real_y))

def main():
    global linea_agua, scale_global

    cap = cv2.VideoCapture(VIDEO_PATH)
    ret, frame = cap.read()
    if not ret:
        print("Error leyendo video")
        return

    h, w = frame.shape[:2]

    # ===== SELECCIÓN LÍNEA DE AGUA =====
    cv2.namedWindow("Seleccion Agua")
    cv2.setMouseCallback("Seleccion Agua", mouse)

    while True:
        temp = frame.copy()
        for p in puntos_agua:
            cv2.circle(temp, p, 5, (0, 255, 255), -1)
        if len(puntos_agua) >= 2:
            p1, p2 = ajustar_linea(puntos_agua, w)
            cv2.line(temp, p1, p2, (255, 255, 0), 2)
        cv2.putText(temp, "Marca linea agua + ENTER",
                    (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
        temp_scaled, scale = escalar_frame(temp)
        scale_global = scale
        cv2.imshow("Seleccion Agua", temp_scaled)
        key = cv2.waitKey(1) & 0xFF
        if key == 13 and len(puntos_agua) >= 2:
            linea_agua = ajustar_linea(puntos_agua, w)
            break

    cv2.destroyWindow("Seleccion Agua")

    # ===== PROCESADO =====
    # Variable para registrar el ángulo en el frame de contacto
    frame_contacto = None
    angulo_contacto = None
    dist_anterior = None

    if os.path.exists(CSV_OUTPUT):
        os.remove(CSV_OUTPUT)

    with mp_pose.Pose(static_image_mode=False, model_complexity=2) as pose:
        with open(CSV_OUTPUT, "w", newline="") as f:
            writer = csv.writer(f)

            header = ["frame"]
            for i in range(33):
                nombre = NOMBRES.get(i, f"p{i}")
                header += [f"{nombre}_x", f"{nombre}_y", f"{nombre}_vis"]
            header += ["lado", "angulo", "dist_signo", "contacto"]
            writer.writerow(header)

            frame_id = 0
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = pose.process(rgb)

                fila = [frame_id]
                es_contacto = 0

                if results.pose_landmarks:
                    landmarks = results.pose_landmarks.landmark

                    for p in landmarks:
                        fila += [p.x, p.y, p.visibility]

                    idx_mano, idx_cadera = elegir_lado(landmarks)
                    mano   = landmarks[idx_mano]
                    cadera = landmarks[idx_cadera]

                    p_mano   = (clamp(int(mano.x*w),   0, w-1),
                                clamp(int(mano.y*h),   0, h-1))
                    p_cadera = (clamp(int(cadera.x*w), 0, w-1),
                                clamp(int(cadera.y*h), 0, h-1))

                    angulo = calcular_angulo_vector_linea(
                        p_cadera, p_mano, linea_agua[0], linea_agua[1])

                    # Distancia en píxeles reales (0 = contacto exacto)
                    dist = distancia_signo(p_mano, linea_agua[0], linea_agua[1])

                    # ===== DETECCIÓN DE CONTACTO =====
                    # El contacto ocurre cuando la distancia cruza cero:
                    # dist anterior positiva (mano sobre el agua) y
                    # dist actual <= 0 (mano toca o cruza la línea)
                    if dist_anterior is not None and dist_anterior > 0 and dist <= 0:
                        if frame_contacto is None:  # solo el primer cruce
                            frame_contacto  = frame_id
                            angulo_contacto = angulo
                            es_contacto = 1
                            print(f"CONTACTO detectado en frame {frame_id}")
                            print(f"Ángulo de ataque en contacto: {angulo:.2f}°")
                            print(f"Distancia en contacto: {dist:.2f} px")

                    dist_anterior = dist

                    lado = "derecho" if idx_mano == 16 else "izquierdo"
                    fila += [lado, angulo, round(dist, 4), es_contacto]

                    # ===== VISUALIZACIÓN =====
                    for c in mp_pose.POSE_CONNECTIONS:
                        i1, i2 = c
                        x1, y1 = int(landmarks[i1].x*w), int(landmarks[i1].y*h)
                        x2, y2 = int(landmarks[i2].x*w), int(landmarks[i2].y*h)
                        cv2.line(frame, (x1,y1), (x2,y2), (255,0,0), 2)

                    # Segmento cadera-mano en color destacado
                    cv2.line(frame, p_cadera, p_mano, (0, 255, 255), 3)
                    cv2.circle(frame, p_mano,   8, (0, 0, 255), -1)
                    cv2.circle(frame, p_cadera, 8, (0, 255, 0), -1)

                    # Línea de agua
                    cv2.line(frame, linea_agua[0], linea_agua[1], (255,255,0), 2)

                    # Textos informativos
                    cv2.putText(frame, f"Angulo: {angulo:.2f} deg",
                                (20, 40), cv2.FONT_HERSHEY_SIMPLEX,
                                0.7, (0,255,0), 2)
                    cv2.putText(frame, f"Dist agua: {dist:.1f} px",
                                (20, 70), cv2.FONT_HERSHEY_SIMPLEX,
                                0.6, (255,255,255), 2)

                    if es_contacto:
                        cv2.putText(frame, f"CONTACTO  Angulo={angulo:.1f} deg",
                                    (20, 110), cv2.FONT_HERSHEY_SIMPLEX,
                                    0.9, (0,0,255), 3)

                else:
                    # Sin detección: rellenar columnas con -1
                    fila += [-1]*33*3
                    fila += ["ninguno", -1, -1, 0]

                writer.writerow(fila)

                frame_scaled, _ = escalar_frame(frame)
                cv2.imshow("Procesando", frame_scaled)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

                frame_id += 1

    cap.release()
    cv2.destroyAllWindows()

    print("\n===== RESUMEN =====")
    print(f"Total frames procesados: {frame_id}")
    if frame_contacto is not None:
        print(f"Frame de contacto: {frame_contacto}")
        print(f"Ángulo de ataque en contacto: {angulo_contacto:.2f}°")
    else:
        print("No se detectó contacto (la mano no cruzó la línea de agua)")
    print(f"CSV guardado en: {CSV_OUTPUT}")

if __name__ == "__main__":
    main()