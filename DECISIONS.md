# Decisions about what comes next

For each part: what we, or our AI tool, chose. The reason, in our own words. What we still do not understand.
We choose with the training sessions only, and we open the test sessions once, at the end.

## Pilot, before session S01
`python code/grabar.py --piloto`, three times. SinArm RMS without the first second of each phase:

| Pilot | Neutral (mV) | Up (mV) | Down (mV) | Up / neutral | Down / neutral |
|---|---|---|---|---|---|
| 1 | 15.96 | 15.78| 16.05 | 0.99 | 1.01 |
| 2 | 4.37 | 4.69 | 3.71 | 1.07| 0.85 |
| 3 | | | | | |

**What it decides.** If "up" is not clearly above "neutral", the movement or the site must change before we record 100 trials. "Down" is recorded only here: it tells us if this muscle could also separate up from down later (project Atlas). Looking down also loads the neck extensors, so the two may look alike on this muscle.

## 7. Features
**Chose (provisional).** Windows of 100 ms without overlap, inside the rest and the movement windows, without the first second of each (the filter settles, the head is still moving). Six numbers per window: MAV, RMS, WL, ZC (time), MNF and MDF (frequency).
**Reason.** 100 ms is the same block in which the Arduino already computes the SinArm RMS that it sends to the ESP32, so a model that uses this RMS can run on the board without new code. Rest and movement give 40 windows each per trial, so the classes are balanced.
**Not understood before.** Does a frequency feature add anything for two classes? The seven notch filters remove about 10 % of the band: does that change MNF and MDF?
**What we learned** Initially, we were unsure whether frequency-domain features would help distinguish the two classes. After training the models, we observed that the selected Decision Tree used mainly WL and MDF in its decision rules. This suggests that both time-domain signal variation and frequency information contributed to the classification in our training data.

However, the fact that MDF appears in the tree does not prove that frequency features improve accuracy. To confirm this, we would need to compare models trained with and without MNF and MDF.

We also recognize that the seven notch filters remove portions of the EMG frequency spectrum, which may affect MNF and MDF. Since all recordings were processed using the same filtering pipeline, the features were calculated consistently. Nevertheless, we have not quantified how much the notch filters change these frequency features.

**AI contribution**. MAV, RMS, MNF, and MDF were selected based on concepts covered in the course. WL and ZC were suggested by AI as additional time-domain features. We reviewed their definitions and included them in the model comparison. The AI also helped organize the feature extraction and training code.

**Sources**. MAV and RMS: course, video 8. MNF and MDF: De Luca (1984), as referenced in course video 10. WL and ZC: AI-assisted feature suggestions; their implementation is documented in the project's Python code.

## 8. Model
**Decision Tree classifier with a maximum depth of 3 and six input features (MAV, RMS, WL, ZC, MNF, and MDF)** to distinguish between rest (class 0) and neck extension (class 1). `notebooks/entrenamiento_colab.ipynb` compares, leaving one training session out each time (new electrodes, like the test):

| Option | In plain words | What it keeps |
|---|---|---|
| Chance floor | always says the most common class | nothing |
| Threshold floor on RMS | "up if RMS is above this number" | one number |
| Logistic regression, RMS only | a border on one feature | two numbers |
| Logistic regression, 6 features | a straight border in 6 dimensions | seven numbers |
| k nearest neighbours, k = 5 | the 5 closest training windows vote | all training windows |
| Decision tree, depth 3 | at most 3 if-questions | a few rules |

**Cross-validation results**
| Model | Mean Accuracy | Standard deviation | Worst session |
|Logistic regression (6 features) | 86.8% | 9.3 percentage points | 71.2% |
|Decision tree, depth 3 (6 features) | 87.7% | 8.0 percentage points | 73.9% |
**Reason.** 
### Model Selection and Justification

We selected a **Decision Tree classifier with a maximum depth of 3 and six input features (MAV, RMS, WL, ZC, MNF, and MDF)** to distinguish between rest (class 0) and neck extension (class 1).

The model achieved a mean accuracy of **87.7%** using leave-one-session-out cross-validation, with a standard deviation of approximately 8.0 percentage points and a minimum session accuracy of 73.9%. Although its performance was similar to that of logistic regression (86.8% mean accuracy), the decision tree was selected because it provided slightly higher average accuracy and more interpretable classification rules.

One important advantage of the decision tree is that its predictions can be explained through a small number of decision rules. Although six features were provided as inputs, the trained tree mainly used **Waveform Length (WL)** and **Median Frequency (MDF)** to distinguish between the two classes. This allows us to better understand which signal characteristics contribute to the classification.

Additionally, limiting the tree to a maximum depth of three helps control model complexity and reduces the risk of overfitting. The model was evaluated by separating entire recording sessions rather than randomly splitting individual windows, providing a more realistic assessment of its performance with different electrode placements.

Overall, the decision tree offered a good balance between classification accuracy, simplicity, and interpretability. However, its performance on the final unseen test sessions (S11–S14) still needs to be evaluated before confirming its generalization ability.

## 9. Route
1. The model runs in Python on a laptop. Each record goes to Azure Blob Storage with its metadata.
  The Arduino UNO R4 WiFi acquires the EMG signal and sends the raw samples to a laptop through USB. Python processes the signal using the SinArm filtering pipeline, extracts the six features (MAV, RMS, WL, ZC, MNF, and MDF) and uses the trained Decision Tree classifier to predict rest (class 0) or neck extension (class 1). 
**Reason.** We selected this route because our Decision Tree uses more than RMS alone. Although the ESP32 can already receive SinArms RMS values through the optocouplers, those values are not sufficient to reproduce the selected model. Running the classifier in Python allows us to reuse the same filtering and feature extraction pipeline used during training, without implementing additional signal processing on the ESP32.
This option also makes it easier to inspect predictions, identify errors, and update the model during development. However, it requires a connected laptop, making the system less portable than an ESP32-based implementation.
**What one record should contain**. Each recording should include the participant code, session ID, trial ID, acquisition date, sampling frequency, raw EMG samples, phase labels, and quality information. The model predictions and the model version can be stored as additional metadata or in a separate results file.
**Not implemented yet**. The connection between the Python application and Azure Blob Storage still needs to be completed and tested.
**Not understood yet.** How the ESP32 sends one record to Azure, and what one record must hold.

