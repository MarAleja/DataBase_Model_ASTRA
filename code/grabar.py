"""grabar.py - graba la base de datos: un archivo por intento, con senales de audio.

Escrito por el equipo con ayuda de Claude (IA). Lo explica cualquier miembro.

Uso (desde la carpeta raiz del repositorio):
    python code/grabar.py --probar-enlace          # 60 s sin persona: revisa el USB
    python code/grabar.py --piloto                 # paso 0: neutro, arriba, neutro, abajo
    python code/grabar.py --sesion S01             # sesion de entrenamiento (S01 a S10)
    python code/grabar.py --sesion S11             # sesion de prueba, clase final (S11 a S14)
    python code/grabar.py --sesion S01 --simular   # ensayo sin Arduino (va a data/simulado/)
Opciones: --puerto /dev/cu.usbmodemXXXX   --voz (macOS)   --sin-sonido

Cada intento: reposo 5 s, aviso 1 s, arriba 5 s, regreso 4 s (config/config.json).
Las fases se marcan con el contador del Arduino, asi la etiqueta coincide con la senal.
Nunca sobrescribe: si un intento se repite, el malo se queda marcado como rechazado.
"""
import argparse
import datetime as dt
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from emg_cuello import calidad                                          # noqa: E402
from emg_cuello.adquisicion import (ErrorAdquisicion, FuenteArduino,    # noqa: E402
                                    FuenteSimulada, buscar_puerto, capturar)
from emg_cuello.config import (CAMPOS_FIJOS, FASES_PILOTO, RAIZ,        # noqa: E402
                               campos_incompletos, cargar_config, carpeta, fases_intento,
                               plan_muestras, set_de_sesion)
from emg_cuello.datos import (agregar_fila_metadata, escribir_registro,  # noqa: E402
                              leer_metadata, nombre_archivo)
from emg_cuello.filtros import adc_a_voltios, sinarm_desde_config        # noqa: E402
from emg_cuello.procesar import rms_por_fase                             # noqa: E402
from emg_cuello.sonidos import Sonidos                                   # noqa: E402

COLOR = {"rest": "\033[42;30m", "warning": "\033[43;30m", "move": "\033[41;97m",
         "between": "\033[44;97m", "down": "\033[45;97m"}
TEXTO = {"rest": "REPOSO   - cuello neutro, mira la marca A",
         "warning": "PREPARATE",
         "move": "ARRIBA   - sube la cabeza a la marca B y sostenla",
         "between": "REGRESA  - vuelve a la marca A y relaja",
         "down": "ABAJO    - baja la barbilla a la marca C y sostenla"}
FIN = "\033[0m"


# ------------------------------------------------------------------ pantalla
def anunciar(fase, sonidos):
    sonidos.tocar(fase)
    print(f"\n  {COLOR.get(fase, '')}  {TEXTO.get(fase, fase.upper()):<56}{FIN}", flush=True)


def progreso(n, total, fs):
    print(f"\r    {n / fs:5.1f} s de {total / fs:.0f} s", end="", flush=True)


def preguntar(texto, opciones=("",)):
    while True:
        r = input(texto).strip().lower()
        if r in opciones:
            return r
        print(f"    Opciones: {', '.join(o or 'Enter' for o in opciones)}")


# ------------------------------------------------------------------ fuente
def abrir_fuente(args, cfg, plan):
    if args.simular:
        print("MODO SIMULADO: la senal es inventada. Sirve solo para ensayar el flujo.")
        fuente = FuenteSimulada(plan, fs=cfg["fs_hz"], rapido=args.rapido)
        return fuente, fuente.saludo()
    puerto = args.puerto
    if not puerto:
        candidatos = buscar_puerto()
        if len(candidatos) == 1:
            puerto = candidatos[0][0]
        else:
            print("Puertos encontrados:" if candidatos else "No encontre un Arduino.")
            for dev, desc in candidatos:
                print(f"   {dev}   ({desc})")
            sys.exit("Indiquen el puerto con --puerto (el mismo que usa el Arduino IDE).")
    print(f"Abriendo {puerto} a {cfg['serial_baud']} baudios ...")
    try:
        fuente = FuenteArduino(puerto, cfg["serial_baud"])
    except Exception as e:
        if "denied" in str(e).lower() or "busy" in str(e).lower():
            sys.exit(f"El puerto {puerto} esta ocupado por otro programa. Cierren el Arduino "
                     "IDE completo (Serial Monitor y Plotter) y otras terminales.")
        sys.exit(f"No pude abrir {puerto}: {e}. Revisen el numero de puerto.")
    info = fuente.saludo()
    print(f"Arduino listo: {info}")
    if info.get("version") != cfg["firmware_expected"]:
        print(f"AVISO: el sketch dice version={info.get('version')}, "
              f"se esperaba {cfg['firmware_expected']}.")
    if int(info.get("fs", 0)) != cfg["fs_hz"] or int(info.get("bits", 0)) != cfg["adc_bits"]:
        sys.exit("La Fs o los bits del sketch no coinciden con config/config.json.")
    return fuente, info


