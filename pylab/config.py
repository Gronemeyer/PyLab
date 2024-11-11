import os
import json
import pathlib
import pandas as pd
import os
import useq
import warnings


class ExperimentConfig:
    """## Generate and store parameters loaded from a JSON file. 
    
    #### Example Usage:
        ```
        config = ExperimentConfig()
            # create dict and pandas DataFrame from JSON file path:
        config.load_parameters('path/to/json_file.json')
            # update the 'subject' parameter to '001':
        config.update_parameter('subject', '001') 
            # return the value of the 'subject' parameter:
        config.parameters.get('subject') 
            # return a pandas DataFrame with 'Parameter' and 'Value' columns:
        ```
    """

    def __init__(self):
        self._parameters = {}
        self._json_file_path = ''
        self._output_path = ''
        self._save_dir = ''
        
        self.dhyana_fps: int = 50
        self.thorcam_fps: int = 34
        self.trial_duration: int = 5
        self.notes: list = []

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
    def num_meso_frames(self) -> int:
        return self._parameters.get('num_frames', 0)
    
    @property
    def sequence_duration(self) -> int:
        return int(self._parameters.get('num_frames', 100)) / self.dhyana_fps # 50 fps
    #TODO: type checking here, cast to ints
    
    @property
    def num_pupil_frames(self) -> int:
        return int((self.thorcam_fps * self.sequence_duration)) + 100 # 34 fps
    #TODO: type checking here, cast to ints
    
    @property
    def num_trials(self) -> int:
        return int(self.sequence_duration / self.trial_duration) # 5 seconds per trial 
    
    @num_trials.setter
    def num_trials(self, value):
        self._parameters['num_trials'] = value
    
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
    def bids_dir(self):
        """ Dynamic construct of BIDS directory path """
        bids = os.path.join(
            f"{self.protocol}",
            f"sub-{self.subject}",
            f"ses-{self.session}",
            'func'
        )
        return os.path.abspath(os.path.join(self.save_dir, bids))

    # Property to compute the full file path, handling existing files
    @property
    def meso_file_path(self):
        file = f"{self.protocol}-sub-{self.subject}_ses-{self.session}_task-{self.task}_meso.ome.tiff"
        return self._generate_unique_file_path(file)

    # Property for pupil file path, if needed
    @property
    def pupil_file_path(self):
        file = f"{self.protocol}-sub-{self.subject}_ses-{self.session}_task-{self.task}_pupil.ome.tiff"
        return self._generate_unique_file_path(file)

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
        if isinstance(value, list):
            self._parameters['led_pattern'] = [str(item) for item in value]
        else:
            raise ValueError("led_pattern must be a list")
    
    # Helper method to generate a unique file path
    def _generate_unique_file_path(self, file):
        os.makedirs(self.bids_dir, exist_ok=True)
        base, ext = os.path.splitext(file)
        counter = 1
        file_path = os.path.join(self.bids_dir, file)
        while os.path.exists(file_path):
            file_path = os.path.join(self.bids_dir, f"{base}_{counter}{ext}")
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
            


Config = ExperimentConfig()