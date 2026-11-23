# Paso a paso: de los electrodos al modelo

Guía del equipo. Todo se corre desde la carpeta raíz del repositorio.
Los documentos que se califican (README, PROTOCOL, DECISIONS, QUALITY-REPORT) están en inglés, como el ejemplo del profe.

```
Arduino (adq-v2) ──USB──> grabar.py ──> data/raw/ + data/metadata.csv ──> GitHub (entrenamiento)
                                    └─> data/test_local/ ──> subir_azure.py ──> Azure (prueba)
GitHub ──> Colab: notebook entrena (dejando una sesión fuera) ──> models/
Azure  ──> Colab: celda 8, una sola vez ──> results/test_result.json
Azure o local ──> descargar_excel.py ──> salidas/P01_test.xlsx
```

---

## Paso 0. Una sola vez, en la compu que va a grabar

1. **Clonar** el repo y entrar a la carpeta.
2. **Python 3.10 o más nuevo**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate          # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   python -m pytest code/tests -q     # deben pasar las 16 pruebas
   ```
3. **Arduino IDE**: abrir `arduino/adquisicion_emg_cuello/adquisicion_emg_cuello.ino`, placa *Arduino UNO R4 WiFi*, subir.
   - Usa **A1**, como su código. El comentario de su sketch original dice A0: confirmen dónde está el cable.
   - En espera imprime lo mismo que su diagnóstico (`Bruto`, `Sin60`, `SinArm`): abran el **Serial Plotter a 250000** para ver los electrodos. **Ciérrenlo** antes de usar `grabar.py`: el puerto no se puede compartir.
   - Sigue mandando el RMS SinArm al ESP32 por D1, igual que antes.
4. **Ensayo sin Arduino** (no guarda nada en `data/raw/`):
   ```bash
   python code/grabar.py --sesion S01 --simular
   python code/check_quality.py --simulado
   python code/descargar_excel.py --simulado
   ```

## Paso 1. Llenar lo que solo ustedes saben

En `config/config.json` y en `PROTOCOL.md`, todo lo que dice **COMPLETAR**:

| Campo | Dónde se saca |
|---|---|
| `sensor_model`, `gain` | hoja de datos o diseño del sensor |
| tipo y orden del pasa-banda 40–450 Hz | su circuito (p. ej. Butterworth de 2.º orden); los límites ya están |
| `electrode_type`, `electrode_distance_cm` | la caja de los electrodos; distancia entre centros |
| `skin_preparation` | lo que hagan: apartar o rasurar pelo, alcohol, secar |
| Marcas A y B, distancia a la pared | medir con cinta y anotar en PROTOCOL.md, sección 4 |

Los tiempos (5, 1, 5, 4 s) son una **propuesta**: si los cambian, háganlo **antes** de S01 y vuelvan a generar el video con `python code/hacer_video_cue.py`.

## Paso 2. Piloto (antes de S01) — decide si seguimos

0. **Prueba del enlace**, sin la persona: `python code/grabar.py --probar-enlace`. Debe decir **ENLACE OK** (60 s, 60000 muestras, 0 huecos).

1. Electrodos en el esplenio izquierdo (PROTOCOL.md, sección 2). Marcas A (frente), B (arriba) y C (abajo).
2. `python code/grabar.py --piloto` (agreguen `--voz` en Mac). Tres veces.
3. Anoten neutro, arriba y abajo en la tabla de `DECISIONS.md`.
4. **Si "arriba" no sube claramente sobre "neutro", paren** y lo platicamos antes de grabar 100 intentos (otro sitio, otra marca B, u otra tarea).

## Paso 3. Sesiones de entrenamiento S01 a S10

En cada sesión:
1. Electrodos **nuevos**, colocados desde cero. Foto **sin cara** → `figures/placement_S01.jpg`.
2. Revisar contacto en el Serial Plotter (SinArm bajo en reposo, sube al levantar la cabeza). Cerrar el Plotter.
3. Grabar:
   ```bash
   python code/grabar.py --sesion S01 --voz
   ```
   - Enter para cada intento; la persona sigue los **tonos** (con la cabeza arriba no ve la pantalla).
   - Al terminar cada intento ven: muestras, huecos, saturación, Fs medida y RMS reposo/arriba.
   - **Enter** acepta. **r** lo marca rechazado (escriban por qué) y graba otro. Nada se sobrescribe.
   - Se detiene solo al llegar a **10 aceptados**. Si lo cortan, vuelvan a correrlo: sigue donde iba.
4. Calidad y subir:
   ```bash
   python code/check_quality.py
   git add data/raw data/metadata.csv QUALITY-REPORT.md figures/placement_S01.jpg
   git commit -m "Add session S01" -m "10 accepted. Why: training data. Checked with check_quality."
   git push
   ```
Hagan las 10 sesiones en **al menos dos días distintos**.

## Paso 4. Reporte 1 (sábado 23 de noviembre, 23:59)

- [ ] README.md: tabla del equipo y los números *(fill in)* (los da `check_quality.py`).
- [ ] PROTOCOL.md: sin COMPLETAR, y cada miembro agrega su línea "I read the method and I agree" **desde su cuenta**.
- [ ] DECISIONS.md: tabla del piloto; reescribir en sus palabras lo marcado *(AI draft)*.
- [ ] `rationale/M01.md`, ... (~100 palabras, cada quien la suya) y `ai-tools/M01.png`, ...
- [ ] Una foto por sesión en `figures/`; `figures/one_recording_marked.png` (la hace el notebook, celda 3).
- [ ] Al menos un commit de cada miembro. Mahdi como colaborador (Settings → Collaborators; el repo de ejemplo es de `MahdiTec`, confirmen que es su usuario).
- [ ] Tags: `git tag v0-first <commit del primer protocolo>` y, al entregar, `git tag v1-report`; luego `git push --tags`.

## Paso 5. Entrenar en Colab (con datos de GitHub)

1. Token de GitHub de **solo lectura**: GitHub → Settings → Developer settings → Fine-grained tokens → solo este repo → *Contents: Read-only*.
2. Colab → Archivo → Abrir → pestaña GitHub (marcar repos privados) → `notebooks/entrenamiento_colab.ipynb`.
3. Secrets (icono de llave): `GITHUB_TOKEN`. Corran las celdas 1 a 7.
4. Celda 6: tabla de modelos dejando una sesión fuera. Celda 7: escriban `MODELO_ELEGIDO` y guárdenlo (`models/modelo.joblib` y `models/modelo.json`). Suban `models/` y las figuras a GitHub.

## Paso 6. Azure (una vez, quien lleve la nube)

1. Azure for Students con el correo del Tec → cuenta de almacenamiento (una por grupo) → contenedor **`recordings`**, privado.
2. *Access keys* → copiar la **connection string**:
   - en la compu que graba: copiar `.env.example` como `.env` y pegarla ahí (`.env` no sube a GitHub);
   - en Colab: Secrets → `AZURE_STORAGE_CONNECTION_STRING`.
3. Para Mahdi: contenedor → *Shared access tokens* → permisos **Read** y **List**, con fecha de fin → mandarle el enlace. Nunca al repo.

## Paso 7. Clase final: prueba con electrodos nuevos

1. Cuatro colocaciones nuevas: `python code/grabar.py --sesion S11` ... `S14`. Van a `data/test_local/` (**no** a GitHub). En la prueba la pantalla **no** muestra el RMS: la prueba va sellada.
2. Después de cada sesión: `python code/subir_azure.py --sesion S11`. Nunca sobrescribe; sube el índice `P01/metadata_test.csv`.
3. Con el modelo ya elegido: notebook, celda 8, `ABRIR_TEST = True`, **una sola vez**. El resultado queda en `results/test_result.json`; súbanlo.

## Paso 8. Bajar los datos de una persona a Excel

```bash
python code/descargar_excel.py --fuente azure --participante P01            # prueba, desde Azure
python code/descargar_excel.py --fuente local --participante P01 --set train
python code/descargar_excel.py --fuente azure --participante P01 --sesion S11 --sin-senal
```
Queda en `salidas/P01_test.xlsx`: hoja LEEME, metadata, resumen (calidad y RMS por fase), ventanas de 100 ms con sus 6 características, y una hoja por grabación (cruda, en voltios y filtrada con SinArm). Con las 140 grabaciones el archivo pesa unos 90 MB: para algo ligero usen `--sesion` o `--sin-senal`. Bajar la prueba la **abre**: el script pide escribir `abrir`.

---

## Qué hace cada archivo

| Archivo | Qué hace |
|---|---|
| `arduino/adquisicion_emg_cuello/` | sketch de grabación (crudo a 1 kHz + SinArm al ESP32) |
| `arduino/diagnostico_emg_enlace/` | su sketch original, sin cambios |
| `config/config.json` | todos los valores fijos: persona, músculo, tiempos, sensor, reglas |
| `code/grabar.py` | piloto y sesiones, con tonos; escribe archivo y metadata |
| `code/check_quality.py` | aplica la regla y escribe `QUALITY-REPORT.md` |
| `code/subir_azure.py` | sube la prueba a Azure con su metadata |
| `code/descargar_excel.py` | una persona a `.xlsx` (desde Azure o local) |
| `code/hacer_video_cue.py` | genera `cue/cue-video.mp4` con los tiempos de config |
| `code/emg_cuello/` | las piezas: filtro SinArm, calidad, características, modelos, Azure, Excel |
| `code/tests/` | 16 pruebas con respuesta conocida |
| `notebooks/entrenamiento_colab.ipynb` | entrenamiento y prueba final |