def capturar_con_senales(fuente, plan, fs, sonidos):
    total = plan[-1][2]
    datos = capturar(fuente, plan, fs, al_cambiar_fase=lambda f: anunciar(f, sonidos),
                     al_avanzar=lambda n: progreso(n, total, fs))
    print()
    return datos


# ------------------------------------------------------------------ enlace
def probar_enlace(args, cfg):
    """Recibe datos N segundos sin guardar nada y dice si el enlace USB aguanta."""
    segundos = args.probar_enlace
    plan = plan_muestras([("rest", segundos)], cfg["fs_hz"])
    total = plan[-1][2]
    fuente, info = abrir_fuente(args, cfg, plan)
    print(f"\nPRUEBA DEL ENLACE: {segundos} s, no guarda nada y no hace falta la persona.")
    t0 = time.monotonic()
    try:
        d = capturar(fuente, plan, cfg["fs_hz"], al_avanzar=lambda n: progreso(n, total, cfg["fs_hz"]))
    finally:
        fuente.cerrar()
    reloj = time.monotonic() - t0
    huecos = calidad.contar_huecos(d["n"])
    fs_real = calidad.fs_medida(d["marcas"])
    print(f"\n  Muestras recibidas: {len(d['n'])} de {total}   huecos: {huecos}"
          f"   lineas danadas: {d['ignoradas']}")
    print(f"  Fs medida en el Arduino: {fs_real:.1f} Hz   atrasos: {d['atrasos']}"
          f"   tiempo de reloj: {reloj:.1f} s (debe ser ~{segundos} s)")
    ok = huecos == 0 and d["ignoradas"] == 0 and abs(reloj - segundos) < 0.1 * segundos
    print("  ENLACE OK: ya pueden hacer el piloto." if ok else
          "  ENLACE CON PROBLEMAS: manden estas lineas antes de grabar.")


# ------------------------------------------------------------------ piloto
def correr_piloto(args, cfg):
    plan = plan_muestras(FASES_PILOTO, cfg["fs_hz"])
    fuente, info = abrir_fuente(args, cfg, plan)
    sonidos = Sonidos(activo=not args.sin_sonido, voz=args.voz)
    print("\nPILOTO: 25 s. Neutro 5 s, ARRIBA 5 s, neutro 5 s, ABAJO 5 s, neutro 5 s.")
    print("Sirve para ver si el esplenio distingue arriba de neutro (y de abajo).")
    input("Enter para empezar ... ")
    try:
        d = capturar_con_senales(fuente, plan, cfg["fs_hz"], sonidos)
    finally:
        fuente.cerrar()
    destino = carpeta(cfg, "simulated" if args.simular else "pilot")
    sello = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta = destino / f"{cfg['participant']}_PILOT_{sello}.csv"
    escribir_registro(ruta, d["n"], d["adc"], d["phase"], cfg["fs_hz"])
    y = sinarm_desde_config(adc_a_voltios(d["adc"], cfg["vref_v"], cfg["adc_bits"]), cfg)
    r = rms_por_fase(y, d["phase"], cfg["fs_hz"], cfg["windows"]["skip_after_cue_s"])
    neutro = float(np.mean(r["rest"]))
    arriba, abajo = r["move"][0], r["down"][0]
    print(f"\nGuardado: {ruta.relative_to(RAIZ)}")
    print("RMS SinArm (sin el primer segundo de cada fase):")
    print(f"   neutro  {1000 * neutro:7.2f} mV")
    print(f"   arriba  {1000 * arriba:7.2f} mV   ({arriba / neutro:4.1f} veces el neutro)")
    print(f"   abajo   {1000 * abajo:7.2f} mV   ({abajo / neutro:4.1f} veces el neutro)")
    print("Anoten estos numeros en DECISIONS.md. Repitan el piloto 3 veces.")


