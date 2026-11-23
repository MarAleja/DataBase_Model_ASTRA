"""hacer_video_cue.py - genera cue/cue-video.mp4 con los mismos tiempos y sonidos de grabar.py.

Escrito por el equipo con ayuda de Claude (IA). Lo explica cualquier miembro.

Uso:  python code/hacer_video_cue.py      (necesita ffmpeg instalado)
Si cambian los tiempos en config/config.json, vuelvan a generar el video.
El video documenta lo que la persona ve y oye en cada intento; durante la grabacion
las senales las da grabar.py, sincronizadas con el contador del Arduino.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from emg_cuello.config import RAIZ, cargar_config, fases_intento        # noqa: E402
from emg_cuello.sonidos import SR, _TONOS, _onda, escribir_wav          # noqa: E402

COLORES = {"rest": "0x2e7d32", "warning": "0xf9a825", "move": "0xc62828", "between": "0x1565c0"}
TITULO = {"rest": "REPOSO", "warning": "PREPÁRATE", "move": "ARRIBA", "between": "REGRESA"}
DETALLE = {"rest": "cuello neutro, mira la marca A", "warning": "en un segundo sube la cabeza",
           "move": "sube la cabeza a la marca B y sostenla", "between": "vuelve a la marca A y relaja"}
FUENTES = ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "C:/Windows/Fonts/arialbd.ttf",
           "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]


def buscar_fuente():
    for f in FUENTES:
        if Path(f).exists():
            return f
    salida = subprocess.run(["fc-match", "-f", "%{file}", "sans:bold"], capture_output=True,
                            text=True)
    return salida.stdout.strip() or None


def texto(t):
    return t.replace(":", r"\:").replace("'", r"\'")


def main():
    if not shutil.which("ffmpeg"):
        sys.exit("Necesitan ffmpeg (macOS: brew install ffmpeg).")
    cfg = cargar_config()
    fuente = buscar_fuente()
    fases = fases_intento(cfg)
    tmp = Path(tempfile.mkdtemp(prefix="cue_"))
    # audio: el tono de cada fase al inicio de la fase, silencio el resto
    total = int(SR * sum(s for _, s in fases))
    audio = np.zeros(total, dtype=np.int16)
    inicio = 0
    for fase, seg in fases:
        tono = _onda(_TONOS[fase])
        a = int(SR * inicio)
        audio[a:a + len(tono)] = tono[: max(0, total - a)]
        inicio += seg
    escribir_wav(tmp / "audio.wav", audio)
    # video: un tramo de color por fase, con su nombre y cuenta regresiva
    partes = []
    for i, (fase, seg) in enumerate(fases):
        f = f":fontfile='{fuente}'" if fuente else ""
        dibujo = (f"drawtext=text='{texto(TITULO[fase])}'{f}:fontsize=130:fontcolor=white:"
                  f"x=(w-tw)/2:y=h/2-170,"
                  f"drawtext=text='{texto(DETALLE[fase])}'{f}:fontsize=44:fontcolor=white:"
                  f"x=(w-tw)/2:y=h/2+10,"
                  f"drawtext=text='%{{eif\\:{seg}-t+0.999\\:d}} s'{f}:fontsize=70:"
                  f"fontcolor=white:x=(w-tw)/2:y=h/2+110")
        ruta = tmp / f"p{i}.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                        f"color=c={COLORES[fase]}:s=1280x720:d={seg}:r=30", "-vf", dibujo,
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(ruta)], check=True)
        partes.append(ruta)
    lista = tmp / "lista.txt"
    lista.write_text("".join(f"file '{p}'\n" for p in partes))
    salida = RAIZ / "cue" / "cue-video.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i",
                    str(lista), "-i", str(tmp / "audio.wav"), "-c:v", "copy", "-c:a", "aac",
                    "-shortest", str(salida)], check=True)
    print(f"Listo: {salida.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
