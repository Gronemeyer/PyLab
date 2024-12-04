# encoder_widget.py

import time
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import QTimer
import pyqtgraph as pg

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pylab.io import SerialWorker
    from pylab.config import ExperimentConfig
    from pylab.startup import EncoderConfig

# # Constants
# ENCODER_CPR = 360       # Encoder counts per revolution
# WHEEL_DIAMETER = 0.1    # Wheel diameter in meters
# SERIAL_PORT = 'COM4'    # Replace with your serial port
# BAUD_RATE = 57600       # Match the Arduino's baud rate
# SAMPLE_INTERVAL = 20   # Update interval in milliseconds

class EncoderWidget(QWidget):
    def __init__(self, cfg):
        super().__init__()
        self._encoder: SerialWorker = cfg.hardware.encoder.worker
        self._config: EncoderConfig = cfg.hardware.encoder.worker.config
        self.init_ui()
        self.init_data()

    def init_ui(self):
        self.layout = QVBoxLayout()

        # Status label to show connection status
        self.status_label = QLabel("Click 'Start Live View' to begin.")
        self.start_button = QPushButton("Start Live View")
        self.start_button.setCheckable(True)
        self.plot_widget = pg.PlotWidget()

        self.start_button.clicked.connect(self.toggle_serial_thread)
        self.start_button.setEnabled(True)

        self.layout.addWidget(self.status_label)
        self.layout.addWidget(self.start_button)
        self.layout.addWidget(self.plot_widget)
        self.setLayout(self.layout)

        self.plot_widget.setTitle('Encoder Speed')
        self.plot_widget.setLabel('left', 'Speed', units='m/s')
        self.plot_widget.setLabel('bottom', 'Time', units='s')
        self.speed_curve = self.plot_widget.plot(pen='y')

        # Limit the range of the y-axis to +/- 2
        self.plot_widget.setYRange(-2, 2)
        self.plot_widget.showGrid(x=True, y=True)
        
        self._encoder.serialStreamStarted.connect(self.start_live_view)
        self._encoder.serialDataReceived.connect(self.process_data)
        self._encoder.serialStreamStopped.connect(self.stop_timer)
        #self.encoder.serialSpeedUpdated.connect(self.update_speed) # TODO: Implement this method

    def init_data(self):
        self.times = []
        self.speeds = []
        self.start_time = None
        self.timer = None
        self.previous_time = 0

    def start_live_view(self):
        self.status_label.setText("LIVE")
        self.start_time = time.time()
        self.init_timer()

    def toggle_serial_thread(self):
        if self.start_button.isChecked():
            self._encoder.start()
            self.status_label.setText("Serial thread started.")
        else:
            self.stop_serial_thread()
            self.status_label.setText("Serial thread stopped.")

    def stop_serial_thread(self):
        if self._encoder is not None:
            self._encoder.stop()

    def init_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(self._config.sample_interval_ms)
        self.status_label.setText("Timer started.")

    def stop_timer(self):
        if self.timer is not None:
            self.timer.stop()
            self.timer = None
            print("Timer stopped.")

    def process_data(self, position_change):
        try:
            # Use fixed delta_time based on sample interval
            delta_time = self._config.sample_interval_ms / 1000.0  # Convert milliseconds to seconds

            # Calculate speed
            speed = self.calculate_speed(position_change, delta_time)

            # Update data lists
            current_time = time.time()
            self.times.append(current_time - self.start_time)
            self.speeds.append(speed)

            # Update status label
            self.status_label.setText(f"Speed: {speed:.2f} m/s")
        except Exception as e:
            print(f"Exception in processData: {e}")

    def calculate_speed(self, delta_clicks, delta_time):
        reverse = 1  # Adjust based on your configuration

        rotations = delta_clicks / self._config.cpr
        distance = reverse * rotations * (3.1416 * self._config.diameter_cm)  # Circumference * rotations
        speed = distance / delta_time
        return speed

    def update_plot(self):
        try:
            if self.times and self.speeds:
                # Keep only the last 100 data points
                self.times = self.times[-100:]
                self.speeds = self.speeds[-100:]
                self.speed_curve.setData(self.times, self.speeds)
                # Adjust x-axis range to show recent data
                self.plot_widget.setXRange(self.times[0], self.times[-1], padding=0)
            else:
                self.plot_widget.clear()
                self.plot_widget.setTitle('No data received.')
        except Exception as e:
            print(f"Exception in updatePlot: {e}")
