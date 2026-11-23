"""Ventanas de 100 ms y caracteristicas de tiempo y de frecuencia.

Por que 100 ms: es el mismo bloque con el que el Arduino calcula el RMS SinArm
que manda al ESP32. Si el modelo usa el RMS de 100 ms, el ESP32 ya lo recibe.

Tiempo (diapositivas 8 y 10):     MAV, RMS, WL (largo de onda), ZC (cruces por cero)
Frecuencia (diapositiva 10):      MNF (frecuencia media), MDF (frecuencia mediana)
"""
import numpy as np
import pandas as pd


def mav(x):
    """Valor absoluto medio. mav([2, -3, 1, -2]) = 2."""
    return float(np.mean(np.abs(x)))


def rms(x):
    """Raiz del valor cuadratico medio. rms([2, -3, 1, -2]) = 2.121."""
    return float(np.sqrt(np.mean(np.square(x))))


def wl(x):
    """Largo de onda: suma de los saltos entre muestras seguidas."""
    return float(np.sum(np.abs(np.diff(x))))


def zc(x):
    """Cruces por cero: cuantas veces cambia el signo."""
    s = np.signbit(np.asarray(x))
    return int(np.count_nonzero(s[1:] != s[:-1]))


def _espectro(x, fs):
    x = np.asarray(x, dtype=float) - np.mean(x)
    p = np.abs(np.fft.rfft(x)) ** 2
    f = np.fft.rfftfreq(len(x), d=1.0 / fs)
    return f, p


def mnf(x, fs):
    """Frecuencia media, pesada por la potencia."""
    f, p = _espectro(x, fs)
    return float(np.sum(f * p) / np.sum(p)) if np.sum(p) > 0 else 0.0


def mdf(x, fs):
    """Frecuencia mediana: parte la potencia en dos mitades iguales."""
    f, p = _espectro(x, fs)
    if np.sum(p) == 0:
        return 0.0
    acumulada = np.cumsum(p)
    return float(f[np.searchsorted(acumulada, acumulada[-1] / 2.0)])


NOMBRES = ["mav", "rms", "wl", "zc", "mnf", "mdf"]


def caracteristicas(x, fs):
    """Las seis caracteristicas de una ventana, como diccionario."""
    return {"mav": mav(x), "rms": rms(x), "wl": wl(x), "zc": zc(x),
            "mnf": mnf(x, fs), "mdf": mdf(x, fs)}


def segmentos(fases):
    """Tramos seguidos de la misma fase: [(fase, inicio, fin), ...]."""
    fases = list(fases)
    tramos, inicio = [], 0
    for i in range(1, len(fases) + 1):
        if i == len(fases) or fases[i] != fases[inicio]:
            tramos.append((fases[inicio], inicio, i))
            inicio = i
    return tramos


def ventanas(y, fases, fs, largo_ms=100, saltar_s=1.0, clases=None):
    """Corta la senal filtrada en ventanas sin traslape dentro de cada fase util.

    y       senal SinArm (voltios)
    fases   etiqueta de fase de cada muestra ('rest', 'warning', 'move', 'between')
    saltar_s  se descarta el primer tramo de cada fase (filtro asentandose en
            'rest'; tiempo de reaccion y cabeza en movimiento en 'move')
    clases  {'rest': 0, 'move': 1}; las demas fases no dan ventanas
    """
    clases = clases or {"rest": 0, "move": 1}
    largo = int(round(largo_ms * fs / 1000.0))
    salto = int(round(saltar_s * fs))
    filas = []
    for fase, ini, fin in segmentos(fases):
        if fase not in clases:
            continue
        for a in range(ini + salto, fin - largo + 1, largo):
            fila = {"start_sample": a, "phase": fase, "label": clases[fase]}
            fila.update(caracteristicas(y[a:a + largo], fs))
            filas.append(fila)
    return pd.DataFrame(filas, columns=["start_sample", "phase", "label"] + NOMBRES)
