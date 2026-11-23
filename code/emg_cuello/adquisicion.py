"""Lectura del Arduino por USB, y un simulador para probar todo sin hardware.

Protocolo con adquisicion_emg_cuello.ino:
  PC -> '?'   Arduino -> '#LISTO,version=adq-v2,fs=1000,bits=14,vref=5.0,pin=A1'
  PC -> 's'   Arduino -> '#INICIO' y luego bloques de 10 muestras 'n0:a0,a1,...,a9'
              (adq-v1 mandaba una muestra por linea 'n,adc'; tambien se acepta),
              y cada 1000 muestras '#T,n,micros,atrasos'
  PC -> 'x'   Arduino -> '#FIN,<muestras>'
Las lineas 'Bruto:...' que manda en espera se ignoran. Si llegan a mitad de una
grabacion, la placa se reinicio o salio del modo de grabacion.
"""
import collections
import re
import time

import numpy as np

from .config import fase_de_muestra

PATRON_DATO = re.compile(r"^(\d+),(\d+)$")                  # adq-v1
PATRON_BLOQUE = re.compile(r"^(\d+):(\d+(?:,\d+)*)$")         # adq-v2


def parsear(linea):
    """Linea de datos -> [(n, adc), ...]; None si no es una linea de datos."""
    m = PATRON_BLOQUE.match(linea)
    if m:
        n0 = int(m.group(1))
        return [(n0 + i, int(a)) for i, a in enumerate(m.group(2).split(","))]
    m = PATRON_DATO.match(linea)
    if m:
        return [(int(m.group(1)), int(m.group(2)))]
    return None


class ErrorAdquisicion(RuntimeError):
    pass


# --------------------------------------------------------------------- Arduino
class FuenteArduino:
    """Habla con el Arduino por el puerto serie (pyserial)."""

    def __init__(self, puerto, baudios=250000):
        import serial                                   # pyserial
        self.ser = serial.Serial(puerto, baudios, timeout=0.5)
        self._buf = b""
        time.sleep(2.0)                                 # por si la placa se reinicia al abrir
        self._vaciar()

    def _vaciar(self):
        self.ser.reset_input_buffer()
        self._buf = b""

    def _escribir(self, texto):
        self.ser.write(texto.encode("ascii"))
        self.ser.flush()

    def leer_linea(self, espera_s=0.5):
        """Una linea sin el salto, o None si en espera_s no llega una linea completa."""
        limite = time.monotonic() + espera_s
        while b"\n" not in self._buf:
            if time.monotonic() > limite:
                return None
            trozo = self.ser.read(max(1, self.ser.in_waiting))
            if trozo:
                self._buf += trozo
                if len(self._buf) > 20000:              # basura sin saltos de linea
                    self._buf = b""
        linea, self._buf = self._buf.split(b"\n", 1)
        return linea.decode("ascii", errors="ignore").strip()

    def saludo(self, intentos=8):
        """Pregunta '?' hasta recibir '#LISTO,...'. Regresa el diccionario de campos."""
        self._escribir("x")
        time.sleep(0.2)
        self._vaciar()
        for _ in range(intentos):
            self._escribir("?")
            limite = time.monotonic() + 0.6
            while time.monotonic() < limite:
                linea = self.leer_linea()
                if linea and linea.startswith("#LISTO"):
                    return dict(p.split("=", 1) for p in linea.split(",")[1:] if "=" in p)
        raise ErrorAdquisicion("El Arduino no contesto '#LISTO'. Revisen el puerto, que el "
                               "sketch sea adquisicion_emg_cuello.ino y que el Serial Monitor "
                               "del IDE este CERRADO.")

    def iniciar(self):
        self._escribir("x")
        time.sleep(0.1)
        self._vaciar()
        self._escribir("s")

    def detener(self):
        self._escribir("x")
        limite = time.monotonic() + 2.0
        while time.monotonic() < limite:
            linea = self.leer_linea()
            if linea and linea.startswith("#FIN"):
                break
        self._vaciar()

    def cerrar(self):
        try:
            self._escribir("x")
        finally:
            self.ser.close()


def buscar_puerto():
    """Puertos que parecen un Arduino. Regresa una lista de (puerto, descripcion)."""
    from serial.tools import list_ports
    candidatos = []
    for p in list_ports.comports():
        texto = f"{p.device} {p.description} {p.manufacturer or ''}".lower()
        if any(k in texto for k in ("arduino", "usbmodem", "ttyacm", "usbserial", "ch340",
                                    "cp210", "espressif", "usb jtag")):
            candidatos.append((p.device, p.description))
    return candidatos


