# Talon DX Tango Device Log Utility
The `log_analysis.py` utility loads the Talon log messages received from the Talon DX boards and filters them according the contents of `query.yaml`.

## Reference
* [SKA log message format](https://developer.skatelescope.org/en/latest/tools/logging-format.html#ska-log-message-format)

## Dump the Talon DX Logs from the Log Consumer
```bash
kubectl logs ds-talondxlogconsumer-001-0 -n ci-ska-skampi-cbf-automated-pipeline-testing-mid > talondxlogconsumer.log
```

## Configure the Query YAML
### Example: filter by time range, device type and log level 
```yaml
log_file: talondxlogconsumer-5-May-2023.log
log_out:  filtered.log
time_start: 2023-05-05T11:12:00.000Z
time_end:   2023-05-05T11:15:00.000Z
tango_device: vcc|slim|lstv
severity: INFO|DEBUG
message: ""
```
Filters all log messages with "vcc", "slim" or "lstv" devices logging at "INFO" or "DEBUG" between the times specified.

### Example: all error messages
All fields are required. To see all timestamps, set the time range to be wider than those in the file. To see all devices, set the field to "".  
e.g.,
```yaml
log_file: talondxlogconsumer-5-May-2023.log
log_out:  filtered.log
time_start: 2023-01-01T00:00:00.000Z
time_end:   2024-01-01T00:00:00.000Z
tango_device: ""
severity: ERROR
message: ""
```
Shows all error log messages.

### Example: messages containing substring
```yaml
log_file: talondxlogconsumer-5-May-2023.log
log_out:  filtered.log
time_start: 2023-01-01T00:00:00.000Z
time_end:   2024-01-01T00:00:00.000Z
tango_device: hps
severity: ""
message: "'device name' ="
```
Shows all messages containing `'device name' =`, which gives a list of all HPS devices being configured by the HPS Master device.   

## Initial Setup
Python virtual environment setup as required:
```bash
python3 -m venv ~/dev/mypyenv
source ~/dev/mypyenv/bin/activate
pip install -r requirements.txt
```
Note: `log_analysis` ran successfully on Python 3.8.10.

## Generate the Filtered Log File
```bash
./log_analysis.py
```
to output to the `log_out` file specified in `query.yaml`.
