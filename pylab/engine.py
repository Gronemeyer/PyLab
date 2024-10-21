from magicgui.widgets import ComboBox
import datetime
import pandas as pd
from magicgui import magicgui
import os
import keyboard
import napari.layers
import napari.layers.image
import pymmcore_plus
import useq
from useq import MDASequence
from magicgui.widgets import Container, CheckBox, create_widget
import pathlib
import numpy as np

from pylab.utils import utils
from pylab.config import ExperimentConfig

import subprocess #for PsychoPy Subprocess


class AcquisitionEngine(Container):
    """ AcquisitionEngine object for the napari-mesofield plugin
    This class is a subclass of the Container class from the magicgui.widgets module.
    The object connects to the Micro-Manager Core object instance and the napari viewer object.
 
    _update_config: updates the experiment configuration from a new json file
    
    run_sequence: runs the MDA sequence with the configuration parameters
    
    launch_psychopy: launches the PsychoPy experiment as a subprocess with ExperimentConfig parameters
    """
    def __init__(self, viewer: "napari.viewer.Viewer", mmc: pymmcore_plus.CMMCorePlus, mmc2: pymmcore_plus.CMMCorePlus = None):
        super().__init__()
        self._viewer = viewer
        self._mmc = mmc
        self._mmc2 = mmc2
        self.config = ExperimentConfig()
        self.dhyana_metadata = []
        self.thor_metadata = []
        
        #====================================GUI Widgets=====================================#
        
        # 1. Selecting a save directory with a FileEdit widget
        self._gui_directory_fileedit = create_widget(
            label='Select Save Directory:',
            widget_type='FileEdit',
            annotation='pathlib.Path',
            options={'mode': 'd'}
        )
        # 2. Dropdown Widget for JSON configuration files
        self._gui_json_dropdown = ComboBox(
            label='Select JSON Config:'
        )
        # 3. Table widget to display the configuration parameters loaded from the JSON
        self._gui_config_table = create_widget(
            label='Experiment Config:',
            widget_type='Table',
            is_result=True,
            value=self.config.dataframe
        )
        self._gui_config_table.read_only = False  # Allow user input to edit the table
        self._gui_config_table.changed.connect(self._on_table_edit)  # Connect to table update function

        # 4. Record button to start the MDA sequence
        self._gui_record_button = create_widget(
            label='Record', widget_type='PushButton'
        )
        # 5. Launch PsychoPy button to start the PsychoPy experiment
        self._gui_psychopy_button = create_widget(
            label='Launch PsychoPy', widget_type='PushButton'
        )
        #-------------------------------------------------------------------------------------#
        
        #============Callback connections between widget values and functions===================#
        
        self._gui_directory_fileedit.changed.connect(lambda path: self._get_json_file_choices(path))
        # Load the JSON configuration file from the dropdown value 
        self._gui_json_dropdown.changed.connect(self._update_config)
        # Run the MDA sequence upon button press
        self._gui_record_button.changed.connect(self.rec)
        # Launch the PsychoPy experiment upon button press
        self._gui_psychopy_button.changed.connect(self.launch_psychopy)
        
        self._mmc.mda.events.frameReady.connect(self._dhyana_on_frame_ready)
        self._mmc2.mda.events.frameReady.connect(self._thor_on_frame_ready) #241004 Added second connection, untested; can a method be called internally by two threaded operations? 241013 - works fine
        self._mmc.mda.events.sequenceFinished.connect(self._save_mmc_metadata)
        self._mmc2.mda.events.sequenceFinished.connect(self._save_mmc_metadata)

        #-------------------------------------------------------------------------------------#
        
        # Add the widgets to the container
        self.extend([
            self._gui_directory_fileedit,
            self._gui_json_dropdown,
            self._gui_config_table,
            self._gui_record_button,
            self._gui_psychopy_button
        ])

    #==============================Private Class Methods=============================================#
    
    def _get_json_file_choices(self, path):
        """Return a list of JSON files in the current directory."""
        import glob
        self.config.save_dir = path
        try:
            json_files = glob.glob(os.path.join(path, "*.json"))
            self._gui_json_dropdown.choices = json_files
        except Exception as e:
            print(f"Error getting JSON files from directory: {path}\n{e}")
    
    def _update_config(self):
        """Update the experiment configuration from a new JSON file."""
        json_path_input = self._gui_json_dropdown.value
        
        if json_path_input and os.path.isfile(json_path_input):
            try:
                self.config.load_parameters(json_path_input)
                # Refresh the GUI table
                self._refresh_config_table()
            except Exception as e:
                print(f"Trouble updating ExperimentConfig from AcquisitionEngine:\n{json_path_input}\nConfiguration not updated.")
                print(e)
                
    def _on_table_edit(self, event=None):
        """Update the configuration parameters when the table is edited."""
        # Retrieve the updated data from the table
        table_value = self._gui_config_table.value  # This should be a dict with 'data' and 'columns'

        # Convert the table data into a DataFrame
        df = pd.DataFrame(data=table_value['data'], columns=table_value['columns'])
        try:
            if not df.empty:
                # Update the parameters in the config
                for index, row in df.iterrows():
                    key = row['Parameter']
                    value = row['Value']
                    self.config.update_parameter(key, value)
        except Exception as e:
            print(f"Error updating config from table: check AcquisitionEngine._on_table_edit()\n{e}")

    def _refresh_config_table(self):
        """Refresh the configuration table to reflect current parameters."""
        self._gui_config_table.value = self.config.dataframe
        
    def _dhyana_on_frame_ready(self, data: np.ndarray, event: useq.MDAEvent, metadata: dict):
        """Callback function to save MicroManager core metadata when an image is captured during the MDA."""
        # Update the viewer with the new image
        self.dhyana_metadata.append(metadata)
    
    def _thor_on_frame_ready(self, data: np.ndarray, event: useq.MDAEvent, metadata: dict):
        """Callback function to save MicroManager core metadata when an image is captured during the MDA."""
        # Update the viewer with the new image
        self.thor_metadata.append(metadata)
        
    def _save_mmc_metadata(self):
        """Save the metadata from the MDA to a CSV file in the same folder as the acquired .tiff files."""
        if self.dhyana_metadata:
            metadata_df = pd.DataFrame(self.dhyana_metadata)
            metadata_df.to_json(os.path.join(self.config.bids_dir, 'dhyana_metadata.json'))
        if self.thor_metadata:
            metadata_df = pd.DataFrame(self.thor_metadata)
            metadata_df.to_json(os.path.join(self.config.bids_dir, 'thor_metadata.json'))


    #-----------------------------------------------------------------------------------------------#

    #==============================Public Class Methods=============================================#
    
    def rec(self):
        """Run the MDA sequence with the configuration parameters.
        """
        dhyana_fps = 50 #20ms exposure
        thorcam_fps = 34 # 20ms exposure
        duration = self.config.num_frames / dhyana_fps # 50 fps
        pupil_frames = (thorcam_fps * duration) + 1000 # 34 fps
         
        # Wait for spacebar press if start_on_trigger is True
        wait_for_trigger = self.config.start_on_trigger
        if wait_for_trigger:
            print("Press spacebar to start recording...")
            #self.launch_psychopy()
            while not keyboard.is_pressed('space'):
                pass
            self.config.update_parameter('keyb_trigger_timestamp', datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
            
        # Run the MDA, if second instance of MMC is loaded on the engine (ie. ThorPupil Cam) then start that MDA, too
        self._mmc.run_mda(
            MDASequence(time_plan={"interval": 0, "loops": self.config.num_frames}),
            output=self.config.data_path
        )
        
        if self._mmc2 is not None:
            self._mmc2.run_mda(
                MDASequence(time_plan={"interval": 0, "loops": pupil_frames}),
                output=self.config.pupil_file_path
            )
    
        #return 241013 - devJG trying to figure out why the _mmc2 Thor acquistion hangs after the dhyana acquisition stops
        
    def launch_psychopy(self):
        """ 
        Launches a PsychoPy experiment as a subprocess with the current ExperimentConfig parameters 
        """
        dhyana_fps = 50 #20ms exposure
        duration = self.config.num_frames / dhyana_fps # 50 fps

        assert duration is not None, "Duration must be specified for PsychoPy experiment"
        self.config.num_trials = int(duration / 5) # 5 seconds per trial 
        # Build the command arguments
        args = [
            "C:\\Program Files\\PsychoPy\\python.exe",
            "F:\\jgronemeyer\\Gratings_vis_0.6.py",
            f'{self.config.protocol}',
            f'{self.config.subject}',
            f'{self.config.session}',
            f'{self.config.save_dir}',
            f'{self.config.num_trials}'
        ]
        
        subprocess.Popen(args, start_new_session=True)
        
    def pupil_view(self):
        from matplotlib import pyplot as plt
        plt.imshow(self._mmc2.snap(), interpolation='nearest')
        plt.show()
        return
    
    def save_config(self):
        """ Save the current configuration to a JSON file """
        self.config.to_json(os.path.join(self.config.bids_dir, 'configuration.json'))

    #-----------------------------------------------------------------------------------------------#