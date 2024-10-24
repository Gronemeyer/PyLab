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



from PyQt5.QtWidgets import (
    QWidget, QFileDialog, QComboBox, QTableWidget, QPushButton, QVBoxLayout,
    QHBoxLayout, QLabel, QLineEdit, QTableWidgetItem, QHeaderView
)
from PyQt5.QtCore import pyqtSignal, Qt
import pymmcore_plus
import os
import pandas as pd
import subprocess
import datetime

# Assuming ExperimentConfig is defined elsewhere
# from your_module import ExperimentConfig

class AcquisitionEngine(QWidget):
    """AcquisitionEngine object for the napari-mesofield plugin.
    This class is a subclass of the QWidget class.
    The object connects to the Micro-Manager Core object instance and the napari viewer object.

    _update_config: updates the experiment configuration from a new JSON file

    run_sequence: runs the MDA sequence with the configuration parameters

    launch_psychopy: launches the PsychoPy experiment as a subprocess with ExperimentConfig parameters
    """
    def __init__(self, mmc: pymmcore_plus.CMMCorePlus, cfg):
        super().__init__()
        self._mmc = mmc
        self.config: ExperimentConfig = cfg

        # Create main layout
        self.layout = QVBoxLayout(self)

        # ==================================== GUI Widgets ===================================== #

        # 1. Selecting a save directory
        self.directory_label = QLabel('Select Save Directory:')
        self.directory_line_edit = QLineEdit()
        self.directory_line_edit.setReadOnly(True)
        self.directory_button = QPushButton('Browse')

        dir_layout = QHBoxLayout()
        dir_layout.addWidget(self.directory_label)
        dir_layout.addWidget(self.directory_line_edit)
        dir_layout.addWidget(self.directory_button)

        self.layout.addLayout(dir_layout)

        # 2. Dropdown Widget for JSON configuration files
        self.json_dropdown_label = QLabel('Select JSON Config:')
        self.json_dropdown = QComboBox()

        json_layout = QHBoxLayout()
        json_layout.addWidget(self.json_dropdown_label)
        json_layout.addWidget(self.json_dropdown)

        self.layout.addLayout(json_layout)

        # 3. Table widget to display the configuration parameters loaded from the JSON
        self.layout.addWidget(QLabel('Experiment Config:'))
        self.config_table = QTableWidget()
        self.config_table.setEditTriggers(QTableWidget.AllEditTriggers)
        self.config_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.layout.addWidget(self.config_table)

        # 4. Record button to start the MDA sequence
        self.record_button = QPushButton('Record')
        self.layout.addWidget(self.record_button)

        # ------------------------------------------------------------------------------------- #

        # ============ Callback connections between widget values and functions ================ #

        self.directory_button.clicked.connect(self._select_directory)
        self.json_dropdown.currentIndexChanged.connect(self._update_config)
        self.config_table.cellChanged.connect(self._on_table_edit)
        self.record_button.clicked.connect(self.record)

        # ------------------------------------------------------------------------------------- #

        # Initialize the config table
        self._refresh_config_table()

    # ============================== Private Class Methods ============================================ #

    def _select_directory(self):
        """Open a dialog to select a directory and update the GUI accordingly."""
        directory = QFileDialog.getExistingDirectory(self, "Select Save Directory")
        if directory:
            self.directory_line_edit.setText(directory)
            self._get_json_file_choices(directory)

    def _get_json_file_choices(self, path):
        """Return a list of JSON files in the current directory."""
        import glob
        self.config.save_dir = path
        try:
            json_files = glob.glob(os.path.join(path, "*.json"))
            self.json_dropdown.clear()
            self.json_dropdown.addItems(json_files)
        except Exception as e:
            print(f"Error getting JSON files from directory: {path}\n{e}")

    def _update_config(self, index):
        """Update the experiment configuration from a new JSON file."""
        json_path_input = self.json_dropdown.currentText()

        if json_path_input and os.path.isfile(json_path_input):
            try:
                self.config.load_parameters(json_path_input)
                # Refresh the GUI table
                self._refresh_config_table()
            except Exception as e:
                print(f"Trouble updating ExperimentConfig from AcquisitionEngine:\n{json_path_input}\nConfiguration not updated.")
                print(e)

    def _on_table_edit(self, row, column):
        """Update the configuration parameters when the table is edited."""
        try:
            if self.config_table.item(row, 0) and self.config_table.item(row, 1):
                key = self.config_table.item(row, 0).text()
                value = self.config_table.item(row, 1).text()
                self.config.update_parameter(key, value)
        except Exception as e:
            print(f"Error updating config from table: check AcquisitionEngine._on_table_edit()\n{e}")

    def _refresh_config_table(self):
        """Refresh the configuration table to reflect current parameters."""
        df = self.config.dataframe
        self.config_table.blockSignals(True)  # Prevent signals while updating the table
        self.config_table.clear()
        self.config_table.setRowCount(len(df))
        self.config_table.setColumnCount(len(df.columns))
        self.config_table.setHorizontalHeaderLabels(df.columns.tolist())

        for i, row in df.iterrows():
            for j, (col_name, value) in enumerate(row.items()):
                item = QTableWidgetItem(str(value))
                self.config_table.setItem(i, j, item)

        self.config_table.blockSignals(False)  # Re-enable signals

    # ----------------------------------------------------------------------------------------------- #

    # ============================== Public Class Methods ============================================ #

    def record(self):
        """Run the MDA sequence with the global Config object parameters loaded from JSON."""

        # Wait for spacebar press if start_on_trigger is True
        wait_for_trigger = self.config.start_on_trigger
        if wait_for_trigger:
            print("Press spacebar to start recording...")
            # self.launch_psychopy()
            # Note: Implement key press detection suitable for PyQt5
            # For example, using QEventLoop or custom dialog

        # Run the MDA sequence
        self._mmc.run_mda(
            self.config.meso_sequence,
            output=self.config.meso_data_path
        )

    def launch_psychopy(self):
        """Launches a PsychoPy experiment as a subprocess with the current ExperimentConfig parameters."""
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
    
    def save_config(self):
        """ Save the current configuration to a JSON file """
        self.config.save_parameters()

    #-----------------------------------------------------------------------------------------------#