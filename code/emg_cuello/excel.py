"""Exportar los registros de una persona a un archivo de Excel (.xlsx).

Hojas:
  LEEME        que significa cada hoja y cada columna
  metadata     una fila por grabacion (las mismas columnas de metadata.csv)
  resumen      una fila por grabacion: calidad y RMS SinArm por fase
  ventanas     una fila por ventana de 100 ms: fase, etiqueta y 6 caracteristicas
  P01_S11_R01  ... una hoja por grabacion: sample, time_ms, emg_adc, emg_v,
               emg_sinarm_v, phase  (opcional con --sin-senal)
Excel admite 1 048 576 filas por hoja; una grabacion de 15 s tiene 15 000.
"""
import numpy as np
import xlsxwriter

LEEME = [
    ("Hoja", "Contenido"),
    ("metadata", "Una fila por grabacion. Mismas columnas que data/metadata.csv (ver DATA-DICTIONARY.md)."),
    ("resumen", "Una fila por grabacion: muestras, huecos, saturacion, nivel cero y RMS SinArm por fase."),
    ("ventanas", "Una fila por ventana de 100 ms dentro de reposo y arriba (sin el primer segundo de cada fase)."),
    ("P.._S.._R..", "Una hoja por grabacion, una fila por muestra."),
    ("", ""),
    ("Columna", "Significado"),
    ("sample", "Numero de muestra que da el contador del Arduino (empieza en 0)."),
    ("time_ms", "sample x 1 ms (Fs nominal 1000 Hz). La Fs medida esta en metadata, fs_measured_hz."),
    ("emg_adc", "Cuenta cruda del ADC de 14 bits (0 a 16383). Sin filtrar."),
    ("emg_v", "emg_adc x 5.0 / 16383, en voltios a la salida del sensor."),
    ("emg_sinarm_v", "emg_v con el filtro SinArm: sin DC y sin 60 Hz ni sus armonicos hasta 420 Hz."),
    ("phase", "rest = reposo, warning = aviso, move = cuello arriba, between = regreso."),
    ("label", "0 = reposo (cuello neutro), 1 = movimiento (cuello arriba)."),
    ("mav, rms, wl, zc, mnf, mdf", "Caracteristicas de la ventana (ver code/emg_cuello/caracteristicas.py)."),
]


def _hoja_tabla(libro, nombre, df, negrita):
    hoja = libro.add_worksheet(nombre[:31])
    hoja.write_row(0, 0, list(df.columns), negrita)
    for i, fila in enumerate(df.itertuples(index=False), start=1):
        hoja.write_row(i, 0, ["" if (isinstance(v, float) and np.isnan(v)) else v
                              for v in fila])
    hoja.freeze_panes(1, 0)
    return hoja


def exportar(salida, metadata, resumen, ventanas, registros, incluir_senal=True):
    """registros: lista de (nombre_hoja, DataFrame con las columnas de la senal)."""
    salida.parent.mkdir(parents=True, exist_ok=True)
    libro = xlsxwriter.Workbook(str(salida), {"constant_memory": True,
                                              "nan_inf_to_errors": True})
    negrita = libro.add_format({"bold": True})
    hoja = libro.add_worksheet("LEEME")
    for i, (a, b) in enumerate(LEEME):
        hoja.write_row(i, 0, [a, b], negrita if a in ("Hoja", "Columna") else None)
    hoja.set_column(0, 0, 26)
    hoja.set_column(1, 1, 100)
    _hoja_tabla(libro, "metadata", metadata, negrita)
    _hoja_tabla(libro, "resumen", resumen, negrita)
    _hoja_tabla(libro, "ventanas", ventanas, negrita)
    if incluir_senal:
        for nombre, df in registros:
            _hoja_tabla(libro, nombre, df, negrita)
    libro.close()
    return salida
