import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

def load_frame_metadata(path):
    # Load the JSON Data
    with open(path, 'r') as file:
        data = json.load(file)

    # Extract Data and Create DataFrame
    p0_data = data['p0']  # p0 is a list of the frames at Position 0 (artifact of hardware sequencing in MMCore)
    df = pd.DataFrame(p0_data)  # dataframe it

    # Expand 'camera_metadata' into separate columns
    camera_metadata_df = pd.json_normalize(df['camera_metadata'])
    df = df.join(camera_metadata_df)

    return df

def load_metadata(directory):
    frame_metadata_df = None
    pupil_frame_metadata_df = None

    # Parse the directory for files ending with '_frame_metadata.json' and 'pupil_frame_metadata.json'
    for file in os.listdir(directory):
        if file.endswith('widefield_frame_metadata.jsonf'): #need an 'f' after json???????????????????
            frame_metadata_path = os.path.join(directory, file)
            frame_metadata_df = load_frame_metadata(frame_metadata_path)
        elif file.endswith('pupil_frame_metadata.jsonf'):
            pupil_frame_metadata_path = os.path.join(directory, file)
            pupil_frame_metadata_df = load_frame_metadata(pupil_frame_metadata_path)

    return frame_metadata_df, pupil_frame_metadata_df

def plot_camera_intervals(frame_metadata_df, pupil_frame_metadata_df, threshold=1):
    
    def process_dataframe(df, label):
        df['TimeReceivedByCore'] = pd.to_datetime(df['TimeReceivedByCore'], format='%Y-%m-%d %H:%M:%S.%f')  # Convert to datetime
        df['runner_time_ms'] = df['runner_time_ms'].astype(float)  # Convert to float

        # Compute Time Intervals Between Frames
        df = df.sort_values('TimeReceivedByCore').reset_index(drop=True)
        df['runner_interval'] = df['runner_time_ms'].diff()  # Compute differential
        df['time_received_ms'] = df['TimeReceivedByCore'].astype(np.int64) / 1e6  # Convert to milliseconds
        df['core_interval'] = df['time_received_ms'].diff()  # Compute differential

        # Compute Differences Between Intervals
        df['interval_difference'] = df['runner_interval'] - df['core_interval']
        
        # Plot the data
        plt.plot(df['TimeReceivedByCore'], df['interval_difference'], label=label)
    
    plt.figure(figsize=(10, 6))
    
    if frame_metadata_df is not None:
        process_dataframe(frame_metadata_df, 'Dhyana')
    
    if pupil_frame_metadata_df is not None:
        process_dataframe(pupil_frame_metadata_df, 'ThorCam')
    
    plt.axhline(y=threshold, color='r', linestyle='--', label='Threshold')
    plt.xlabel('Time Received By Core')
    plt.ylabel('Interval Difference (ms)')
    plt.title('Interval Differences Over Time')
    plt.legend()
    plt.grid(True)

    plt.show()

def load_wheel_data(directory) -> pd.DataFrame:

    # Parse the beh_path directory for a file ending with 'wheel_df.csv'
    path = os.path.join(os.path.dirname(directory), 'beh')
    for file in os.listdir(path):
        if file.endswith('wheeldf.csv'):
            file_path = os.path.join(path, file)
            break
    df = pd.read_csv(file_path)
    # Create a pandas dataframe
    return df
    
def plot_wheel_data(wheel_df: pd.DataFrame):
    # Calculate the time difference in seconds
    total_seconds = wheel_df['timestamp'].array[-1] - wheel_df['timestamp'][0]  # Get Range
    time = np.arange(0, total_seconds, 1)  # create array [0,1,...12] with the total_seconds

    # Create separate plots for each variable
    plt.figure(figsize=(10, 6))#, dpi=300)

    # Plot 'speed' over time
    plt.subplot(3, 1, 1)
    plt.plot(wheel_df['timestamp'], wheel_df['speed'])
    plt.title('Speed')
    plt.xlabel('Time (secs)')
    plt.ylabel('Speed')

    # Plot 'distance' over time
    plt.subplot(3, 1, 2)
    plt.plot(wheel_df['timestamp'], wheel_df['distance'])
    plt.title('Distance')
    plt.xlabel('Time (secs)')
    plt.ylabel('Distance')

    # Plot 'direction' over time
    plt.subplot(3, 1, 3)
    plt.plot(wheel_df['timestamp'], wheel_df['direction'])
    plt.title('Direction')
    plt.xlabel('Time (secs)')
    plt.ylabel('Direction')

    # Adjust the layout
    plt.tight_layout()

    # Show the plots
    plt.show()

    # # Reverse (flip) backwards data due to wrong encoder direction
    # wheel_df['speed'] = wheel_df['speed'] * -1
    # wheel_df['distance'] = wheel_df['distance'] * -1

    # return wheel_df

def load_psychopy_data(directory):
    # Parse the beh_path directory for a file ending with 'wheel_df.csv'
    path = os.path.join(os.path.dirname(directory), 'beh')
    for file in os.listdir(path):
        if file.endswith('.csv'):
            file_path = os.path.join(path, file)
            break
        
    # Load the CSV file into a pandas DataFrame
    df = pd.read_csv(file_path)

    # Display the first few rows of the DataFrame
    print(df.head())

    # List the columns from the DataFrame
    print(df.columns)
    
    return df

def plot_stim_times(df):
    import matplotlib.pyplot as plt

    # Create a scatter plot for 'thisRow.t'
    plt.figure(figsize=(10, 6))
    plt.scatter(df['thisRow.t'], [0] * len(df['thisRow.t']), label='thisRow.t', color='blue')

    # Add vertical lines for 'stim_grayScreen.started'
    for start_time in df['stim_grayScreen.started']:
        plt.axvline(x=start_time, color='red', linestyle='--', label='stim_grayScreen.started')

    # Add vertical lines for 'stim_grating.started'
    for start_time in df['stim_grating.started']:
        plt.axvline(x=start_time, color='green', linestyle='--', label='stim_grating.started')

    plt.title('Visual stim presentation timepoints')
    plt.xlabel('Time')
    plt.legend()
    plt.grid(True)
    plt.show()

def plot_stim_times2(df):
    import plotly.express as px
    import plotly.graph_objects as go
    
    # Create an interactive scatter plot for 'thisRow.t'
    fig = px.scatter(df, x='thisRow.t', title='Scatter Plot of thisRow.t')
    fig.update_layout(xaxis_title='thisRow.t', yaxis_title='na')
    #fig.show()

    # Create an interactive plot with vertical lines for 'stim_grayScreen.started' and 'stim_grating.started'
    fig = go.Figure()

    # Add scatter plot for 'thisRow.t'
    fig.add_trace(go.Scatter(x=df['thisRow.t'], mode='markers', name='thisRow.t'))

    # Add vertical lines for 'stim_grayScreen.started'
    for start_time in df['stim_grayScreen.started']:
        fig.add_vline(x=start_time, line=dict(color='red', dash='dash'), name='stim_grayScreen.started')

    # Add vertical lines for 'stim_grating.started'
    for start_time in df['stim_grating.started']:
        fig.add_vline(x=start_time, line=dict(color='green', dash='dash'), name='stim_grating.started')

    fig.update_layout(title='Visual stim presentation timepoints',
                    xaxis_title='Time')
    fig.show()
    