# ------------------------------------------------------------------ sesion
def lista_previa(sesion, conjunto):
    print(f"\nSESION {sesion} ({conjunto}). Antes de grabar:")
    for paso in ("Electrodos NUEVOS, colocados desde cero (PROTOCOL.md, paso 3)",
                 f"Foto de los electrodos SIN cara: figures/placement_{sesion}.jpg",
                 "Marcas A (frente) y B (arriba) en la pared, persona sentada igual",
                 "Serial Monitor y Serial Plotter del IDE CERRADOS"):
        print(f"   [ ] {paso}")
    preguntar("Enter cuando todo este listo ... ")


def estado_sesion(meta, participante, sesion):
    """(grabaciones ya hechas, grabaciones aceptadas: pasaron calidad y quien opera)."""
    filas = meta[(meta["participant"] == participante) & (meta["session"] == sesion)]
    hechas = len(filas)
    aceptadas = int((filas["trials_rejected"].astype(str) == "0").sum()) if hechas else 0
    return hechas, aceptadas


def ultimo_numero_en_disco(destino, participante, sesion):
    """Numero de grabacion mas alto que ya existe en disco (para nunca sobrescribir)."""
    numeros = [int(p.stem.rsplit("_R", 1)[1]) for p in destino.glob(f"{participante}_{sesion}_R*.csv")
               if p.stem.rsplit("_R", 1)[1].isdigit()]
    return max(numeros, default=0)


def revisar_y_mostrar(d, plan, cfg, conjunto):
    fs_real = calidad.fs_medida(d["marcas"])
    rev = calidad.revisar(d["n"], d["adc"], plan[-1][2], cfg["adc_bits"], fs_real, cfg["fs_hz"])
    rech, razones = calidad.decidir(rev, cfg["quality"])     # solo para mostrar
    print(f"    N = {rev['n_samples']} de {rev['n_plan']}   huecos = {rev['missing_pct']:.2f} %"
          f"   saturadas = {rev['clipped_samples']}   Fs medida = {fs_real:.1f} Hz"
          f"   atrasos = {d['atrasos']}")
    if conjunto == "train":                  # en test no miramos la senal (sobre sellado)
        y = sinarm_desde_config(adc_a_voltios(d["adc"], cfg["vref_v"], cfg["adc_bits"]), cfg)
        r = rms_por_fase(y, d["phase"], cfg["fs_hz"], cfg["windows"]["skip_after_cue_s"])
        if "rest" in r and "move" in r:
            print(f"    RMS SinArm: reposo {1000 * r['rest'][0]:.2f} mV, "
                  f"arriba {1000 * r['move'][0]:.2f} mV")
    if rech:
        print("    \033[91mNO PASA: " + "; ".join(razones) + FIN)
    return rev, rech


