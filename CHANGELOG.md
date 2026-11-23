# Changelog

## 2026-11-19, sketch adq-v2
- The Arduino sends 10 samples per line instead of one (100 lines per second instead of 1000).
- The recorder stops with a message that says what failed (board restarted, link silent, damaged lines) instead of waiting forever. New mode `--probar-enlace`.
- Why: in the first pilot on Windows the link stopped after 4 s and after 23 s, and the recorder froze the second time.

## 2026-11-19
- Added the protocol, the acquisition sketch (`adq-v1`), the recorder with audio cues, the quality check, the upload to Azure, the export to Excel, the training notebook and the cue video.
- Why: everything must be ready before session S01, so the first recordings follow one written method.
