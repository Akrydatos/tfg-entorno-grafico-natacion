import cv2
import csv
import numpy as np
import tkinter as tk

VIDEO_PATH = "video.mp4"
CSV_PATH = "analisis_completo.csv"

# ===== RESOLUCION PANTALLA =====
def get_screen_resolution():
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
    return cv2.resize(frame, (int(w*scale), int(h*scale)))

# ===== CONFIG =====
NOMBRES = {
    11: "Hombro_Izq", 12: "Hombro_Der",
    13: "Codo_Izq",   14: "Codo_Der",
    15: "Mano_Izq",   16: "Mano_Der",
    23: "Cadera_Izq", 24: "Cadera_Der",
    25: "Rodilla_Izq",26: "Rodilla_Der",
    27: "Tobillo_Izq",28: "Tobillo_Der"
}

# ===== CARGAR CSV =====
data = []
with open(CSV_PATH, newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        data.append(row)

total_frames = len(data)

# ===== EXTRAER DISTANCIAS =====
distancias = []

for row in data:
    try:
        d = float(row["dist_signo"])
        distancias.append(None if d == -1 else d)
    except:
        distancias.append(None)

# ===== SUAVIZADO =====
def suavizar(signal, window=5):
    smoothed = []
    for i in range(len(signal)):
        vals = []
        for j in range(i-window, i+window+1):
            if 0 <= j < len(signal) and signal[j] is not None:
                vals.append(signal[j])
        smoothed.append(np.mean(vals) if vals else None)
    return smoothed

dist_suave = suavizar(distancias, window=5)

# ===== DETECCION CONTACTO (MINIMO REAL) =====
# Buscamos el primer frame donde dist_signo es más cercana a 0
frame_contacto = None

valid_vals = [(i, d) for i, d in enumerate(distancias) if d is not None]

if valid_vals:
    # Ordenamos por cercanía a 0 y cogemos el primero cronológicamente
    # entre los que estén dentro de los 10 más cercanos a 0
    por_cercania = sorted(valid_vals, key=lambda x: abs(x[1]))
    umbral = abs(por_cercania[0][1]) * 2  # margen del doble del mínimo absoluto
    candidatos = [i for i, d in valid_vals if abs(d) <= umbral]

    if candidatos:
        min_idx = min(candidatos)  # el más temprano cronológicamente
        try:
            frame_contacto = int(float(data[min_idx]["frame"]))
        except:
            frame_contacto = min_idx

print("Frame contacto REAL:", frame_contacto)

# ===== MAIN =====
def main():

    cap = cv2.VideoCapture(VIDEO_PATH)
    frame_id = 0

    while True:

        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
        ret, frame = cap.read()
        if not ret:
            break

        h, w, _ = frame.shape
        row = data[frame_id]

        puntos = [None]*33

        # ===== LANDMARKS =====
        for i in range(33):
            nombre = NOMBRES.get(i, f"p{i}")
            try:
                x = float(row[f"{nombre}_x"])
                y = float(row[f"{nombre}_y"])
            except:
                continue

            if x == -1:
                continue

            px = int(x*w)
            py = int(y*h)

            puntos[i] = (px, py)
            cv2.circle(frame, (px, py), 5, (0,255,0), -1)

        # ===== CONEXIONES =====
        conexiones = [
            (11,13),(13,15),
            (12,14),(14,16),
            (11,12),
            (23,24),
            (11,23),(12,24),
            (23,25),(25,27),
            (24,26),(26,28)
        ]

        for i1,i2 in conexiones:
            if puntos[i1] and puntos[i2]:
                cv2.line(frame, puntos[i1], puntos[i2], (255,0,0),2)

        # ===== INFO =====
        try:
            angulo = float(row["angulo"])
        except:
            angulo = -1

        try:
            dist = float(row["dist_signo"])
        except:
            dist = 0
        
        
        overlay = frame.copy()
        
        cv2.rectangle(overlay, (15, 15), (240, 55), (0,0,0), -1)
        cv2.rectangle(overlay, (15, 55), (240, 95), (0,0,0), -1)
        cv2.rectangle(overlay, (15, 95), (320, 135), (0,0,0), -1)

        cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)


        cv2.putText(frame, f"Angulo: {angulo:.2f}", (20,40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0),2,cv2.LINE_AA)

        cv2.putText(frame, f"Dist: {dist:.2f}", (20,80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255),2,cv2.LINE_AA)

        # CAMBIO 2: mostramos el frame actual en pantalla
        cv2.putText(frame, f"Frame: {frame_id}/{total_frames-1}", (20,120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,165,225), 2, cv2.LINE_AA)

        

        # ===== CONTACTO =====
        if frame_contacto is not None and frame_id == frame_contacto:
            cv2.putText(frame, "CONTACTO REAL", (20,200),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255),3)

        # ===== ESCALADO =====
        frame_show = escalar_frame(frame)
        cv2.imshow("Analisis PRO", frame_show)

        key = cv2.waitKey(30) & 0xFF

        if key == ord('d'):
            frame_id = min(frame_id + 1, total_frames-1)
        elif key == ord('a'):
            frame_id = max(frame_id - 1, 0)
        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()