from pymmcore_plus import CMMCorePlus

# Necessary modules for the IPython console
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.inprocess import QtInProcessKernelManager

from qtpy.QtWidgets import (
    QMainWindow, 
    QWidget, 
    QHBoxLayout, 
    QVBoxLayout,
)

from pylab.widgets import MDA, ConfigController
from pylab.config import ExperimentConfig
from pylab.engines import MesoEngine, PupilEngine

class MainWindow(QMainWindow):
    def __init__(self, core_object1: CMMCorePlus, core_object2: CMMCorePlus, cfg: ExperimentConfig):
        super().__init__()
        self.setWindowTitle("Main Widget with Two MDA Widgets")
        self.config: ExperimentConfig = cfg
        self._meso_engine: MesoEngine = MesoEngine(cfg, core_object1, True)
        self._pupil_engine: PupilEngine = PupilEngine(core_object2, True)
        
        # register engines to cores
        core_object1.register_mda_engine(self._meso_engine)
        core_object2.register_mda_engine(self._pupil_engine)
        
        # Create a central widget and set it as the central widget of the QMainWindow
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Set layout for the central widget
        main_layout = QHBoxLayout(central_widget)
        mda_layout = QVBoxLayout()
        
        # Create two instances of MDA widget
        self.dhyana_gui = MDA(core_object1, cfg)
        self.thor_gui = MDA(core_object2, cfg)
        self.cfg_gui = ConfigController(core_object1, core_object2, cfg)
        
        # Add MDA widgets to the layout
        mda_layout.addWidget(self.dhyana_gui)
        mda_layout.addWidget(self.thor_gui)
        main_layout.addLayout(mda_layout)
        main_layout.addWidget(self.cfg_gui)
        
        self.init_console(core_object1=core_object1, core_object2=core_object2, cfg=cfg)
        toggle_console_action = self.menuBar().addAction("Toggle Console")
        toggle_console_action.triggered.connect(self.toggle_console)

        self.thor_gui.mmc.mda.events.sequenceFinished.connect(self._on_end)
        self.cfg_gui.configUpdated.connect(self._update_config)
        self.cfg_gui.recordStarted.connect(self.record)
        
    def record(self):
        self.dhyana_gui.mda.run_mda()
        self.thor_gui.mda.run_mda()   
        
    def toggle_console(self):
        """Show or hide the IPython console."""
        if self.console_widget and self.console_widget.isVisible():
            self.console_widget.hide()
        else:
            if not self.console_widget:
                self.init_console()
            else:
                self.console_widget.show()
    
    def plots(self):
        import pylab.processing.plot as data
        dh_md_df, th_md_df = data.load_metadata(self.cfg_gui.config.bids_dir)
        data.plot_wheel_data(data.load_wheel_data(self.cfg_gui.config.bids_dir), data.load_psychopy_data(self.cfg_gui.config.bids_dir))
        data.plot_stim_times(data.load_psychopy_data(self.cfg_gui.config.bids_dir))
        data.plot_camera_intervals(dh_md_df, th_md_df)
    
    def metrics(self):
        import pylab.processing.plot as data
        from pylab.processing.metrics import calculate_metrics
        wheel_df = data.load_wheel_data(self.cfg_gui.config.bids_dir)
        stim_df = data.load_psychopy_data(self.cfg_gui.config.bids_dir)
        metrics_df = calculate_metrics(wheel_df, stim_df)
        print(metrics_df)   
                
    def init_console(self, core_object1: CMMCorePlus, core_object2: CMMCorePlus, cfg: ExperimentConfig):
        """Initialize the IPython console and embed it into the application."""
        # Create an in-process kernel
        self.kernel_manager = QtInProcessKernelManager()
        self.kernel_manager.start_kernel()
        self.kernel = self.kernel_manager.kernel
        self.kernel.gui = 'qt'

        # Create a kernel client and start channels
        self.kernel_client = self.kernel_manager.client()
        self.kernel_client.start_channels()

        # Create the console widget
        self.console_widget = RichJupyterWidget()
        self.console_widget.kernel_manager = self.kernel_manager
        self.console_widget.kernel_client = self.kernel_client

        # Expose variables to the console's namespace
        self.kernel.shell.push({
            'wdgt1': self.dhyana_gui,
            'wdgt2': self.thor_gui,
            'self': self,
            'config': cfg,
            'meso_core': core_object1,
            'pupil_core': core_object2,

            # Optional, so you can use 'self' directly in the console
        })

    def _on_end(self) -> None:
        """Called when the MDA is finished."""
        self.cfg_gui.save_config()
        self.plots()

    def _update_config(self, config):
        self.config: ExperimentConfig = config
        self._refresh_mda_gui()
        self._refresh_save_gui()
        self._update_engines()
        
    def _refresh_mda_gui(self):
        self.dhyana_gui.mda.setValue(self.config.meso_sequence)
        self.thor_gui.mda.setValue(self.config.pupil_sequence)
        
    def _refresh_save_gui(self):
        self.dhyana_gui.mda.save_info.setValue({'save_dir': str(self.config.bids_dir),  'save_name': str(self.config.meso_file_path), 'format': 'ome-tiff', 'should_save': True})
        self.thor_gui.mda.save_info.setValue({'save_dir': str(self.config.bids_dir), 'save_name': str(self.config.pupil_file_path), 'format': 'ome-tiff', 'should_save': True})
        
    def _update_engines(self):
        self._meso_engine.led_sequence = self.config.led_pattern
        
    def _on_pause(self, state: bool) -> None:
        """Called when the MDA is paused."""
