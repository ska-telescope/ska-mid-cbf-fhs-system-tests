#!/bin/bash

# This script creates a file containing log level counts for the various logs saved as part of a test run.

cd logs/

# DEVICE SERVER LOGS
# Log file names starting with ds- are assumed to be device server logs. 
# Log level counts for each device server are populated in the device server table.
x=0
echo "DEVICE SERVER LOGS" > log_level_summary.txt
for LOGFILE in *; do 
if echo "$LOGFILE" | grep -q '^ds-'
then
   if [ $x == 0 ]
   then
      echo "Logfile CRITICAL ERROR WARNING INFO DEBUG"
   fi
   echo "$LOGFILE $(grep "|CRITICAL|" $LOGFILE | wc -l) $(grep "|ERROR|" $LOGFILE | wc -l) $(grep "|WARNING|" $LOGFILE | wc -l) $(grep "|INFO|" $LOGFILE | wc -l) $(grep "|DEBUG|" $LOGFILE | wc -l)"
   x=1
fi
done | column -t >> log_level_summary.txt

# CONSUMER LOGS
# Log level counts for each tango device in the talondxlogconsumer are populated in the consumer table.
# File is read in and each line with a tango device name and log level are extracted and sorted.
echo -e "\nCONSUMER LOGS" >> log_level_summary.txt
input="ds-talondxlogconsumer-001-0.log"
while IFS= read -r line
do
if echo "$line" | grep -q 'tango-device:'
  then 
  tangodevicefull=$(echo "$line" | cut -d "|" -f 7)
  tangodevice=$(echo $tangodevicefull | sed s/"tango-device:"//)
  if [ $(echo $tangodevicefull | head -c 13) == "tango-device:" ]
    then
    loglevel=$(echo "$line" | cut -d "|" -f 3)
    echo $tangodevice $loglevel >> consumer-raw.txt
  fi
fi
done < "$input"
sort -o consumer-sorted.txt consumer-raw.txt 
# Sorted list of tango devices and log levels is read in and counts are calculated
y=0
input2="consumer-sorted.txt"
while IFS= read -r line
do
if [ $y == 0 ]
   then
      echo "tango-device CRITICAL ERROR WARNING INFO DEBUG"
fi
tangodevicename=$(echo "$line" | cut -d " " -f 1)
if [ "$lasttangodevice" != "$tangodevicename" ]
then
  echo "$tangodevicename $(grep "$tangodevicename CRITICAL" consumer-sorted.txt | wc -l) $(grep "$tangodevicename ERROR" consumer-sorted.txt | wc -l) $(grep "$tangodevicename WARNING" consumer-sorted.txt | wc -l) $(grep "$tangodevicename INFO" consumer-sorted.txt | wc -l) $(grep "$tangodevicename DEBUG" consumer-sorted.txt | wc -l)"

  lasttangodevice=$(echo "$line" | cut -d " " -f 1)
  y=1

fi
done < "$input2" | column -t >> log_level_summary.txt

# DATABASE LOGS
# Log file names starting with database are assumed to be database logs. 
# Log level counts for each database log are populated in the database table.
echo -e "\nDATABASE LOGS" >> log_level_summary.txt
x=0
for LOGFILE in *; do 
if echo "$LOGFILE" | grep -q '^database'
then
   if [ $x == 0 ]
   then
      echo "Logfile ERROR WARNING NOTE"
   fi
   echo "$LOGFILE $(grep '\[Error' $LOGFILE | wc -l) $(grep '\[Warn' $LOGFILE | wc -l) $(grep '\[Note' $LOGFILE | wc -l)"
   x=1
fi
done | column -t >> log_level_summary.txt

echo "Log level summary capture complete."