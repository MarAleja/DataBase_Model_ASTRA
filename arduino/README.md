# Arduino

- `adquisicion_emg_cuello/`: the sketch we record with (version `adq-v2`, 10 samples per line). Same sampling, pin, ADC and SinArm filter as our diagnostic sketch. It sends each raw sample to the laptop only when `code/grabar.py` asks for it, and keeps sending the SinArm RMS to the ESP32 every 100 ms.
- `diagnostico_emg_enlace/`: our original diagnostic sketch, unchanged.
