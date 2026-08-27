# RobotCAD Try-1: Image+Text RMDG

Try-1 evaluates whether a predicted Robot Mechanical Design Graph (RMDG) is a
useful intermediate representation for blind Image+Text robot CAD generation.
It reuses the audited 15-case Go/No-Go 3 development set, but does not alter
the earlier experiment or its frozen Qwen provenance.

## Commands

```powershell
.\.venv\Scripts\python.exe try1\scripts\build_inputs.py
.\.venv\Scripts\python.exe try1\validators\validate_image_text_input_v1.py try1\inputs\image_text_v1\dev_arm-0573e1e127.json
.\.venv\Scripts\python.exe try1\validators\validate_rmdg_v1.py try1\examples\rmdg_v1\valid_serial_arm.json
.\.venv\Scripts\python.exe try1\scripts\run_try1.py --condition D1 --case dev_arm-0573e1e127
.\.venv\Scripts\python.exe try1\scripts\run_try1.py --condition D2 --case dev_arm-0573e1e127
.\.venv\Scripts\python.exe try1\scripts\run_try1.py --condition G1 --case dev_arm-0573e1e127
.\.venv\Scripts\python.exe try1\scripts\run_try1.py --condition O_GT --case dev_arm-0573e1e127
.\.venv\Scripts\python.exe try1\scripts\aggregate_try1.py
```

`runs/` is deliberately ignored: it contains raw API responses and generated
CAD. The frozen input manifest, configuration, results and reports are tracked.
