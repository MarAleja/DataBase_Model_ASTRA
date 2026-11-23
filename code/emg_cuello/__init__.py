"""emg_cuello: pipeline de EMG del esplenio de la cabeza (cuello arriba vs neutro).

Modulos:
    config        carga config/config.json y arma el plan de fases
    datos         nombres de archivo, lectura y escritura de registros y metadata
    filtros       filtro SinArm (igual al sketch del Arduino)
    calidad       tres revisiones del curso (nivel cero, saturacion, longitud) y huecos
    caracteristicas  ventanas de 100 ms y MAV, RMS, WL, ZC, MNF, MDF
    adquisicion   lectura del Arduino por USB y simulador sin hardware
    sonidos       senales de audio para la persona
    nube          subir y bajar archivos de Azure Blob Storage
    excel         exportar los registros de una persona a .xlsx
"""
__version__ = "1.0.0"
