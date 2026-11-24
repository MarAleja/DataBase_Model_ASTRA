# Protocol

Written so that a person outside the group can repeat the recording. Fields marked **COMPLETAR** are facts only our group can write (our sensor, our electrodes, our marks). They are also in `config/config.json`, which copies them into `data/metadata.csv`.

## 1. Person and consent
One person, code **P01**. The person signs the consent form before the first recording. Files and photos carry the code, never a name or a face.

## 2. Muscle, site and electrodes
- **Muscle:** left splenius capitis. It extends the neck and turns the head to its own side (Mayoux-Benhamou et al. 1997). With surface electrodes it can be reached in most people (Joines et al. 2006).
- **Site:** over the muscle belly at the level of C2/C3, between the uppermost parts of the trapezius and the sternocleidomastoid (Gosselin and Fagan 2014, Table 2, after Strimpakos et al.). Electrodes in line with the muscle fibres (SENIAM, general rule).
- **How we find it:** the person turns the head a little to the left and raises it against light resistance of a hand. The muscle hardens between the two muscles named above. This test contraction comes from the dataset paper (Fuentes-Aguilar et al. 2024), adapted to the neck.
- **Ground electrode:** spinous process of C7 (Gosselin and Fagan 2014, Table 2).
- **Electrodes:** Disposable Ag/AgCl surface electrode, Brand: Medi-Trace, Size: 35 - 38 mm. New electrodes in every session.
- **Distance between electrode centres:** 2 cm.
- **Skin preparation:** Hair moved away from the recording area and skin was cleaned with alcohol. 
- **Photo:** one photo of the electrodes per session, no face: `figures/placement_S01.jpg`, ...

## 3. Sensor and acquisition
- **Sensor:** surface EMG model, gain 10000. Analog band-pass filter from 40 to 450 Hz inside the sensor (Sallen-Key, 8th Order).
- **Board:** Arduino UNO R4 WiFi, input A1, ADC of 14 bits (0 to 16383), reference 5.0 V.
- **Sampling:** 1000 Hz. The sketch `arduino/adquisicion_emg_cuello/adquisicion_emg_cuello.ino` (version `adq-v2`) reads one sample every 1000 µs with `micros()`, the same loop as our diagnostic sketch.
- **Transfer:** USB at 250000 baud, 10 samples per line (`n0:a0,...,a9`, with `n0` the counter of the board for the first sample). One sample per line (version `adq-v1`) stopped the USB link of the UNO R4 WiFi after a few seconds. Every 1000 samples the board sends its `micros()` time, so `code/grabar.py` measures the real sampling rate (column `fs_measured_hz`) and finds missing samples (column `missing_pct`).
- **File:** one CSV per trial in `data/raw/`, columns `sample, time_ms, emg_adc, phase`. Raw counts, never filtered. The phase of each sample comes from the counter of the board, not from the clock of the laptop.

## 4. Posture and marks
- Seated, back against the chair, hands on the thighs, feet flat. Same chair and same distance to the wall in every session: 92 cm.
- **Mark A** on the wall in front, at eye level: neutral neck.
- **Mark B** above mark A, at a height the person reaches with a comfortable extension, not the maximum: 15cm (height or angle).
- **Mark C** below mark A, only for the pilot (head down).

## 5. Task and classes
Two classes:
- **Movement (label 1):** raise the head from mark A to mark B and hold it there.
- **Rest (label 0):** neutral neck, looking at mark A, shoulders relaxed.

## 6. Trial and cues
| Window | Seconds | What the person sees and hears |
|---|---|---|
| Rest | 0 to 5 | REPOSO, a low short tone |
| Warning | 5 to 6 | PREPÁRATE, a high short tone |
| Movement | 6 to 11 | ARRIBA, one long tone |
| Return | 11 to 15 | REGRESA, two low tones |

One trial per file, 15 s, 15000 samples. The tones matter: with the head up the person cannot see the screen. `code/grabar.py` plays them at the exact sample where each phase starts (with `--voz`, macOS also says the word). `cue/cue-video.mp4` shows the same sequence.

Why these times: 5 s of movement, as each movement in the dataset paper (Fuentes-Aguilar et al. 2024). 5 s of rest, so both classes have the same amount of signal. 4 s to come back and relax before the next file.

