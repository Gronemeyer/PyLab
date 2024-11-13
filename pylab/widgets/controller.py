import os
import subprocess #for PsychoPy Subprocess
import datetime

from qtpy.QtCore import Qt
from PyQt6.QtCore import pyqtSignal, QProcess
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
    QLineEdit,
    QPushButton,
    QComboBox,
    QTableWidget,
    QHeaderView,
    QFileDialog,
    QTableWidgetItem,
    QMessageBox,
    QInputDialog
)

from pymmcore_plus import CMMCorePlus

from pylab.config import ExperimentConfig

class ConfigController(QWidget):
    """AcquisitionEngine object for the napari-mesofield plugin.
    The object connects to the Micro-Manager Core object instances and the Config object.

    The ConfigController widget is a QWidget that allows the user to select a save directory,
    load a JSON configuration file, and edit the configuration parameters in a table.
    The user can also trigger the MDA sequence with the current configuration parameters.
    
    The ConfigController widget emits signals to notify other widgets when the configuration is updated
    and when the record button is pressed.
    
    Public Methods:
    save_config(): saves the current configuration to a JSON file
    
    record(): triggers the MDA sequence with the configuration parameters
    
    launch_psychopy(): launches the PsychoPy experiment as a subprocess with ExperimentConfig parameters
    
    show_popup(): shows a popup message to the user
    
    Private Methods:
    _select_directory(): opens a dialog to select a directory and update the GUI accordingly
    
    _get_json_file_choices(): returns a list of JSON files in the current directory

    _update_config(): updates the experiment configuration from a new JSON file

    _on_table_edit(): updates the configuration parameters when the table is edited
    
    _refresh_config_table(): refreshes the configuration table to reflect current parameters
    
    _test_led(): tests the LED pattern by sending a test sequence to the Arduino-Switch device
    
    _stop_led(): stops the LED pattern by sending a stop sequence to the Arduino-Switch device
    
    _add_note(): opens a dialog to get a note from the user and save it to the ExperimentConfig.notes list
    
    """
    # ==================================== Signals ===================================== #
    configUpdated = pyqtSignal(object)
    recordStarted = pyqtSignal()
    # ------------------------------------------------------------------------------------- #
    
    def __init__(self, mmc1: CMMCorePlus, mmc2: CMMCorePlus, cfg):
        super().__init__()
        self._mmc1 = mmc1
        self._mmc2 = mmc2
        self.config: ExperimentConfig = cfg
        self.psychopy_process = None

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
        
        # 5. Test LED button to test the LED pattern
        self.test_led_button = QPushButton("Test LED")
        self.layout.addWidget(self.test_led_button)
        
        # 6. Stop LED button to stop the LED pattern
        self.stop_led_button = QPushButton("Stop LED")
        self.layout.addWidget(self.stop_led_button)
        
        # 7. Add Note button to add a note to the configuration
        self.add_note_button = QPushButton("Add Note")
        self.layout.addWidget(self.add_note_button)


        # ------------------------------------------------------------------------------------- #

        # ============ Callback connections between widget values and functions ================ #

        self.directory_button.clicked.connect(self._select_directory)
        self.json_dropdown.currentIndexChanged.connect(self._update_config)
        self.config_table.cellChanged.connect(self._on_table_edit)
        self.record_button.clicked.connect(self.record)
        self.test_led_button.clicked.connect(self._test_led)
        self.stop_led_button.clicked.connect(self._stop_led)
        self.add_note_button.clicked.connect(self._add_note)

        # ------------------------------------------------------------------------------------- #

        # Initialize the config table
        self._refresh_config_table()

    # ============================== Public Class Methods ============================================ #

    def record(self):
        """Run the MDA sequence with the global Config object parameters loaded from JSON."""
        import keyboard

        # Wait for spacebar press if start_on_trigger is True
        wait_for_trigger = self.config.start_on_trigger
        if wait_for_trigger == True:
            self.launch_psychopy()
            self.show_popup()
        # Emit signal to notify other widgets
        self.recordStarted.emit() # Signals to start the MDA sequence


    def launch_psychopy(self):
        """Launches a PsychoPy experiment as a subprocess with the current ExperimentConfig parameters."""
        # Build the command arguments
        args = [
            "C:\\Program Files\\PsychoPy\\python.exe",
            f'{self.config.psychopy_path}',
            f'{self.config.protocol}',
            f'{self.config.subject}',
            f'{self.config.session}',
            f'{self.config.save_dir}',
            f'{self.config.num_trials}'
        ]

        # Create and start the QProcess
        self.psychopy_process = QProcess(self)
        self.psychopy_process.finished.connect(self._handle_process_finished)
        self.psychopy_process.start(args[0], args[1:])
        self.show_popup()


    def _handle_process_finished(self, exit_code, exit_status):
        from PyQt6.QtCore import QProcess

        """Handle the finished state of the PsychoPy subprocess."""
        if self.psychopy_process.state() != QProcess.NotRunning:
            self.psychopy_process.kill()
            self.psychopy_process = None
        self.psychopy_process.deleteLater()
        print(f"PsychoPy process finished with exit code {exit_code} and exit status {exit_status}")
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            self.event_loop.quit()
    
    def show_popup(self):
        msg_box = QMessageBox()
        msg_box.setText("Press spacebar to start recording.")
        #msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()
    
    def save_config(self):
        """ Save the current configuration to a JSON file """
        self.config.save_parameters()
        
    #TODO: add breakdown method

    #-----------------------------------------------------------------------------------------------#
    
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
                # FIXME: This implicitly assumes mmc1 is the Dhyana core with the arduino-switch device
                self._refresh_config_table()
            except Exception as e:
                print(f"Trouble updating ExperimentConfig from AcquisitionEngine:\n{json_path_input}\nConfiguration not updated.")
                print(e)
            # try:
            #     # Load the LED pattern to the Arduino-Switch device
            #     self._mmc1.getPropertyObject('Arduino-Switch', 'State').loadSequence(self.config.led_pattern)
            # except Exception as e:
            #     print(f'{self.__str__}: LED Pattern not uploaded to Arduino: {e}')    

    def _on_table_edit(self, row, column):
        """Update the configuration parameters when the table is edited."""
        try:
            if self.config_table.item(row, 0) and self.config_table.item(row, 1):
                key = self.config_table.item(row, 0).text()
                value = self.config_table.item(row, 1).text()
                self.config.update_parameter(key, value)
            self.configUpdated.emit(self.config) # EMIT SIGNAL TO LISTENERS                
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

        self.configUpdated.emit(self.config) # EMIT SIGNAL TO LISTENERS
        
    def _test_led(self):
        """
        Test the LED pattern by sending a test sequence to the Arduino-Switch device.
        """
        try:
            led_pattern = self.config.led_pattern
            self._mmc1.getPropertyObject('Arduino-Switch', 'State').loadSequence(led_pattern)
            self._mmc1.getPropertyObject('Arduino-Switch', 'State').setValue(4) # seems essential to initiate serial communication
            self._mmc1.getPropertyObject('Arduino-Switch', 'State').startSequence()
            print("LED test pattern sent successfully.")
        except Exception as e:
            print(f"Error testing LED pattern: {e}")
            
    def _stop_led(self):
        """
        Stop the LED pattern by sending a stop sequence to the Arduino-Switch device.
        """
        try:
            self._mmc1.getPropertyObject('Arduino-Switch', 'State').stopSequence()
            print("LED test pattern stopped successfully.")
        except Exception as e:
            print(f"Error stopping LED pattern: {e}")
            
    def _add_note(self):
        """
        Open a dialog to get a note from the user and save it to the ExperimentConfig.notes list.
        """
        text, ok = QInputDialog.getText(self, 'Add Note', 'Enter your note:')
        if ok and text:
            time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            note_with_timestamp = f"{time}: {text}"
            self.config.notes.append(note_with_timestamp)
            print("Note added to configuration.")

    # ----------------------------------------------------------------------------------------------- #



