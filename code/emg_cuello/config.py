"""Carga config/config.json y arma el plan de fases de un intento."""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
RUTA_CONFIG = RAIZ / "config" / "config.json"

# Campos que copiamos tal cual de la configuracion a cada fila de metadata.csv
CAMPOS_FIJOS = [
    "participant", "task", "muscle", "side", "posture",
    "rest_s", "warning_s", "move_s", "between_s",
    "fs_hz", "adc_bits", "vref_v", "gain", "sensor_model", "sensor_analog_filter",
    "electrode_type", "electrode_distance_cm", "ground_site", "skin_preparation",
    "electrodes", "cue",
]

# Fases del modo piloto: neutro, arriba, neutro, abajo, neutro (5 s cada una)
FASES_PILOTO = [("rest", 5), ("move", 5), ("rest", 5), ("down", 5), ("rest", 5)]


def cargar_config(ruta=None):
    """Lee el JSON de configuracion y lo regresa como diccionario."""
    with open(Path(ruta) if ruta else RUTA_CONFIG, encoding="utf-8") as f:
        return json.load(f)


def campos_incompletos(cfg):
    """Lista de campos que todavia dicen COMPLETAR."""
    return [k for k, v in cfg.items()
            if isinstance(v, str) and v.strip().upper() == "COMPLETAR"]


def carpeta(cfg, nombre):
    """Ruta absoluta de una carpeta de config['folders']."""
    return RAIZ / cfg["folders"][nombre]


def fases_intento(cfg):
    """Fases de un intento, en orden: [(nombre, segundos), ...]."""
    return [("rest", cfg["rest_s"]), ("warning", cfg["warning_s"]),
            ("move", cfg["move_s"]), ("between", cfg["between_s"])]


def plan_muestras(fases, fs):
    """Convierte [(nombre, s)] en [(nombre, muestra_inicio, muestra_fin)].

    Ejemplo: [("rest", 5), ("move", 5)] a 1000 Hz -> [("rest", 0, 5000), ("move", 5000, 10000)]
    """
    plan, inicio = [], 0
    for nombre, segundos in fases:
        fin = inicio + int(round(segundos * fs))
        plan.append((nombre, inicio, fin))
        inicio = fin
    return plan


def fase_de_muestra(plan, n):
    """Nombre de la fase a la que pertenece la muestra n."""
    for nombre, inicio, fin in plan:
        if inicio <= n < fin:
            return nombre
    return plan[-1][0]


def set_de_sesion(cfg, sesion):
    """'train' o 'test' segun la lista de la configuracion; None si no esta."""
    if sesion in cfg["train_sessions"]:
        return "train"
    if sesion in cfg["test_sessions"]:
        return "test"
    return None
