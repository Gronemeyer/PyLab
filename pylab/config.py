import os
import json
import pathlib
import pandas as pd
import os
import useq
import warnings
from pymmcore_plus import CMMCorePlus

from typing import TYPE_CHECKING

from pylab.io import SerialWorker
    
from pylab.startup import Startup

class ExperimentConfig:
    """## Generate and store parameters loaded from a JSON file. 
    
    #### Example Usage:
    ```python
    config = ExperimentConfig()
    # create dict and pandas DataFrame from JSON file path:
    config.load_parameters('path/to/json_file.json')
        
    config._save_dir = './output'
    config.subject = '001'
    config.task = 'TestTask'
    config.notes.append('This is a test note.')

    # Update a parameter
    config.update_parameter('new_param', 'test_value')

    # Save parameters and notes
    config.save_parameters()
    ```
    """

    def __init__(self, path: str = None, development_mode: bool = False):
        self._parameters = {}
        self._json_file_path = ''
        self._output_path = ''
        self._save_dir = ''

        if development_mode: 
            self.hardware = Startup() 
        else:
            self.hardware = Startup._from_json(os.path.join(os.path.dirname(__file__), path))

        # Extract FPS values from Startup instance, if available

        self.dhyana_fps: int = self.hardware._dhyana_fps
        self.thorcam_fps: int = self.hardware._thorcam_fps 
        
        self.notes: list = []

    @property
    def _cores(self) -> tuple[CMMCorePlus, CMMCorePlus]:
        """Return the two CMMCorePlus instances from the Startup cores."""
        return self.hardware.widefield.core, self.hardware.thorcam.core

    @property
    def encoder(self) -> SerialWorker:
        return self.hardware.encoder.worker

    @property
    def save_dir(self) -> str:
        return os.path.join(self._save_dir, 'data')

    @save_dir.setter
    def save_dir(self, path: str):
        if isinstance(path, str):
            self._save_dir = os.path.abspath(path)
        else:
            print(f"ExperimentConfig: \n Invalid save directory path: {path}")

    @property
    def protocol(self) -> str:
        return self._parameters.get('protocol', 'protocol')
    
    @property
    def wheel_encoder(self) -> dict:
        return self._parameters.get('wheel_encoder', {'port': 'COM4', 'baudrate': 57600})

    @property
    def subject(self) -> str:
        return self._parameters.get('subject', 'sub')

    @property
    def session(self) -> str:
        return self._parameters.get('session', 'ses')

    @property
    def task(self) -> str:
        return self._parameters.get('task', 'task')

    @property
    def start_on_trigger(self) -> bool:
        return self._parameters.get('start_on_trigger', False)
    
    @property
    def sequence_duration(self) -> int:
        return int(self._parameters.get('duration', 60))
    
    @property
    def trial_duration(self) -> int:
        return int(self._parameters.get('trial_duration', None))
    
    @property
    def num_meso_frames(self) -> int:
        return int(self.dhyana_fps * self.sequence_duration) 
    
    @property
    def num_pupil_frames(self) -> int:
        return int((self.thorcam_fps * self.sequence_duration)) + 100 
    
    @property
    def num_trials(self) -> int:
        return int(self.sequence_duration / self.trial_duration)  
    
    @property
    def parameters(self) -> dict:
        return self._parameters
    
    @property
    def meso_sequence(self) -> useq.MDASequence:
        return useq.MDASequence(time_plan={"interval": 0, "loops": self.num_meso_frames})
    
    @property
    def pupil_sequence(self) -> useq.MDASequence:
        return useq.MDASequence(time_plan={"interval": 0, "loops": self.num_pupil_frames})
    
    @property #currently unused
    def filename(self):
        return f"{self.protocol}-sub-{self.subject}_ses-{self.session}_task-{self.task}.tiff"

    @property
    def bids_dir(self) -> str:
        """ Dynamic construct of BIDS directory path """
        bids = os.path.join(
            f"{self.protocol}",
            f"sub-{self.subject}",
            f"ses-{self.session}",
        )
        return os.path.abspath(os.path.join(self.save_dir, bids))

    # Property to compute the full file path, handling existing files
    @property
    def meso_file_path(self):
        file = f"{self.protocol}-sub-{self.subject}_ses-{self.session}_task-{self.task}_meso.ome.tiff"
        return self._generate_unique_file_path(file, 'func')

    # Property for pupil file path, if needed
    @property
    def pupil_file_path(self):
        file = f"{self.protocol}-sub-{self.subject}_ses-{self.session}_task-{self.task}_pupil.ome.tiff"
        return self._generate_unique_file_path(file, 'func')

    @property
    def dataframe(self):
        data = {'Parameter': list(self._parameters.keys()),
                'Value': list(self._parameters.values())}
        return pd.DataFrame(data)
    
    @property
    def json_path(self):
        return self._json_file_path
    
    @property
    def psychopy_filename(self) -> str:
        py_files = list(pathlib.Path(self._save_dir).glob('*.py'))
        if py_files:
            return py_files[0].name
        else:
            warnings.warn(f'No Psychopy experiment file found in directory {pathlib.Path(self.save_dir).parent}.')
        return self._parameters.get('psychopy_filename', 'experiment.py')
    
    @psychopy_filename.setter
    def psychopy_filename(self, value: str) -> None:
        self._parameters['psychopy_filename'] = value

    @property
    def psychopy_path(self) -> str:
        return os.path.join(self._save_dir, self.psychopy_filename)
    
    @property
    def led_pattern(self) -> list[str]:
        return self._parameters.get('led_pattern', ['4', '4', '2', '2'])
    
    @led_pattern.setter
    def led_pattern(self, value: list) -> None:
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                raise ValueError("led_pattern string must be a valid JSON list")
        if isinstance(value, list):
            self._parameters['led_pattern'] = [str(item) for item in value]
        else:
            raise ValueError("led_pattern must be a list or a JSON string representing a list")
    
    # Helper method to generate a unique file path
    def _generate_unique_file_path(self, file, bids_type: str = 'func'):
        """
        Generates a unique file path in the specified bids_type directory by appending a counter to the file name if a file with the same name already exists.
        Args:
            file (str): The name of the file for which a unique path is to be generated.
            bids_type (str): The subdirectory within the BIDS directory.
        Returns:
            str: A unique file path within the specified bids_type directory.
        Example:
            If `self.bids_dir` is "/path/to/dir", `bids_type` is "func", and `file` is "example.txt":
            - If "/path/to/dir/func/example.txt" does not exist, the function returns "/path/to/dir/func/example.txt".
            - If "/path/to/dir/func/example.txt" exists, the function returns "/path/to/dir/func/example_1.txt".
            - If both "/path/to/dir/func/example.txt" and "/path/to/dir/func/example_1.txt" exist, the function returns "/path/to/dir/func/example_2.txt".
        """
        
        bids_path = os.path.join(self.bids_dir, bids_type)
        os.makedirs(bids_path, exist_ok=True)
        base, ext = os.path.splitext(file)
        counter = 1
        file_path = os.path.join(bids_path, file)
        while os.path.exists(file_path):
            file_path = os.path.join(bids_path, f"{base}_{counter}{ext}")
            counter += 1
        return file_path
    
    def load_parameters(self, json_file_path) -> None:
        """ 
        Load parameters from a JSON file path into the config object. 
        """
        
        try:
            with open(json_file_path, 'r') as f: 
                self._parameters = json.load(f)
        except FileNotFoundError:
            print(f"File not found: {json_file_path}")
            return
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            return

    def update_parameter(self, key, value) -> None:
        """ Update a parameter in the config object """
        self._parameters[key] = value
        
    def list_parameters(self) -> pd.DataFrame:
        """ Create a DataFrame from the ExperimentConfig properties """
        properties = [prop for prop in dir(self.__class__) if isinstance(getattr(self.__class__, prop), property)]
        exclude_properties = {'dataframe', 'parameters'}
        data = {prop: getattr(self, prop) for prop in properties if prop not in exclude_properties}
        return pd.DataFrame(data.items(), columns=['Parameter', 'Value'])
        
    def save_parameters(self, filename='parameters.json') -> None:
        """
        Save the current parameters to a JSON file in the save directory.
        """
        filename = f'{self.subject}_{self.task}_ExperimentConfig.json'
        save_path = os.path.join(self.bids_dir, filename)

        properties = [prop for prop in dir(self.__class__) if isinstance(getattr(self.__class__, prop), property)]
        exclude_properties = {'dataframe', 'pupil_sequence', 'meso_sequence', 'parameters', 'filename', 'json_path', 'save_dir',}
        parameters = {prop: getattr(self, prop) for prop in properties if prop not in exclude_properties}
        
        # dump it all to json
        try:
            with open(save_path, 'w') as file:
                json.dump(parameters, file, indent=4)
            print(f"Parameters saved to {save_path}")
        except Exception as e:
            print(f"Error saving parameters: {e}")
            
        # save any notes to a text file    
        if self.notes:
            notes_filename = f'{self.subject}_{self.task}_notes.txt'
            notes_path = os.path.join(self.bids_dir, notes_filename)
            try:
                with open(notes_path, 'w') as notes_file:
                    notes_file.write('\n'.join(self.notes))
                print(f"Notes saved to {notes_path}")
            except Exception as e:
                print(f"Error saving notes: {e}")
                
    def save_wheel_encoder_data(self, data):
        """ Save the wheel encoder data to a CSV file """
        
        if isinstance(data, list):
            data = pd.DataFrame(data)
            
        filename = f'{self.subject}_session-{self.session}_encoder-data.csv'
        params_file = f'session_{self.session}_configuration.csv'

        unique_filename = self._generate_unique_file_path(filename, 'beh')
        params_path = self._generate_unique_file_path(params_file, 'beh')
        self.save_parameters()
        # Step up one hierarchy and then step back into the /beh folder
        # beh_dir = os.path.abspath(os.path.join(self.bids_dir, '..', 'beh'))
        # os.makedirs(beh_dir, exist_ok=True)
        # unique_filename = os.path.join(beh_dir, os.path.basename(unique_filename))
        try:
            params = self.list_parameters()
            params.to_csv(params_path, index=False)
            data.to_csv(unique_filename, index=False)
            print(f"Encoder data saved to {unique_filename}")
        except Exception as e:
            print(f"Error saving encoder data: {e}")
        
            

