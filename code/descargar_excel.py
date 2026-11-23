"""descargar_excel.py - baja los registros de UNA persona y los guarda en un .xlsx.

Escrito por el equipo con ayuda de Claude (IA). Lo explica cualquier miembro.

Uso:
  python code/descargar_excel.py --fuente azure --participante P01            # prueba, desde Azure
  python code/descargar_excel.py --fuente local --participante P01 --set train
  python code/descargar_excel.py --fuente azure --participante P01 --sesion S11 --sin-senal
Opciones: --salida salidas/archivo.xlsx  --sas-url URL  --sin-senal (solo resumen y ventanas)
          --si (no preguntar antes de abrir la prueba)

El .xlsx trae: LEEME, metadata, resumen, ventanas de 100 ms y una hoja por grabacion
con la senal cruda, en voltios y filtrada (SinArm). Va a salidas/ (ignorado por git).
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from emg_cuello import calidad, excel, nube                                # noqa: E402
from emg_cuello.config import RAIZ, cargar_config, carpeta                  # noqa: E402
from emg_cuello.datos import leer_metadata, leer_registro, ruta_de_fila     # noqa: E402
from emg_cuello.filtros import adc_a_voltios                                # noqa: E402
from emg_cuello.procesar import rms_por_fase, senal_sinarm, ventanas_de_registro  # noqa: E402


def bajar_de_azure(cfg, participante, sas_url):
    """Baja metadata_test.csv y cada grabacion. Regresa (metadata, {archivo: ruta})."""
    cont = nube.contenedor(cfg["azure_container"], sas_url)
    destino = carpeta(cfg, "azure_download") / participante
    ruta_meta, rutas = nube.bajar_participante(cont, participante, destino)
    if not rutas:
        sys.exit(f"No hay grabaciones de {participante} en el contenedor.")
    meta = leer_metadata(ruta_meta) if ruta_meta else pd.DataFrame(
        {"file_name": sorted(rutas), "set": "test"})
    print(f"{len(rutas)} grabaciones bajadas a {destino.relative_to(RAIZ)}")
    return meta, rutas


def de_local(cfg, meta):
    rutas = {}
    for _, fila in meta.iterrows():
        ruta = ruta_de_fila(cfg, fila)
        if ruta.exists():
            rutas[fila["file_name"]] = ruta
        else:
            print(f"  no esta aqui: {ruta.relative_to(RAIZ)}")
    return rutas


def procesar(cfg, meta, rutas):
    """Arma las tablas resumen y ventanas, y la senal de cada grabacion."""
    resumen, partes, registros = [], [], []
    for nombre in sorted(rutas):
        df = leer_registro(rutas[nombre])
        y = senal_sinarm(df, cfg)
        fases = df["phase"].to_numpy()
        rms = rms_por_fase(y, fases, cfg["fs_hz"], cfg["windows"]["skip_after_cue_s"])
        v = adc_a_voltios(df["emg_adc"], cfg["vref_v"], cfg["adc_bits"])
        tope = 2 ** cfg["adc_bits"] - 1
        resumen.append({
            "file_name": nombre, "n_samples": len(df),
            "missing_samples": calidad.contar_huecos(df["sample"]),
            "clipped_samples": int(((df["emg_adc"] <= 0) | (df["emg_adc"] >= tope)).sum()),
            "zero_level_v": float(np.mean(v[fases == "rest"])) if (fases == "rest").any() else np.nan,
            **{f"{f}_rms_mv": 1000 * np.mean(r) for f, r in rms.items()},
        })
        w = ventanas_de_registro(df, cfg)
        w.insert(0, "file_name", nombre)
        partes.append(w)
        registros.append((Path(nombre).stem, pd.DataFrame({
            "sample": df["sample"], "time_ms": df["time_ms"], "emg_adc": df["emg_adc"],
            "emg_v": v, "emg_sinarm_v": y, "phase": df["phase"]})))
    ventanas = pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()
    return pd.DataFrame(resumen), ventanas, registros


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--fuente", choices=["azure", "local"], default="azure")
    p.add_argument("--participante", default=None, help="P01 (por defecto el de config.json)")
    p.add_argument("--set", choices=["test", "train", "todos"], default="test")
    p.add_argument("--sesion", help="solo una sesion, p. ej. S11")
    p.add_argument("--salida", help="ruta del .xlsx")
    p.add_argument("--sin-senal", action="store_true", help="sin una hoja por grabacion")
    p.add_argument("--sas-url", help="enlace SAS de solo lectura")
    p.add_argument("--si", action="store_true", help="no preguntar")
    p.add_argument("--simulado", action="store_true", help="ensayo con data/simulado/ (local)")
    args = p.parse_args()
    cfg = cargar_config()
    part = args.participante or cfg["participant"]
    if args.simulado:
        meta = leer_metadata(carpeta(cfg, "simulated") / "metadata.csv")
        rutas = {f: carpeta(cfg, "simulated") / f for f in meta["file_name"]}
        resumen, ventanas, registros = procesar(cfg, meta, rutas)
        salida = Path(args.salida) if args.salida else carpeta(cfg, "outputs") / f"{part}_simulado.xlsx"
        excel.exportar(salida, meta, resumen, ventanas, registros, not args.sin_senal)
        print(f"Excel listo: {salida}  ({len(rutas)} grabaciones SIMULADAS)")
        return
    if args.set in ("test", "todos") and not args.si:
        r = input("Esto ABRE las sesiones de prueba (el examen sellado). "
                  "Escriban 'abrir' para seguir: ")
        if r.strip().lower() != "abrir":
            sys.exit("Cancelado.")
    if args.fuente == "azure":
        meta, rutas = bajar_de_azure(cfg, part, args.sas_url)
    else:
        meta = leer_metadata(RAIZ / "data" / "metadata.csv")
        meta = meta[meta["participant"] == part]
        if args.set != "todos":
            meta = meta[meta["set"] == args.set]
        rutas = de_local(cfg, meta)
    if args.sesion:
        meta = meta[meta.get("session", pd.Series(dtype=str)) == args.sesion.upper()]
        rutas = {k: v for k, v in rutas.items() if f"_{args.sesion.upper()}_" in k}
    if not rutas:
        sys.exit("No hay grabaciones que exportar con ese filtro.")
    resumen, ventanas, registros = procesar(cfg, meta, rutas)
    sufijo = args.sesion.upper() if args.sesion else args.set
    salida = Path(args.salida) if args.salida else carpeta(cfg, "outputs") / f"{part}_{sufijo}.xlsx"
    excel.exportar(salida, meta, resumen, ventanas, registros, not args.sin_senal)
    print(f"Excel listo: {salida}  ({len(rutas)} grabaciones, {len(ventanas)} ventanas)")


if __name__ == "__main__":
    main()
