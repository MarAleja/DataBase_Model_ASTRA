# DataBase_sEMD_adq: neck up or neutral, from the left splenius capitis

Course: M6 Machine Learning and IoT apps. Report 1, the data stage.
Project: tell "neck up" from "neutral neck" with one surface EMG channel on the left splenius capitis of one person, on sessions with new electrodes that the model never saw. Goal: more than 75 % right.

> **Status: protocol and code ready, no recordings yet.** Lines marked *(fill in)* get their numbers after recording. `python code/check_quality.py` gives most of them.

## The team

| Member code | GitHub user | In charge of | AI tool |
|---|---|---|---|
| M01 | @Aleja246 | COMPLETAR | COMPLETAR |
| M02 | COMPLETAR | COMPLETAR | COMPLETAR |
| M03 | COMPLETAR | COMPLETAR | COMPLETAR |

Every member has at least one commit. We measure one person. In the data that person has the code P01.

## The six parts

### 1. Data acquisition
Plan: 100 training recordings, one trial each, 10 sessions, 1 person. Electrodes COMPLETAR (type), COMPLETAR cm apart, on the left splenius capitis. Arduino UNO R4 WiFi, 14 bits, 1000 samples per second, measured on the board with `micros()`.
Result *(fill in)*: N recordings, N trials, N sessions.
**Evidence:** `data/raw/`, `data/metadata.csv`, `cue/cue-video.mp4`.

### 2. Task
Seated. Raise the head from mark A (eye level) to mark B and hold it. Two classes: neck up (movement) and neutral neck (rest).
**Evidence:** `PROTOCOL.md`, sections 4 and 5. Photos in `figures/`.

### 3. Trial and cue timing
| Window | Seconds | What the person sees and hears |
|---|---|---|
| Rest | 0 to 5 | REPOSO, a low tone |
| Warning | 5 to 6 | PREPÁRATE, a high tone |
| Movement | 6 to 11 | ARRIBA, a long tone |
| Return | 11 to 15 | REGRESA, two low tones |

One trial per file, 15 s. Tones, because the person cannot see the screen with the head up.
**Evidence:** `cue/cue-video.mp4`, the columns `rest_s`, `warning_s`, `move_s`, `between_s`, `figures/one_recording_marked.png`.

### 4. Sessions
Plan: 10 training sessions on at least 2 days, 10 accepted recordings each. New electrodes, placed again from zero, at the start of every session.
Result *(fill in)*: sessions on N days.
**Evidence:** the columns `session` and `date` of `data/metadata.csv`, one photo per session in `figures/`.

### 5. Cleaning
Filters: DC removal (first order high-pass, 0.48 Hz) and seven notch filters at 60 Hz and its harmonics up to 420 Hz (Q = 20), the same chain as our Arduino sketch. Analog band-pass of the sensor: 40 to 450 Hz, so no digital band-pass. Type, order, limits and sources in `PROTOCOL.md`, section 9. The raw files are never changed.
Rule, written before any score: reject a recording if a sample hits 0 or 16383, if more than 1 % of samples are missing, if its length or its sampling rate is more than 2 % off, or if the operator rejected it.
Result *(fill in)*: N of N rejected.
**Evidence:** `QUALITY-REPORT.md`, `code/check_quality.py`.

### 6. Fair split
Training: sessions S01 to S10, in GitHub. Test: sessions S11 to S14, 4 new placements in the final class, only in Azure. No session is in both. Model choice with one training session left out each time. Limit: one person and one movement; we do not claim it works for other people.
**Evidence:** the column `set` of `data/metadata.csv`.

## What comes next
`DECISIONS.md` (features, model, route). `rationale/` (one file per member).

## How to repeat our recording
`PROTOCOL.md` is enough to record the same way. `PASO-A-PASO.md` is our step-by-step guide (in Spanish).

| What | Command |
|---|---|
| Install | `pip install -r requirements.txt` |
| Practise without the board | `python code/grabar.py --sesion S01 --simular` |
| Pilot | `python code/grabar.py --piloto` |
| Record a session | `python code/grabar.py --sesion S01` |
| Quality report | `python code/check_quality.py` |
| Upload a test session | `python code/subir_azure.py --sesion S11` |
| One person to Excel | `python code/descargar_excel.py --fuente azure --participante P01` |
| Train | `notebooks/entrenamiento_colab.ipynb` in Google Colab |
| Tests | `python -m pytest code/tests -q` |

## Where to search
- Wilson and others, *Good enough practices in scientific computing*, PLOS Computational Biology 2017.
- Merletti, *Standards for Reporting EMG Data*, ISEK 1999, and CEDE-Check.
- Riascos Salas, Molinas and Lotte, *Machine learning methods for BCI*, ESANN 2024.
- scikit-learn user guide. emlearn, for models on a microcontroller.

## Versions
Tags `v0-first` and `v1-report`.
