# Data dictionary

## `data/metadata.csv`: one row per recording
`code/grabar.py` writes the row when the recording ends. `code/check_quality.py` updates the quality columns. Fixed values come from `config/config.json`.

| Column | Meaning | Unit or allowed values |
|---|---|---|
| file_name | the file of the recording | `P01_S03_R07.csv` = person, session, recording |
| participant | code of the person | P01, never a name |
| session | one placement of the electrodes | S01 to S10 train, S11 to S14 test |
| date | day of the session | year-month-day |
| time_start | time the recording started | hour:minute:second |
| recording | number of the recording in its session | 1, 2, ... (a repeated trial gets the next number) |
| trials | trials in the file | always 1 |
| task | what the person does | text |
| muscle, side | where the sensor sits | splenius capitis, left |
| posture | how the person sits | text |
| rest_s, warning_s, move_s, between_s | the windows of one trial | seconds (5, 1, 5, 4) |
| fs_hz | planned sampling rate | hertz |
| adc_bits | bits of the converter | 14 |
| vref_v | reference voltage of the converter | volts |
| gain | gain of the sensor | number (from its datasheet) |
| sensor_model | the sensor | text |
| sensor_analog_filter | the filter inside the sensor | type, order, limits |
| electrode_type | the electrodes | text |
| electrode_distance_cm | distance between electrode centres | centimetres |
| ground_site | where the ground electrode sits | text |
| skin_preparation | how the skin was prepared | text |
| electrodes | when the electrodes were placed | new at the start of the session |
| cue | what the person follows | path of the cue video |
| firmware | version of the sketch that recorded the file | adq-v2 |
| set | use of the recording | train or test |
| n_samples | samples in the file | count (plan: 15000) |
| fs_measured_hz | sampling rate measured with `micros()` of the board | hertz |
| missing_pct | samples missing according to the counter of the board | percent of 15000 |
| late_samples | samples read more than 0.5 ms late | count |
| clipped_samples | samples at 0 or 16383 | count |
| operator_ok | the operator accepted the trial while recording | yes or no |
| operator_note | why the operator rejected it | text |
| trials_rejected | the quality rule rejected the trial | 0 or 1 |
| notes | the reason for each rejection | text |

## `data/raw/*.csv`: one row per sample
| Column | Meaning | Unit |
|---|---|---|
| sample | counter of the board, starts at 0 | count |
| time_ms | sample × 1000 / 1000 Hz | milliseconds |
| emg_adc | raw number from the converter, never filtered | 0 to 16383 |
| phase | the cue at that sample | rest, warning, move, between |

Labels for the model: `rest` = 0 (neutral neck), `move` = 1 (neck up). `warning` and `between` are not used to train.

## Other folders
| Folder | What it holds | In GitHub |
|---|---|---|
| `data/pilot/` | pilot files: neutral, up, neutral, down, neutral | yes |
| `data/test_local/` | test files on the recording laptop, before the upload | no |
| `data/azure_descarga/` | test files downloaded from Azure | no |
| `data/simulado/` | files made by the simulator, to practise without the board | no |
| `salidas/` | Excel files | no |
| `models/` | the trained model and its card (`modelo.json`) | yes |
| `results/` | the single test result (`test_result.json`) | yes |