# ------------------------------------------------------------------- Simulador
class FuenteSimulada:
    """Imita al Arduino (adq-v2) con una senal inventada. SOLO para probar el codigo.

    Los archivos simulados van a data/simulado/ y nunca a data/raw/.
    amplitudes: desviacion en cuentas del ADC por fase (inventadas para la prueba).
    perder: probabilidad de perder una linea completa (10 muestras).
    cortar_en: muestra en la que el enlace se detiene (para probar los errores).
    bruto_tras_corte: despues del corte manda 'Bruto:...', como una placa reiniciada.
    """
    AMPLITUDES = {"rest": 12, "warning": 15, "move": 160, "between": 40, "down": 110}

    def __init__(self, plan, fs=1000, rapido=False, semilla=0, perder=0.0, offset=8192,
                 cortar_en=None, bruto_tras_corte=False):
        self.plan, self.fs, self.rapido = plan, fs, rapido
        self.rng = np.random.default_rng(semilla)
        self.perder, self.offset = perder, offset
        self.cortar_en, self.bruto_tras_corte = cortar_en, bruto_tras_corte
        self.cola = collections.deque()
        self.transmitiendo = False

    def saludo(self):
        return {"version": "simulador", "fs": str(self.fs), "bits": "14", "vref": "5.0"}

    def iniciar(self):
        self.n, self.t0, self.bloque = 0, time.monotonic(), []
        self.transmitiendo = True
        self.cola.append("#INICIO")

    def _generar(self, hasta):
        while self.n < hasta:
            if self.cortar_en is not None and self.n >= self.cortar_en:
                if self.bruto_tras_corte:
                    self.cola.append("Bruto:0.021,Sin60:0.010,SinArm:0.009")
                return
            fase = fase_de_muestra(self.plan, self.n)
            t = self.n / self.fs
            valor = (self.offset + self.rng.normal(0, self.AMPLITUDES.get(fase, 12))
                     + 25 * np.sin(2 * np.pi * 60 * t))
            if self.n % 1000 == 0:
                self.cola.append(f"#T,{self.n},{int(1e6 * t) + 123456},0")
            self.bloque.append(int(np.clip(round(valor), 0, 16383)))
            self.n += 1
            if len(self.bloque) == 10:
                if self.rng.random() >= self.perder:
                    self.cola.append(f"{self.n - 10}:" + ",".join(map(str, self.bloque)))
                self.bloque = []

    def leer_linea(self):
        if not self.cola and self.transmitiendo:
            hasta = self.n + 50 if self.rapido else int((time.monotonic() - self.t0) * self.fs)
            self._generar(hasta)
            if not self.cola and not self.rapido:
                time.sleep(0.002)
        return self.cola.popleft() if self.cola else None

    def detener(self):
        self.transmitiendo = False
        self.cola.clear()

    def cerrar(self):
        pass


# ------------------------------------------------------------------- Captura
def _diagnostico(ultimo_n, fs, vio_bruto, ignoradas, ultima_rara):
    donde = f"en la muestra {ultimo_n + 1} ({(ultimo_n + 1) / fs:.1f} s)"
    if ultimo_n < 0:
        return ("El Arduino no mando ningun dato despues de 's'. Revisen que el sketch "
                "sea adquisicion_emg_cuello.ino (adq-v2).")
    if vio_bruto:
        return (f"El Arduino dejo de mandar datos {donde} y volvio a mandar 'Bruto:...': "
                "la placa se reinicio o salio del modo de grabacion. Revisen el cable USB "
                "(directo a la compu, sin hub) y que nada mas use el puerto.")
    if ignoradas:
        return (f"El Arduino dejo de mandar datos validos {donde}. Llegaron {ignoradas} "
                f"lineas danadas (ultima: {ultima_rara!r}): se pierden bytes en el enlace USB.")
    return (f"El Arduino dejo de mandar datos {donde} y no llego nada mas: el enlace USB "
            "se detuvo. Corran 'grabar.py --probar-enlace' y manden el resultado.")


def capturar(fuente, plan, fs, al_cambiar_fase=None, al_avanzar=None, espera_max_s=3.0):
    """Graba un intento completo siguiendo el plan de fases.

    Las fases se asignan con el CONTADOR del Arduino, no con el reloj de la PC,
    asi la etiqueta de cada muestra coincide con la senal aunque la PC se atrase.
    Si en espera_max_s no llega ninguna muestra valida, se detiene con un
    ErrorAdquisicion que explica que paso (nunca se queda congelado).
    Regresa un diccionario con n, adc, phase, marcas de tiempo y atrasos.
    """
    total = plan[-1][2]
    inicios = {inicio: nombre for nombre, inicio, _ in plan}
    n_lista, adc_lista, marcas = [], [], []
    atrasos, ignoradas, ultimo_n, siguiente = 0, 0, -1, 0
    vio_bruto, ultima_rara, terminado = False, "", False
    fuente.iniciar()
    ultimo_dato = time.monotonic()
    try:
        while not terminado and ultimo_n < total - 1:
            if time.monotonic() - ultimo_dato > espera_max_s:
                raise ErrorAdquisicion(_diagnostico(ultimo_n, fs, vio_bruto, ignoradas,
                                                    ultima_rara))
            linea = fuente.leer_linea()
            if linea is None:
                continue
            muestras = parsear(linea)
            if muestras is not None:
                ultimo_dato = time.monotonic()
                for n, adc in muestras:
                    if n >= total:
                        terminado = True
                        break
                    while siguiente <= n:             # avisar cada fase al cruzar su inicio
                        if siguiente in inicios and al_cambiar_fase:
                            al_cambiar_fase(inicios[siguiente])
                        siguiente += 1
                    n_lista.append(n)
                    adc_lista.append(adc)
                    ultimo_n = n
                    if al_avanzar and n % 250 == 0:
                        al_avanzar(n)
            elif linea.startswith("#T,"):
                partes = linea.split(",")
                marcas.append((int(partes[1]), int(partes[2])))
                if len(partes) > 3:
                    atrasos = int(partes[3])
            elif linea.startswith("Bruto:"):
                vio_bruto = vio_bruto or ultimo_n >= 0
            elif not linea.startswith("#INICIO"):
                ignoradas += 1
                ultima_rara = linea[:60]
    finally:
        fuente.detener()
    n_arr = np.array(n_lista, dtype=np.int64)
    return {"n": n_arr, "adc": np.array(adc_lista, dtype=np.int64),
            "phase": [fase_de_muestra(plan, k) for k in n_arr],
            "marcas": marcas, "atrasos": atrasos, "ignoradas": ignoradas}
