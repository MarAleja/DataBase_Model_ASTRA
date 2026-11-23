"""Senales de audio para la persona: cuando mira arriba no ve la pantalla.

Tonos (por defecto, funcionan en macOS, Windows y Linux):
  inicio   1 tono grave corto       empieza la grabacion (reposo)
  aviso    1 tono agudo corto       preparate
  arriba   1 tono largo             sube la cabeza y sostenla
  regreso  2 tonos graves           regresa a neutro y relaja
  abajo    3 tonos cortos           solo en el piloto: baja la barbilla
Con --voz (solo macOS) ademas se dice la palabra con el comando 'say'.
"""
import platform
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np

SR = 22050
_TONOS = {  # fase: lista de (frecuencia Hz, duracion s, silencio despues s)
    "rest": [(440, 0.12, 0.0)],
    "warning": [(1000, 0.15, 0.0)],
    "move": [(700, 0.60, 0.0)],
    "between": [(500, 0.12, 0.08), (500, 0.12, 0.0)],
    "down": [(850, 0.10, 0.07), (850, 0.10, 0.07), (850, 0.10, 0.0)],
}
PALABRAS = {"rest": "reposo", "warning": "prepárate", "move": "arriba",
            "between": "regresa", "down": "abajo"}


def _onda(partes):
    trozos = []
    for f, dur, pausa in partes:
        t = np.arange(int(SR * dur)) / SR
        env = np.minimum(1.0, np.minimum(t, dur - t) / 0.01)    # sin chasquidos
        trozos += [0.5 * np.sin(2 * np.pi * f * t) * env, np.zeros(int(SR * pausa))]
    return (np.concatenate(trozos) * 32767).astype(np.int16)


def escribir_wav(ruta, muestras):
    with wave.open(str(ruta), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(muestras.tobytes())


class Sonidos:
    def __init__(self, activo=True, voz=False):
        self.sistema = platform.system()
        self.activo = activo
        self.voz = voz and self.sistema == "Darwin" and shutil.which("say") is not None
        self.voz_es = self._buscar_voz_es() if self.voz else None
        self.carpeta = Path(tempfile.mkdtemp(prefix="cues_emg_"))
        self.archivos = {}
        for fase, partes in _TONOS.items():
            ruta = self.carpeta / f"{fase}.wav"
            escribir_wav(ruta, _onda(partes))
            self.archivos[fase] = ruta
        self.reproductor = self._buscar_reproductor()
        if self.activo and self.reproductor is None and self.sistema != "Windows":
            print("Aviso: no encontre un reproductor de audio (afplay/aplay/paplay). "
                  "Las senales seran solo en pantalla.")

    def _buscar_reproductor(self):
        for cmd in (["afplay"], ["paplay"], ["aplay", "-q"]):
            if shutil.which(cmd[0]):
                return cmd
        return None

    def _buscar_voz_es(self):
        try:
            salida = subprocess.run(["say", "-v", "?"], capture_output=True, text=True,
                                    timeout=5).stdout
        except Exception:
            return None
        for linea in salida.splitlines():
            if "es_MX" in linea or "es_ES" in linea or "es_US" in linea:
                return linea.split()[0]
        return None

    def tocar(self, fase):
        """Reproduce la senal de una fase sin detener la lectura del Arduino."""
        if not self.activo or fase not in self.archivos:
            return
        ruta = str(self.archivos[fase])
        try:
            if self.sistema == "Windows":
                import winsound
                winsound.PlaySound(ruta, winsound.SND_FILENAME | winsound.SND_ASYNC)
            elif self.reproductor:
                subprocess.Popen(self.reproductor + [ruta], stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
            if self.voz:
                cmd = ["say"] + (["-v", self.voz_es] if self.voz_es else []) + [PALABRAS[fase]]
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:                       # el audio nunca detiene la grabacion
            print(f"(audio no disponible: {e})")
