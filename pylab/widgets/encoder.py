"""
Author: jgronemeyer
Date: 2024-11-14

"""

import sys
import time
import serial
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import QTimer, pyqtSignal, QThread
import pyqtgraph as pg

from pylab.config import ExperimentConfig

# Constants
ENCODER_CPR = 360  # Encoder counts per revolution
WHEEL_DIAMETER = 0.1  # Wheel diameter in meters
SERIAL_PORT = 'COM4'  # Replace with your serial port
BAUD_RATE = 57600  # Match the Arduino's baud rate
SAMPLE_INTERVAL = 100  # Update interval in milliseconds

class SerialWorker(QThread):

    #============================== Signals =============================#
    encoderReader = pyqtSignal(int)
    #--------------------------------------------------------------------#
    
    def run(self):
        try:
            self.arduino = serial.Serial(SERIAL_PORT, BAUD_RATE)
            self.arduino.flushInput()  # Flush any existing input
        except serial.SerialException as e:
            print(f"Serial connection error: {e}")
            return
        while True:
            try:
                data = self.arduino.readline().decode('utf-8').strip()
                if data:
                    clicks = int(data)
                    self.encoderReader.emit(clicks)
            except ValueError:
                pass
            except Exception as e:
                print(f"Exception in SerialWorker: {e}")
                pass

class EncoderWidget(QWidget):
    def __init__(self, cfg: ExperimentConfig):
        super().__init__()
        self.initUI() # With this syntax we initialize the UI 
        self.initData() # and initialize the data attributes separately for maintainability
        self.config = cfg

    def initUI(self):
        self.layout = QVBoxLayout()

        # Status label to show connection status
        self.status_label = QLabel("Click 'Start Live View' to begin.")
        self.start_button = QPushButton("Start Live View")
        self.plot_widget = pg.PlotWidget()

        self.start_button.clicked.connect(self.startLiveView)
        self.start_button.setEnabled(True)


        self.layout.addWidget(self.status_label)
        self.layout.addWidget(self.start_button)
        self.layout.addWidget(self.plot_widget)
        self.setLayout(self.layout)

        self.plot_widget.setTitle('Encoder Speed')
        self.plot_widget.setLabel('left', 'Speed', units='m/s')
        self.plot_widget.setLabel('bottom', 'Time', units='s')
        self.speed_curve = self.plot_widget.plot(pen='y')

        # Limit the range of the y axis to +/- 10
        self.plot_widget.setYRange(-10, 10)
        self.plot_widget.showGrid(x=True, y=True)

    def initData(self):
        self.times = []
        self.speeds = []
        self.start_time = None
        self.serial_worker = None
        self.timer = None
        self.previous_time = 0

    def startLiveView(self):
        self.start_button.setEnabled(False)
        self.status_label.setText("Starting live view...")
        self.start_time = time.time()
        self.previous_time = self.start_time
        self.startSerialThread()
        self.initTimer()

    def startSerialThread(self):
        self.serial_worker = SerialWorker()
        self.serial_worker.encoderReader.connect(self.processData)
        self.serial_worker.start()
        self.status_label.setText("Serial thread started.")

    def initTimer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.updatePlot)
        self.timer.start(SAMPLE_INTERVAL)
        self.status_label.setText("Timer started.")

    def processData(self, position_change):
        try:
            current_time = time.time()
            delta_time = current_time - self.previous_time

            # Avoid division by zero and invalid delta_time
            if delta_time <= 0:
                return

            # Calculate speed
            speed = self.calculateSpeed(position_change, delta_time)

            # Update data lists
            self.times.append(current_time - self.start_time)
            self.speeds.append(speed)

            # Update previous time
            self.previous_time = current_time

            # Update status label
            self.status_label.setText(f"Receiving data... Speed: {speed:.2f} m/s")
        except Exception as e:
            print(f"Exception in processData: {e}")

    def calculateSpeed(self, delta_clicks, delta_time):
        reverse = -1 #TODO:if self.config.encoder_reverse else -1

        rotations = delta_clicks / ENCODER_CPR
        distance = -1 * rotations * (3.1416 * WHEEL_DIAMETER)  # Circumference * rotations
        speed = distance / delta_time
        return speed

    def updatePlot(self):
        try:
            if self.times and self.speeds:
                # Keep only the last 100 data points
                self.times = self.times[-100:]
                self.speeds = self.speeds[-100:]
                #print(f"Updating plot with {len(self.times)} data points.")
                self.speed_curve.setData(self.times, self.speeds)
                # Adjust x-axis range to show recent data
                self.plot_widget.setXRange(self.times[0], self.times[-1], padding=0)
            else:
                print("No data to plot.")
                self.plot_widget.clear()
                self.plot_widget.setTitle('No data received.')
        except Exception as e:
            print(f"Exception in updatePlot: {e}")

# if __name__ == '__main__':
#     app = QApplication(sys.argv)
#     widget = EncoderWidget()
#     widget.show()
#     sys.exit(app.exec())