def correr_sesion(args, cfg):
    sesion = args.sesion.upper()
    conjunto = set_de_sesion(cfg, sesion)
    if conjunto is None:
        sys.exit(f"{sesion} no esta en train_sessions ni en test_sessions de config.json.")
    faltan = campos_incompletos(cfg)
    if faltan and not args.simular:
        print(f"AVISO: en config/config.json faltan: {', '.join(faltan)}. "
              "Se copiaran como COMPLETAR a metadata.csv; corrijanlos antes del reporte.")
    plan = plan_muestras(fases_intento(cfg), cfg["fs_hz"])
    if args.simular:
        destino, ruta_meta = carpeta(cfg, "simulated"), carpeta(cfg, "simulated") / "metadata.csv"
    else:
        destino = carpeta(cfg, "test" if conjunto == "test" else "train")
        ruta_meta = RAIZ / "data" / "metadata.csv"
    destino.mkdir(parents=True, exist_ok=True)
    meta = leer_metadata(ruta_meta)
    hechas, aceptadas = estado_sesion(meta, cfg["participant"], sesion)
    hechas = max(hechas, ultimo_numero_en_disco(destino, cfg["participant"], sesion))
    meta_obj = cfg["recordings_per_session"]
    if aceptadas >= meta_obj:
        sys.exit(f"{sesion} ya tiene {aceptadas} grabaciones aceptadas.")
    if hechas:
        print(f"{sesion} ya tiene {hechas} grabaciones ({aceptadas} aceptadas). Continuo.")
    fuente, info = abrir_fuente(args, cfg, plan)
    sonidos = Sonidos(activo=not args.sin_sonido, voz=args.voz)
    if not args.simular:
        lista_previa(sesion, conjunto)
    fecha = dt.date.today().isoformat()
    try:
        while aceptadas < meta_obj:
            hechas += 1
            nombre = nombre_archivo(cfg["participant"], sesion, hechas)
            print(f"\n=== {nombre}   (aceptadas {aceptadas} de {meta_obj}) ===")
            r = "" if args.rapido else preguntar("Enter para grabar, q para salir ... ", ("", "q"))
            if r == "q":
                break
            hora = dt.datetime.now().strftime("%H:%M:%S")
            d = capturar_con_senales(fuente, plan, cfg["fs_hz"], sonidos)
            if (destino / nombre).exists():
                sys.exit(f"{nombre} ya existe: no se sobrescribe. Revisen metadata.csv.")
            escribir_registro(destino / nombre, d["n"], d["adc"], d["phase"], cfg["fs_hz"])
            rev, rech = revisar_y_mostrar(d, plan, cfg, conjunto)
            if args.rapido:
                op = ""
            else:
                op = preguntar("Enter = aceptar   r = repetir (este queda rechazado) ... ",
                               ("", "r"))
            nota = input("    Razon (ej. se movio a destiempo): ").strip() if op == "r" else ""
            rech_total, razones = calidad.decidir(rev, cfg["quality"], operador_ok=(op == ""),
                                                  nota_operador=nota)
            ok = not rech_total
            fila = {c: cfg[c] for c in CAMPOS_FIJOS}
            fila.update({
                "file_name": nombre, "session": sesion, "date": fecha, "time_start": hora,
                "recording": hechas, "trials": 1, "firmware": info.get("version", ""),
                "set": conjunto, "n_samples": rev["n_samples"],
                "fs_measured_hz": f"{rev['fs_measured_hz']:.2f}",
                "missing_pct": f"{rev['missing_pct']:.3f}", "late_samples": d["atrasos"],
                "clipped_samples": rev["clipped_samples"],
                "operator_ok": "yes" if op == "" else "no", "operator_note": nota,
                "trials_rejected": int(rech_total), "notes": "; ".join(razones),
            })
            agregar_fila_metadata(fila, ruta_meta)
            aceptadas += int(ok)
            if not ok and op == "":
                print("    Este intento no paso la calidad: se graba otro.")
    finally:
        fuente.cerrar()
    print(f"\nSesion {sesion}: {aceptadas} aceptadas de {meta_obj}. "
          f"Archivos en {destino.relative_to(RAIZ)}")
    if conjunto == "test" and not args.simular:
        print("Prueba: estos archivos NO van a GitHub. Subanlos con code/subir_azure.py")


def desactivar_edicion_rapida():
    """Windows pausa el programa si alguien da clic en la consola; esto lo evita."""
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        entrada = k32.GetStdHandle(-10)
        modo = ctypes.c_uint32()
        if k32.GetConsoleMode(entrada, ctypes.byref(modo)):
            k32.SetConsoleMode(entrada, (modo.value & ~0x0040) | 0x0080)
    except Exception:
        pass


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--sesion", help="S01 ... S14")
    p.add_argument("--piloto", action="store_true", help="prueba piloto neutro/arriba/abajo")
    p.add_argument("--probar-enlace", nargs="?", type=int, const=60, metavar="S",
                   help="recibir S segundos (60) sin guardar, para revisar el USB")
    p.add_argument("--puerto", help="puerto serie del Arduino")
    p.add_argument("--simular", action="store_true", help="sin Arduino, senal inventada")
    p.add_argument("--rapido", action="store_true", help=argparse.SUPPRESS)  # pruebas
    p.add_argument("--voz", action="store_true", help="decir la fase en voz (macOS)")
    p.add_argument("--sin-sonido", action="store_true", help="sin audio")
    args = p.parse_args()
    if os.name == "nt":
        os.system("")                     # activa los colores en la terminal de Windows
        desactivar_edicion_rapida()
    if args.rapido and not args.simular:
        sys.exit("--rapido solo existe con --simular.")
    cfg = cargar_config()
    try:
        if args.probar_enlace:
            probar_enlace(args, cfg)
        elif args.piloto:
            correr_piloto(args, cfg)
        elif args.sesion:
            correr_sesion(args, cfg)
        else:
            p.print_help()
    except ErrorAdquisicion as e:
        sys.exit(f"\nERROR: {e}")
    except (KeyboardInterrupt, EOFError):
        sys.exit("\nDetenido. Lo ya guardado se queda; vuelvan a correr la sesion para seguir. "
                 "Si un archivo quedo sin fila en metadata.csv, check_quality.py lo avisa.")


if __name__ == "__main__":
    main()
