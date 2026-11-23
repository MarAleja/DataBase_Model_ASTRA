"""actualizar_metadata.py - pasa a data/metadata.csv lo que llenaron en config/config.json.

Escrito por el equipo con ayuda de Claude (IA). Lo explica cualquier miembro.

Por que existe: grabar.py copia los campos fijos de config.json (modelo del sensor, ganancia,
electrodos, distancia, preparacion de la piel...) a cada fila de metadata.csv. Si grabaron
mientras esos campos decian COMPLETAR, las 100 filas quedaron con la palabra COMPLETAR.
Este script la cambia por lo que ya escribieron en config.json.

Reglas (para no inventar ni borrar nada):
  - Solo toca celdas que todavia contienen la palabra COMPLETAR. Un valor real nunca se cambia.
  - Se niega a correr si config.json todavia tiene COMPLETAR en alguno de esos campos.
  - Solo toca esos campos de descripcion. No toca la senal, la calidad ni las fechas.
  - Antes de escribir guarda una copia en salidas/metadata_antes_de_actualizar.csv.

Uso:  python code/actualizar_metadata.py            (muestra lo que cambiaria)
      python code/actualizar_metadata.py --aplicar  (lo escribe)
"""
import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from emg_cuello.config import RAIZ, cargar_config                          # noqa: E402
from emg_cuello.datos import RUTA_METADATA, escribir_metadata, leer_metadata  # noqa: E402

# Campos de descripcion que el equipo llena a mano en config.json
CAMPOS = ["sensor_model", "gain", "sensor_analog_filter", "electrode_type",
          "electrode_distance_cm", "ground_site", "skin_preparation"]


def pendientes_en_config(cfg):
    """Campos de CAMPOS que en config.json todavia dicen COMPLETAR."""
    return [c for c in CAMPOS if "COMPLETAR" in str(cfg.get(c, "")).upper()]


def actualizar(meta, cfg):
    """Regresa (tabla nueva, {campo: filas cambiadas}). No toca valores sin COMPLETAR."""
    meta = meta.copy()
    cambios = {}
    for c in CAMPOS:
        if c not in meta.columns:
            continue
        marcadas = meta[c].astype(str).str.upper().str.contains("COMPLETAR")
        if marcadas.any():
            meta.loc[marcadas, c] = str(cfg[c])
            cambios[c] = int(marcadas.sum())
    return meta, cambios


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--aplicar", action="store_true", help="escribir el cambio (sin esto solo se muestra)")
    args = ap.parse_args()

    cfg = cargar_config()
    falta = pendientes_en_config(cfg)
    if falta:
        print("config/config.json todavia dice COMPLETAR en:", ", ".join(falta))
        print("Llenenlos primero y vuelvan a correr esto.")
        sys.exit(1)

    meta = leer_metadata()
    if meta.empty:
        print(f"No hay filas en {RUTA_METADATA}.")
        sys.exit(1)

    nueva, cambios = actualizar(meta, cfg)
    if not cambios:
        print("Nada que cambiar: ninguna fila dice COMPLETAR en esos campos.")
        return
    print(f"{len(meta)} filas en metadata.csv. Celdas con COMPLETAR que se cambiarian:")
    for c, n in cambios.items():
        print(f"  {c:24s} {n:4d} filas  ->  {cfg[c]}")
    if not args.aplicar:
        print("\nNo se escribio nada. Si esta bien, corran:  python code/actualizar_metadata.py --aplicar")
        return
    copia = RAIZ / "salidas" / "metadata_antes_de_actualizar.csv"
    copia.parent.mkdir(exist_ok=True)
    shutil.copy(RUTA_METADATA, copia)
    escribir_metadata(nueva)
    print(f"\nListo. Copia del archivo anterior: {copia}")


if __name__ == "__main__":
    main()
