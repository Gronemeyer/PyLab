import os
import json
import pathlib
import pandas as pd
import os


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

    @property
    def save_dir(self) -> pathlib.Path:
        return self._save_dir

    @save_dir.setter
    def save_dir(self, path: str):
        if isinstance(path, pathlib.Path):
            self._save_dir = os.path.join(path, 'data')
        else:
            print(f"ExperimentConfig: \n Invalid save directory path: {path}")

    @property
    def protocol(self) -> str:
        return self._parameters.get('protocol', 'default_protocol')

    @property
    def subject(self) -> str:
        return self._parameters.get('subject', 'default_subject')

    @property
    def session(self) -> str:
        return self._parameters.get('session', 'default_session')

    @property
    def task(self) -> str:
        return self._parameters.get('task', 'default_task')

    @property
    def start_on_trigger(self) -> bool:
        return self._parameters.get('start_on_trigger', False)

    @property
    def num_frames(self) -> int:
        return self._parameters.get('num_frames', 0)
    
    @property
    def num_trials(self) -> int:
        return self._parameters.get('num_trials', 0)
    
    @num_trials.setter
    def num_trials(self, value):
        self._parameters['num_trials'] = value
    
    @property
    def parameters(self) -> dict:
        return self._parameters
    
    @property
    def filename(self):
        return f"{self.protocol}-sub-{self.subject}_ses-{self.session}_task-{self.task}.ome.tiff"

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
    def data_path(self):
        file = self.filename
        return self._generate_unique_file_path(file)

    # Property for pupil file path, if needed
    @property
    def pupil_file_path(self):
        file = f"{self.protocol}-sub-{self.subject}_ses-{self.session}_task-{self.task}_pupil.tiff"
        return self._generate_unique_file_path(file)

    @property
    def dataframe(self):
        data = {'Parameter': list(self._parameters.keys()),
                'Value': list(self._parameters.values())}
        return pd.DataFrame(data)
    
    @property
    def json_path(self):
        return self._json_file_path
    
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
        filename = self._parameters.get('subject') + '_' + self._parameters.get('task') + '.json'
        save_path = os.path.join(self.save_dir, filename)
        try:
            with open(save_path, 'w') as f:
                json.dump(self._parameters, f, indent=4)
            print(f"Parameters saved to {save_path}")
        except Exception as e:
            print(f"Error saving parameters: {e}")
