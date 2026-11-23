"""De un archivo crudo a ventanas con caracteristicas, y de metadata a una tabla."""
import numpy as np
import pandas as pd

from .caracteristicas import segmentos, ventanas
from .datos import leer_registro, ruta_de_fila
from .filtros import adc_a_voltios, sinarm_desde_config


def senal_sinarm(df_registro, cfg):
    """Registro crudo -> senal SinArm en voltios."""
    v = adc_a_voltios(df_registro["emg_adc"].to_numpy(), cfg["vref_v"], cfg["adc_bits"])
    return sinarm_desde_config(v, cfg)


def rms_por_fase(y, fases, fs, saltar_s=1.0):
    """RMS de la senal en cada fase (saltando el primer tramo). {fase: [rms, ...]}"""
    salida = {}
    salto = int(round(saltar_s * fs))
    for fase, ini, fin in segmentos(fases):
        tramo = y[ini + salto:fin]
        if len(tramo) > 0:
            salida.setdefault(fase, []).append(float(np.sqrt(np.mean(tramo ** 2))))
    return salida


def ventanas_de_registro(df_registro, cfg):
    """Registro crudo -> DataFrame de ventanas con sus caracteristicas."""
    y = senal_sinarm(df_registro, cfg)
    w = cfg["windows"]
    return ventanas(y, df_registro["phase"].to_numpy(), cfg["fs_hz"],
                    largo_ms=w["length_ms"], saltar_s=w["skip_after_cue_s"])


def filas_utiles(meta, conjunto):
    """Filas de metadata del conjunto ('train' o 'test') que pasaron la calidad."""
    m = meta[meta["set"] == conjunto]
    return m[m["trials_rejected"].astype(str).str.strip() == "0"]


def tabla_ventanas(meta, cfg, conjunto="train", carpeta=None):
    """Ventanas de todas las grabaciones aceptadas de un conjunto, con su sesion."""
    partes = []
    for _, fila in filas_utiles(meta, conjunto).iterrows():
        ruta = (carpeta / fila["file_name"]) if carpeta is not None else ruta_de_fila(cfg, fila)
        v = ventanas_de_registro(leer_registro(ruta), cfg)
        v.insert(0, "file_name", fila["file_name"])
        v.insert(1, "session", fila["session"])
        partes.append(v)
    if not partes:
        raise FileNotFoundError(f"No hay grabaciones aceptadas del conjunto '{conjunto}'. "
                                "Corran primero code/check_quality.py.")
    return pd.concat(partes, ignore_index=True)
