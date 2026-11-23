"""subir_azure.py - sube las sesiones de PRUEBA a Azure, con su metadata.

Escrito por el equipo con ayuda de Claude (IA). Lo explica cualquier miembro.

Uso:  python code/subir_azure.py --sesion S11
      python code/subir_azure.py --todas
Credenciales: AZURE_STORAGE_CONNECTION_STRING en .env (raiz del repo, ignorado por git)
o en el entorno. La prueba vive solo en Azure, como el expediente de un paciente;
el entrenamiento vive en GitHub. Nunca sobrescribe un archivo ya subido.
"""
import argparse
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from emg_cuello import nube                                               # noqa: E402
from emg_cuello.config import RAIZ, cargar_config                          # noqa: E402
from emg_cuello.datos import leer_metadata, ruta_de_fila                   # noqa: E402

CAMPOS_BLOB = ["participant", "session", "date", "set", "muscle", "side", "fs_hz",
               "adc_bits", "gain", "sensor_model", "firmware", "trials_rejected"]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--sesion", help="S11 ... S14")
    g.add_argument("--todas", action="store_true", help="todas las sesiones de prueba")
    p.add_argument("--sas-url", help="enlace SAS con permiso de escritura (opcional)")
    args = p.parse_args()
    cfg = cargar_config()
    meta = leer_metadata(RAIZ / "data" / "metadata.csv")
    test = meta[meta["set"] == "test"]
    if args.sesion:
        test = test[test["session"] == args.sesion.upper()]
    if test.empty:
        sys.exit("No hay grabaciones de prueba con ese filtro en data/metadata.csv.")
    cont = nube.contenedor(cfg["azure_container"], args.sas_url)
    try:
        if not cont.exists():
            cont.create_container()
            print(f"Contenedor '{cfg['azure_container']}' creado.")
    except Exception:
        pass                                  # con SAS puede no haber permiso; si existe, sigue
    existentes = set(nube.listar(cont, f"{cfg['participant']}/"))
    subidas = 0
    for _, fila in test.iterrows():
        ruta = ruta_de_fila(cfg, fila)
        blob = f"{fila['participant']}/{fila['session']}/{fila['file_name']}"
        if blob in existentes:
            print(f"  ya estaba: {blob}")
            continue
        if not ruta.exists():
            print(f"  FALTA el archivo local: {ruta}")
            continue
        datos = {c: fila[c] for c in CAMPOS_BLOB}
        datos["sha256"] = nube.sha256(ruta)
        nube.subir(cont, ruta, blob, datos)
        subidas += 1
        print(f"  subido: {blob}")
    # indice de metadata de la prueba (se reemplaza en cada subida)
    todo_test = meta[(meta["set"] == "test") & (meta["participant"] == cfg["participant"])]
    texto = io.StringIO()
    todo_test.to_csv(texto, index=False)
    cont.upload_blob(f"{cfg['participant']}/metadata_test.csv", texto.getvalue().encode(),
                     overwrite=True)
    print(f"{subidas} archivos subidos. Indice: {cfg['participant']}/metadata_test.csv")


if __name__ == "__main__":
    main()
