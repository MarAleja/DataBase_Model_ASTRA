# Decisions about what comes next

For each part: what we, or our AI tool, chose. The reason, in our own words. What we still do not understand.
We choose with the training sessions only, and we open the test sessions once, at the end.

> **Draft.** The lines marked *(AI draft)* were written by our AI tool (Claude) when it built the code. Each one must be rewritten in our own words before the report, or deleted.

## Pilot, before session S01
`python code/grabar.py --piloto`, three times. SinArm RMS without the first second of each phase:

| Pilot | Neutral (mV) | Up (mV) | Down (mV) | Up / neutral | Down / neutral |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |

**What it decides.** If "up" is not clearly above "neutral", the movement or the site must change before we record 100 trials. "Down" is recorded only here: it tells us if this muscle could also separate up from down later (project Atlas). Looking down also loads the neck extensors, so the two may look alike on this muscle.

## 7. Features
**Chose (provisional).** Windows of 100 ms without overlap, inside the rest and the movement windows, without the first second of each (the filter settles, the head is still moving). Six numbers per window: MAV, RMS, WL, ZC (time), MNF and MDF (frequency).
**Reason.** *(AI draft)* 100 ms is the same block in which the Arduino already computes the SinArm RMS that it sends to the ESP32, so a model that uses this RMS can run on the board without new code. Rest and movement give 40 windows each per trial, so the classes are balanced.
**Not understood yet.** Does a frequency feature add anything for two classes? The seven notch filters remove about 10 % of the band: does that change MNF and MDF?
**Sources.** MAV and RMS: course, video 8. MNF and MDF: De Luca 1984, as in course video 10.

## 8. Model
**Not decided yet.** `notebooks/entrenamiento_colab.ipynb` compares, leaving one training session out each time (new electrodes, like the test):

| Option | In plain words | What it keeps |
|---|---|---|
| Chance floor | always says the most common class | nothing |
| Threshold floor on RMS | "up if RMS is above this number" | one number |
| Logistic regression, RMS only | a border on one feature | two numbers |
| Logistic regression, 6 features | a straight border in 6 dimensions | seven numbers |
| k nearest neighbours, k = 5 | the 5 closest training windows vote | all training windows |
| Decision tree, depth 3 | at most 3 if-questions | a few rules |

Results (mean, worst session): write them here after running cell 6.
**Reason.** *(AI draft)* A model only counts if it beats both floors on sessions it never saw. If the threshold is as good, we keep the threshold: one number is easy to explain and to run on the board.
**Not understood yet.** COMPLETAR, in our own words.

## 9. Route
**Not decided yet.** Options:
1. The model runs in Python on a laptop. Each record goes to Azure Blob Storage with its metadata.
2. The model runs on the ESP32 as TinyML. It receives the SinArm RMS every 100 ms from the Arduino (already working, through the optocoupler). A threshold or a logistic regression on RMS is a few numbers in C. Each record goes to Azure.
**Reason.** *(AI draft)* Option 2 works without a computer and reuses the link we already have. It only fits if the chosen model uses RMS alone.
**Not understood yet.** How the ESP32 sends one record to Azure, and what one record must hold.
