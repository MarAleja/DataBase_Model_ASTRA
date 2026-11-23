"""Pruebas con respuesta conocida, una por pieza (curso, diapositiva 7: 'check every part').

Correr desde la raiz del repo:   python -m pytest code/tests -q
"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from emg_cuello import calidad, caracteristicas as ca, filtros                # noqa: E402
from emg_cuello.adquisicion import (ErrorAdquisicion, FuenteSimulada,       # noqa: E402
                                    capturar, parsear)
from emg_cuello.config import cargar_config, fases_intento, plan_muestras     # noqa: E402
from emg_cuello.modelos import UmbralUnaCaracteristica                        # noqa: E402

FS = 1000


# ------------------------------------------------------------ matematicas (diapositiva 8)
def test_mav_y_rms_del_curso():
    x = [2, -3, 1, -2]
    assert ca.mav(x) == pytest.approx(2.0)
    assert ca.rms(x) == pytest.approx(2.1213, abs=1e-4)


def test_duracion_con_n_y_fs():
    assert 5288 / FS == pytest.approx(5.288)          # diapositiva 7


def test_wl_y_zc():
    assert ca.wl([0, 1, -1, 2]) == pytest.approx(1 + 2 + 3)
    assert ca.zc([1, -1, 1, -1]) == 3


def test_mnf_y_mdf_de_un_seno():
    t = np.arange(1000) / FS
    x = np.sin(2 * np.pi * 100 * t)
    assert ca.mnf(x, FS) == pytest.approx(100, abs=1)
    assert ca.mdf(x, FS) == pytest.approx(100, abs=1)


# ------------------------------------------------------------ filtro SinArm
def test_notch_quita_60_hz_y_deja_pasar_lo_demas():
    t = np.arange(5 * FS) / FS
    # 250 Hz no se usa: queda a 10 Hz del notch de 240 Hz y baja a 0.92 (es real)
    for f, esperado in [(60, 0.0), (120, 0.0), (420, 0.0), (90, 1.0), (150, 1.0)]:
        v = 2.5 + 0.1 * np.sin(2 * np.pi * f * t)
        y = filtros.sinarm(v, fs=FS)[2 * FS:]          # sin el arranque
        ganancia = ca.rms(y) / (0.1 / np.sqrt(2))
        assert ganancia == pytest.approx(esperado, abs=0.05), f


def test_quita_dc():
    v = np.full(5 * FS, 2.47)
    assert np.max(np.abs(filtros.sinarm(v, fs=FS))) < 1e-9


def test_python_igual_al_arduino():
    rng = np.random.default_rng(1)
    t = np.arange(3000) / FS
    v = 2.5 + 0.02 * rng.normal(size=3000) + 0.05 * np.sin(2 * np.pi * 60 * t)
    rapido = filtros.sinarm(v, fs=FS, dc0=2.5)
    linea_por_linea = filtros.sinarm_como_arduino(v, dc0=2.5)
    assert np.max(np.abs(rapido - linea_por_linea)) < 1e-5   # diferencia float32 vs float64


def test_corte_del_paso_alto():
    assert filtros.corte_paso_alto_hz(0.003, FS) == pytest.approx(0.48, abs=0.02)


# ------------------------------------------------------------ calidad (diapositiva 15)
def test_longitud_como_en_el_curso():
    reglas = {"max_missing_pct": 1.0, "length_tolerance_pct": 2.0, "fs_tolerance_pct": 2.0}
    for n, pasa in [(5084, True), (5363, False), (5091, True)]:
        adc = np.full(n, 8000)
        rev = calidad.revisar(np.arange(n), adc, 5000, 14)
        assert (not calidad.decidir(rev, reglas)[0]) == pasa


def test_saturacion():
    adc = np.full(100, 8000)
    adc[10] = 16383
    adc[20] = 0
    assert calidad.revisar(np.arange(100), adc, 100, 14)["clipped_samples"] == 2


def test_huecos():
    n = np.delete(np.arange(1000), [5, 6, 7])
    assert calidad.contar_huecos(n) == 3


def test_fs_medida_con_vuelta_de_micros():
    marcas = [(0, 2 ** 32 - 500_000), (1000, 500_000)]   # micros() dio la vuelta
    assert calidad.fs_medida(marcas) == pytest.approx(1000.0)


# ------------------------------------------------------------ ventanas
def test_ventanas_saltan_el_primer_segundo_y_no_mezclan_fases():
    fases = ["rest"] * 5000 + ["warning"] * 1000 + ["move"] * 5000 + ["between"] * 4000
    y = np.zeros(len(fases))
    w = ca.ventanas(y, fases, FS, largo_ms=100, saltar_s=1.0)
    assert (w["phase"] == "rest").sum() == 40 and (w["phase"] == "move").sum() == 40
    assert w["start_sample"].min() == 1000
    assert set(w["label"]) == {0, 1}


# ------------------------------------------------------------ captura con el simulador
def test_captura_marca_las_fases_con_el_contador():
    cfg = cargar_config()
    plan = plan_muestras(fases_intento(cfg), FS)
    fuente = FuenteSimulada(plan, fs=FS, rapido=True, perder=0.0)
    d = capturar(fuente, plan, FS)
    assert len(d["n"]) == 15000
    assert d["phase"][0] == "rest" and d["phase"][5000] == "warning"
    assert d["phase"][6000] == "move" and d["phase"][14999] == "between"
    assert calidad.fs_medida(d["marcas"]) == pytest.approx(1000.0)


def test_captura_detecta_muestras_perdidas():
    cfg = cargar_config()
    plan = plan_muestras(fases_intento(cfg), FS)
    d = capturar(FuenteSimulada(plan, fs=FS, rapido=True, perder=0.02, semilla=3), plan, FS)
    rev = calidad.revisar(d["n"], d["adc"], 15000, 14)
    assert rev["missing_pct"] == pytest.approx(2.0, abs=0.5)
    assert calidad.decidir(rev, cfg["quality"])[0]          # rechazado


# ------------------------------------------------------------ piso de umbral
def test_umbral_encuentra_el_corte():
    x = np.r_[np.full(50, 1.0), np.full(50, 5.0)].reshape(-1, 1)
    y = np.r_[np.zeros(50), np.ones(50)].astype(int)
    m = UmbralUnaCaracteristica().fit(x, y)
    assert (m.predict(x) == y).all()


# ------------------------------------------------------------ enlace USB (adq-v2)
def test_parsear_bloques_y_formato_viejo():
    assert parsear("20:5,6,7") == [(20, 5), (21, 6), (22, 7)]
    assert parsear("7,8190") == [(7, 8190)]
    assert parsear("Bruto:0.021,Sin60:0.010,SinArm:0.009") is None
    assert parsear("#T,1000,123,0") is None


def test_si_la_placa_se_reinicia_avisa_y_no_se_congela():
    cfg = cargar_config()
    plan = plan_muestras(fases_intento(cfg), FS)
    fuente = FuenteSimulada(plan, fs=FS, rapido=True, cortar_en=4000, bruto_tras_corte=True)
    with pytest.raises(ErrorAdquisicion, match="reinicio"):
        capturar(fuente, plan, FS, espera_max_s=0.3)


def test_si_el_enlace_se_calla_avisa():
    cfg = cargar_config()
    plan = plan_muestras(fases_intento(cfg), FS)
    fuente = FuenteSimulada(plan, fs=FS, rapido=True, cortar_en=23000 % 15000)
    with pytest.raises(ErrorAdquisicion, match="enlace USB"):
        capturar(fuente, plan, FS, espera_max_s=0.3)