## 7. Sessions and split
- A session is one placement of the electrodes. 10 accepted recordings per session.
- **Training:** sessions S01 to S10, 100 accepted recordings, on at least two different days. In GitHub.
- **Test:** sessions S11 to S14 in the final class, 4 new placements, 40 recordings. Only in Azure, never in GitHub, never used to train. Opened once, at the end.
- The operator starts each trial when the person says they are ready.

## 8. Pilot (before session S01)
`python code/grabar.py --piloto`, three times: neutral 5 s, up 5 s, neutral 5 s, down 5 s, neutral 5 s. It prints the SinArm RMS of each phase. It tells us if this muscle separates "up" from "neutral" before we record 100 trials. Results in `DECISIONS.md`.

## 9. Filters
1. **Analog, in the sensor:** band-pass from 40 to 450 Hz (type and order: Sallen-Key, 8th order; source: Analog filter circuit schematic and design calculations developed by the team . 450 Hz is below 500 Hz, half the sampling rate: 1000 Hz is more than 2 × 450 = 900 Hz. The low limit of 40 Hz also removes most of the drift and electrode movement, which sits below 20 Hz (De Luca et al. 2010).
2. **Digital, after recording, in this order** (`code/emg_cuello/filtros.py`, the same code as our sketch):
   1. Counts to volts: `v = adc × 5.0 / 16383`.
   2. **DC removal:** exponential average `dc += 0.003 × (v − dc)`, then `x = v − dc`. A first order high-pass, −3 dB at 0.48 Hz at 1000 Hz. In each file the average starts at the mean of the first 200 samples.
   3. **Seven notch filters in series** at 60, 120, 180, 240, 300, 360 and 420 Hz, Q = 20. Each one is a second order IIR (biquad) with the formulas of the Audio EQ Cookbook (R. Bristow-Johnson). The −3 dB width is 2.9 Hz at 60 Hz and 3.8 Hz at 420 Hz. 60 Hz is the frequency of the power line in Mexico.
   Together, the notch filters remove about 10 % of our 40 to 450 Hz band at −3 dB. We measured this in code, and it is an open question in `DECISIONS.md`.
3. **No digital band-pass.** The analog filter already sets the band, 40 to 450 Hz. The course uses 20 to 450 Hz (McManus et al. 2020); our low limit is higher, so the signal between 20 and 40 Hz is not in our files.

The Python filter equals the sketch: on 20000 synthetic test samples, the largest difference with the C++ code of the sketch was 2.8 µV, for a signal of 17 mV RMS (float32 rounding).

## 10. Quality rule, written before any score
Reject a recording if a sample sits at the limit of the converter (0 or 16383), if more than 1 % of its samples are missing, if its length is more than 2 % away from 15000 samples, if the measured sampling rate is more than 2 % away from 1000 Hz, or if the operator rejected it. `code/check_quality.py` applies the rule and writes `QUALITY-REPORT.md`. Files in `data/raw/` are never changed.

## 11. Repeat a trial when
The person moves at the wrong time, an electrode comes loose, a sample hits the limit, or the file is short. The rejected file stays in `data/raw/` with its reason. The recorder never overwrites a file.

## Sources
- Fuentes-Aguilar et al. 2024, Data in Brief 57, 111079: the dataset paper of the course.
- Gosselin G, Fagan MJ. The effects of cervical muscle fatigue on balance. Journal of Sports Science and Medicine 2014, 13(2): 329–337, Table 2.
- Joines SMB, Sommerich CM, Mirka GA, Wilson JR, Moon SD. Low-level exertions of the neck musculature: a study of research methods. J Electromyogr Kinesiol 2006, 16(5): 485–497.
- Mayoux-Benhamou MA, Revel M, Vallee C. Selective electromyography of dorsal neck muscles in humans. Exp Brain Res 1997, 113: 353–360.
- McManus et al. 2020, Frontiers in Neurology 11: 576729 (band 20 to 450 Hz, as used in the course).
- De Luca CJ et al. 2010, Journal of Biomechanics 43: 1573 (movement artifact below 20 Hz, as cited in course video 13).
- Bristow-Johnson R. Audio EQ Cookbook (W3C note): notch biquad formulas.
- SENIAM, seniam.org: electrodes in line with the muscle fibres.

## We read the method and we agree
Each member adds their own line, from their own GitHub account, in their own commit:

<!-- M01, 2026-11-20, I read the method and I agree. -->
<!-- M02, 2026-11-23, I read the method and I agree. -->
<!-- M03, 2026-11-23, I read the method and I agree. -->
