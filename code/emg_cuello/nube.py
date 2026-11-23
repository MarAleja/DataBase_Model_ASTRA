"""Subir y bajar archivos de Azure Blob Storage (contenedor 'recordings').

Credenciales, en este orden (la clave NUNCA va en el repositorio):
  1. argumento --sas-url (enlace de solo lectura, por ejemplo el que reciba Mahdi)
  2. variable de entorno AZURE_STORAGE_CONNECTION_STRING o AZURE_SAS_URL
  3. archivo .env en la raiz del repo (lo ignora .gitignore), con esas variables
  4. en Colab: Secrets (icono de llave) con esos mismos nombres

Estructura en el contenedor:
  P01/metadata_test.csv               una fila por grabacion de prueba
  P01/S11/P01_S11_R01.csv             cada grabacion, con su metadata en el blob
Al bajar, todo queda en una sola carpeta: data/azure_descarga/P01/
"""
import hashlib
import os
from pathlib import Path

from .config import RAIZ


def _leer_env(ruta=RAIZ / ".env"):
    valores = {}
    if Path(ruta).exists():
        for linea in Path(ruta).read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                k, v = linea.split("=", 1)
                valores[k.strip()] = v.strip().strip('"').strip("'")
    return valores


def _secreto(nombre):
    if os.environ.get(nombre):
        return os.environ[nombre]
    env = _leer_env()
    if env.get(nombre):
        return env[nombre]
    try:                                            # Google Colab
        from google.colab import userdata
        return userdata.get(nombre)
    except Exception:
        return None


def contenedor(nombre_contenedor="recordings", sas_url=None):
    """ContainerClient con la primera credencial que encuentre."""
    from azure.storage.blob import ContainerClient
    sas_url = sas_url or _secreto("AZURE_SAS_URL")
    if sas_url:
        return ContainerClient.from_container_url(sas_url)
    conexion = _secreto("AZURE_STORAGE_CONNECTION_STRING")
    if conexion:
        return ContainerClient.from_connection_string(conexion, nombre_contenedor)
    raise RuntimeError("No encontre credenciales de Azure. Pongan "
                       "AZURE_STORAGE_CONNECTION_STRING en un archivo .env en la raiz del "
                       "repo (o en Colab Secrets), o usen --sas-url.")


def sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 16), b""):
            h.update(bloque)
    return h.hexdigest()


def subir(cont, ruta_local, nombre_blob, metadata=None, sobrescribir=False):
    """Sube un archivo. Por defecto NO sobrescribe (es el expediente del paciente)."""
    limpio = {k: str(v).encode("ascii", "ignore").decode()[:250]
              for k, v in (metadata or {}).items()}
    with open(ruta_local, "rb") as f:
        cont.upload_blob(nombre_blob, f, overwrite=sobrescribir, metadata=limpio)


def listar(cont, prefijo):
    return [b.name for b in cont.list_blobs(name_starts_with=prefijo)]


def descargar(cont, nombre_blob, destino):
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "wb") as f:
        f.write(cont.download_blob(nombre_blob).readall())
    return destino


def bajar_participante(cont, participante, destino):
    """Baja todo lo de una persona a destino/. Regresa (ruta_metadata o None, {archivo: ruta})."""
    destino = Path(destino)
    rutas, ruta_meta = {}, None
    for b in listar(cont, f"{participante}/"):
        local = descargar(cont, b, destino / Path(b).name)
        if Path(b).name == "metadata_test.csv":
            ruta_meta = local
        elif b.endswith(".csv"):
            rutas[Path(b).name] = local
    return ruta_meta, rutas
