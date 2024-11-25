#!/bin/bash

# This script creates a file containing log level counts for the various logs saved as part of a test run.

cd logs/

# DEVICE SERVER LOGS
# Log file names starting with ds- are assumed to be device server logs.
# Log level counts for each device server are populated in the device server table.
x=0
echo "DEVICE SERVER LOGS" >log_level_summary.txt
for LOGFILE in *; do
	if echo "$LOGFILE" | grep -q '^ds-'; then
		if [ $x == 0 ]; then
			echo "Logfile CRITICAL ERROR WARNING INFO DEBUG"
		fi
		echo "$LOGFILE $(grep "|CRITICAL|" $LOGFILE | wc -l) $(grep "|ERROR|" $LOGFILE | wc -l) $(grep "|WARNING|" $LOGFILE | wc -l) $(grep "|INFO|" $LOGFILE | wc -l) $(grep "|DEBUG|" $LOGFILE | wc -l)"
		x=1
	fi
done | column -t >>log_level_summary.txt

# EMULATOR LOGS
# Log file names starting with fhs-vcc-emulator- are assumed to be emulator logs.
# Log level counts for each device server are populated in the device server table.
x=0
echo -e "\nEMULATOR LOGS" >>log_level_summary.txt
for LOGFILE in *; do
	if echo "$LOGFILE" | grep -q '^fhs-vcc-emulator-'; then
		if [ $x == 0 ]; then
			echo "Logfile CRITICAL ERROR WARNING INFO DEBUG"
		fi
		echo "$LOGFILE $(grep "|CRITICAL|" $LOGFILE | wc -l) $(grep "|ERROR|" $LOGFILE | wc -l) $(grep "|WARNING|" $LOGFILE | wc -l) $(grep "|INFO|" $LOGFILE | wc -l) $(grep "|DEBUG|" $LOGFILE | wc -l)"
		x=1
	fi
done | column -t >>log_level_summary.txt

# DATABASE LOGS
# Log file names starting with database are assumed to be database logs.
# Log level counts for each database log are populated in the database table.
echo -e "\nDATABASE LOGS" >>log_level_summary.txt
x=0
for LOGFILE in *; do
	if echo "$LOGFILE" | grep -q '^database'; then
		if [ $x == 0 ]; then
			echo "Logfile ERROR WARNING NOTE"
		fi
		echo "$LOGFILE $(grep '\[Error' $LOGFILE | wc -l) $(grep '\[Warn' $LOGFILE | wc -l) $(grep '\[Note' $LOGFILE | wc -l)"
		x=1
	fi
done | column -t >>log_level_summary.txt

echo "Log level summary capture complete."
