#!/usr/bin/env python3

import os
import sys
import yaml
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
THIS_DIR = os.path.dirname(os.path.abspath(__file__))

time_format = '%Y-%m-%dT%H:%M:%S.%fZ'
log_fields = ['VERSION', 'TIMESTAMP', 'SEVERITY', 'THREAD-ID', 'FUNCTION', 'LINE-LOC', 'TANGO-DEVICE', 'MESSAGE']

if __name__ == "__main__":
    with open("query.yaml", "r") as stream:
        query = yaml.safe_load(stream)
        print(f"Log search query:\n{yaml.dump(query)}")

    # Load the logs into a dataframe and set the columns
    file = os.path.join(THIS_DIR, query['log_file'])
    print(f"Loading logs from {file}...")
    df = pd.read_csv(filepath_or_buffer=file, sep='|', header=0, names=log_fields)

    # Remove unnecessary columns
    df2 = df.drop(['VERSION', 'FUNCTION', 'THREAD-ID'], axis=1)

    df_out = df2.loc[(df2['TIMESTAMP'] >= query['time_start'].strftime(time_format)) &
                     (df2['TIMESTAMP'] < query['time_end'].strftime(time_format)) &
                     df2['TANGO-DEVICE'].str.contains(query['tango_device'], na=False) &
                     df2['SEVERITY'].str.contains(query['severity']) &
                     df2['MESSAGE'].str.contains(query['message'])]

    print(df_out.head(n=20))

    file_out = os.path.join(THIS_DIR, query['log_out'])
    print(f"Writing filtered logs to {file_out}...")
    df_out.to_csv(path_or_buf=file_out, sep='\t')
    