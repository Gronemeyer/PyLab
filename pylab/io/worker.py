import serial
import time
from queue import Queue

from PyQt6.QtCore import pyqtSignal, QThread

from pylab.io import DataManager

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pylab.config import ExperimentConfig


# Constants
ENCODER_CPR = 360       # Encoder counts per revolution
WHEEL_DIAMETER = 0.1    # Wheel diameter in meters
SERIAL_PORT = 'COM4'    # Replace with your serial port
BAUD_RATE = 57600       # Match the Arduino's baud rate
SAMPLE_INTERVAL = 20   # Update interval in milliseconds

class SerialWorker(QThread):
    
    # ===================== PyQt Signals ===================== #
    serialDataReceived = pyqtSignal(int)
    serialStreamStarted = pyqtSignal()
    serialStreamStopped = pyqtSignal()
    serialSpeedUpdated = pyqtSignal(float)
    # ======================================================== #

    def __init__(self, serial_port, baud_rate, cfg = None):
        super().__init__()
        self.serial_port = str(serial_port)
        self.baud_rate = int(baud_rate)
        self.data_manager= DataManager()
        self.data_queue: Queue = self.data_manager.data_queue
        self.arduino = None
        self.stored_data = []
        self._config: ExperimentConfig = cfg
        self.init_data()

    def init_data(self):
        self.times = []
        self.speeds = []
        self.start_time = None

    def start(self) -> None:
        self.serialStreamStarted.emit()
        return super().start()

    def run(self):
        self.init_data()
        try:
            self.arduino = serial.Serial(self.serial_port, self.baud_rate, timeout=0.1)
            self.arduino.flushInput()  # Flush any existing input
            print("Serial port opened.")
        except serial.SerialException as e:
            print(f"Serial connection error: {e}")
            return
        
        try:
            while not self.isInterruptionRequested():
                try:
                    data = self.arduino.readline().decode('utf-8').strip()
                    if data:
                        try:
                            clicks = int(data)
                            #print(f"Received data: {clicks}")
                            self.stored_data.append(clicks) # Store data for later retrieval
                            self.data_queue.put(clicks) # Store data in the DataManager queue for access by other threads
                            self.serialDataReceived.emit(clicks) # Emit PyQt signal for real-time plotting
                            #self.process_data(clicks) # Process the data for speed calculation
                        except ValueError:
                            print(f"Non-integer data received: {data}")
                except serial.SerialException as e:
                    print(f"Serial exception: {e}")
                    self.requestInterruption()
                except Exception as e:
                    print(f"Exception in SerialWorker: {e}")
                    self.requestInterruption()
                self.msleep(1)  # Sleep for 1ms to reduce CPU usage
        finally:
            if self.arduino is not None:
                try:
                    self.arduino.close()
                    print("Serial port closed.")
                except Exception as e:
                    print(f"Exception while closing serial port: {e}")

    def stop(self):
        self.requestInterruption()
        self.wait()
        self.serialStreamStopped.emit()
        
    def get_data(self):
        experiment_data = self.stored_data
        self.stored_data = []
        return experiment_data
    
    def process_data(self, position_change):
        try:
            # Use fixed delta_time based on sample interval
            delta_time = 20 / 1000.0  # Convert milliseconds to seconds

            # Calculate speed
            speed = self.calculate_speed(position_change, delta_time)

            # Update data lists
            current_time = time.time()
            self.times.append(current_time - self.start_time)
            self.speeds.append(speed)

            # Update status label
            self.status_label.setText(f"Receiving data... Speed: {speed:.2f} m/s")
        except Exception as e:
            print(f"Exception in processData: {e}")

    def calculate_speed(self, delta_clicks, delta_time):
        reverse = -1 #TODO:if self.config.encoder_reverse else -1

        rotations = delta_clicks / ENCODER_CPR
        distance = -1 * rotations * (3.1416 * WHEEL_DIAMETER)  # Circumference * rotations
        speed = distance / delta_time
        #self.serialSpeedUpdated.emit(speed)
