import random
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
SAMPLE_INTERVAL = 20    # Update interval in milliseconds

class SerialWorker(QThread):
    
    # ===================== PyQt Signals ===================== #
    serialDataReceived = pyqtSignal(int)
    serialStreamStarted = pyqtSignal()
    serialStreamStopped = pyqtSignal()
    serialSpeedUpdated = pyqtSignal(float, float)
    # ======================================================== #

    def __init__(self, serial_port: str = None, baud_rate: int = None, sample_interval: int = None, cfg=None, development_mode=False):
        super().__init__()
        self.data_manager = DataManager()
        self.data_queue: Queue = self.data_manager.data_queue
        self.stored_data = []
        self._config: ExperimentConfig = cfg
        self.development_mode = development_mode
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.sample_interval_ms = sample_interval
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
        self.start_time = time.time()
        try:
            if self.development_mode:
                self.run_development_mode()
            else:
                self.run_serial_mode()
        finally:
            print("Simulation stopped.")

    def run_serial_mode(self):
        try:
            import serial
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
                        clicks = int(data)
                        self.stored_data.append(clicks)  # Store data for later retrieval
                        self.data_queue.put(clicks)  # Store data in the DataManager queue for access by other threads
                        self.serialDataReceived.emit(clicks)  # Emit PyQt signal for real-time plotting
                        self.process_data(clicks)
                except ValueError:
                    print(f"Non-integer data received: {data}")
                except serial.SerialException as e:
                    print(f"Serial exception: {e}")
                    self.requestInterruption()
                self.msleep(1)  # Sleep for 1ms to reduce CPU usage
        finally:
            if hasattr(self, 'arduino') and self.arduino is not None:
                try:
                    self.arduino.close()
                    print("Serial port closed.")
                except Exception as e:
                    print(f"Exception while closing serial port: {e}")

    def run_development_mode(self):
        while not self.isInterruptionRequested():
            try:
                # Simulate receiving random encoder clicks
                clicks = random.randint(1, 10)  # Simulating random click values
                
                # Emit signals, store data, and push to the queue
                self.stored_data.append(clicks)  # Store data for later retrieval
                self.data_queue.put(clicks)  # Store data in the DataManager queue for access by other threads
                self.serialDataReceived.emit(clicks)  # Emit PyQt signal for real-time plotting
                
                # Optionally, simulate processing the data for speed calculation
                self.process_data(clicks)
            except Exception as e:
                print(f"Exception in DevelopmentSerialWorker: {e}")
                self.requestInterruption()
            self.msleep(SAMPLE_INTERVAL)  # Sleep for sample interval to reduce CPU usage

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
            delta_time = self.sample_interval_ms / 1000.0  # Convert milliseconds to seconds

            # Calculate speed
            speed = self.calculate_speed(position_change, delta_time)

            # Update data lists
            current_time = time.time()
            self.times.append(current_time - self.start_time)
            self.speeds.append(speed)

            # Optionally update GUI label or emit a signal for speed update
            self.serialSpeedUpdated.emit((current_time - self.start_time), speed)
        except Exception as e:
            print(f"Exception in processData: {e}")

    def calculate_speed(self, delta_clicks, delta_time):
        reverse = -1  # Placeholder for direction configuration

        rotations = delta_clicks / ENCODER_CPR
        distance = reverse * rotations * (3.1416 * WHEEL_DIAMETER)  # Circumference * rotations
        speed = distance / delta_time
        return speed

# Usage Example:
# Replace the original SerialWorker instantiation with SerialWorker in development mode
# worker = SerialWorker(cfg=your_config, development_mode=True)
# worker.start()
