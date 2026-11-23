# Code

Each script starts with what it does and who wrote it. Run them from the root of the repository. Step by step: `PASO-A-PASO.md`.

| File | What it does |
|---|---|
| `grabar.py` | records the pilot and the sessions, with audio cues; writes each file and its row of metadata |
| `check_quality.py` | applies the quality rule and writes `QUALITY-REPORT.md` |
| `subir_azure.py` | uploads the test sessions to Azure with their metadata |
| `descargar_excel.py` | downloads one person (Azure or local) to an Excel file |
| `hacer_video_cue.py` | makes `cue/cue-video.mp4` from the times in `config/config.json` |
| `emg_cuello/` | the parts: SinArm filter, quality, features, models, Azure, Excel |
| `tests/` | one test with a known answer for each part: `python -m pytest code/tests -q` |
