from pymmcore_plus import CMMCorePlus
import numpy as np
import useq
import tifffile
import os
from datetime import datetime
from napari import Viewer, run
from qtpy.QtWidgets import QPushButton, QWidget, QVBoxLayout, QLineEdit, QLabel, QFormLayout
from napari_plugin_engine import napari_hook_implementation
import nidaqmx

SAVE_DIR = r'C:/dev/sipefield/devOutput'
DEVTEST_DIR = r'C:/dev/micro-manager_acq/devtest'
SAVE_NAME = r'Acquisition_test'
MM_DIR = r'C:/Program Files/Micro-Manager-2.0'
MM_CONFIG = r'C:/dev/DyhanaCam.cfg'

mmc = CMMCorePlus.instance()
mmc.loadSystemConfiguration('C:/dev/DyhanaCam.cfg')

# Initialize a list to store frames
frames = []

### Default parameters for file saving
save_dir = SAVE_DIR
protocol_id = "dev"
subject_id = "001"
session_id = "01"

### Functions

# Function to save frames as a TIFF stack with timestamps
def save_tiff_stack(frames, save_dir, protocol, subject_id, session_id):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    anat_dir = os.path.join(save_dir, f"{protocol}-{subject_id}", f"ses-{session_id}", "anat")
    os.makedirs(anat_dir, exist_ok=True)
    filename = os.path.join(anat_dir, f"sub-{subject_id}_ses-{session_id}_T1w_{timestamp}.tiff")
    tifffile.imwrite(filename, np.array(frames))
    print(f"Saved TIFF stack: {filename}")

@mmc.mda.events.frameReady.connect #decorator to connect to the frameReady event of the MDA sequence
def on_frame(image: np.ndarray, event: useq.MDAEvent):
    # Append each received frame to the frames list
    frames.append(image)
    print(
        f"received frame: {image.shape}, {image.dtype} "
        f"@ index {event.index}, z={event.z_pos}"
    )

@mmc.mda.events.sequenceFinished.connect
def on_sequence_finished():
    '''We want to turn off the trigger signal and save the collected frames as a TIFF stack'''
    # Send the trigger signal off when acquisition is complete
    trigger_signal_off()
    # Save the collected frames as a TIFF stack
    save_tiff_stack(frames, save_dir, protocol_id, subject_id, session_id)

# Function to start the MDA sequence
def start_acquisition():
    # Send the trigger signal when acquisition starts
    send_trigger_signal()
    mmc.run_mda(mda_sequence)

# Function to send a high (TRUE) signal out of NIDAQ
def send_trigger_signal():
    with nidaqmx.Task() as task:
        task.do_channels.add_do_chan(
            'Dev2/port0/line0') #Hardware dependent value; check the NIDAQ device for the correct port and line
        task.do_channels.add_do_chan(
            'Dev2/port0/line1') #Hardware dependent value; check the NIDAQ device for the correct port and line
        
        task.write([True, True])
        print("Signal High from Dev2 on both lines")

# Function to send a low (FALSE) signal out of NIDAQ
def trigger_signal_off():
    with nidaqmx.Task() as task:
        task.do_channels.add_do_chan(
            'Dev2/port0/line0')
        task.do_channels.add_do_chan(
            'Dev2/port0/line1')
        
        task.write([False, False])
        print("Signal Low from Dev2 on both lines")

# Custom widget class for Napari
class MyWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.layout = QVBoxLayout(self)
        
        # Form layout for parameters
        self.form_layout = QFormLayout()
        # Form input collection
        self.save_dir_input = QLineEdit(save_dir)
        self.protocol_id_input = QLineEdit(protocol_id)
        self.subject_id_input = QLineEdit(subject_id)
        self.session_id_input = QLineEdit(session_id)
        # Form layout
        self.form_layout.addRow('Save Directory:', self.save_dir_input)
        self.form_layout.addRow('Protocol ID:', self.protocol_id_input)
        self.form_layout.addRow('Subject ID:', self.subject_id_input)
        self.form_layout.addRow('Session ID:', self.session_id_input)
        # Add Form layout to main layout
        self.layout.addLayout(self.form_layout)
        
        # Start Acquisition button
        self.button = QPushButton("Start Acquisition")
        self.button.clicked.connect(self.start_acquisition_with_params)
        self.layout.addWidget(self.button)
    
    def start_acquisition_with_params(self):
        global save_dir, protocol_id, subject_id, session_id
        save_dir = self.save_dir_input.text()
        subject_id = self.subject_id_input.text()
        session_id = self.session_id_input.text()
        start_acquisition()

# Function to start Napari with the custom widget
def start_napari():
    print("Starting Sipefield Napari Acquisition Interface...")
    viewer = Viewer()
    # Activate live view
    viewer.window.add_plugin_dock_widget('napari-micromanager')
    viewer.window.add_dock_widget(MyWidget(), area='right')
    run()

# Define your MDA sequence
mda_sequence = useq.MDASequence(
    time_plan={"interval": 0.5, "loops": 5}
)

# Launch Napari with the custom widget
if __name__ == "__main__":
    start_napari()
