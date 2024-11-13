from contextlib import suppress
from typing import List, Tuple, Union, Literal
import numpy as np
from pymmcore_plus import CMMCorePlus
from qtpy.QtCore import Qt, QTimer
from qtpy.QtGui import QImage, QPixmap
from qtpy.QtWidgets import QHBoxLayout, QLabel, QWidget
from threading import Lock
from functools import partial

class ImagePreview(QWidget):
    """
    A PyQt widget that displays images from one or two `CMMCorePlus` instances (mmc cores).

    This widget is designed to display images from one or two `CMMCorePlus` instances
    simultaneously, updating the display in real-time as new images are captured from
    each core. The widget adapts dynamically based on the number of cores provided,
    displaying a single image when one core is given or multiple images when more cores
    are provided.

    The images are displayed using PyQt's `QLabel` and `QPixmap`, allowing for efficient
    rendering without external dependencies like VisPy.

    **Parameters**
    ----------
    parent : QWidget, optional
        The parent widget. Defaults to `None`.
    mmcores : List[CMMCorePlus]
        A list containing one or two `CMMCorePlus` instances from which images will be displayed.
        Each `CMMCorePlus` instance represents a separate microscope control core.
    use_with_mda : bool, optional
        If `True`, the widget will update during Multi-Dimensional Acquisitions (MDA).
        If `False`, the widget will not update during MDA. Defaults to `True`.

    **Attributes**
    ----------
    clims : Union[Tuple[float, float], Literal["auto"]]
        The contrast limits for the image display. If set to `"auto"`, the widget will
        automatically adjust the contrast limits based on the image data.
    cmap : str
        The colormap to use for the image display. Currently set to `"grayscale"`.

    **Notes**
    -----
    - The widget adapts to the number of mmc cores provided:
        - If one core is provided, it displays a single image centered in the widget.
        - If two cores are provided, it displays the images side by side.

    - Uses `QLabel` widgets to display images. Each image is displayed
      in a separate label. Labels are set to scale images to fit their size
      (`setScaledContents(True)`).

    - Converts images from the `CMMCorePlus` instances to `uint8`
      and scales them appropriately for display using `QImage` and `QPixmap`.

    - Connects to events emitted by each `CMMCorePlus` instance:
        - `imageSnapped`: Emitted when a new image is snapped from a Core.
        - `continuousSequenceAcquisitionStarted` and `sequenceAcquisitionStarted`: Emitted when
          a Core sequence acquisition starts.
        - `sequenceAcquisitionStopped`: Emitted when a Core sequence acquisition stops.
        - `exposureChanged`: Emitted when a Core camera exposure time changes.
        - `frameReady` (MDA): Emitted when a new frame is ready during MDA.

    - Uses threading (`Lock`) to ensure thread-safe movement of frames for display. 
      UI updates are performed in the main thread using Qt's signals and slots mechanism, 
      ensuring thread safety.

    - Adjustable contrast limits (`clims`) and colormap (`cmap`) for the images. 
      By default, only grayscale images are supported.

    **Private Methods**
    ----------------
    internal functionality:

    - `_disconnect()`: Disconnects all connected signals from the `CMMCorePlus` instances.
    - `_on_streaming_start(idx)`: Starts the streaming timer when a sequence acquisition starts.
    - `_on_streaming_stop(idx)`: Stops the streaming timer when all sequence acquisitions stop.
    - `_on_exposure_changed(idx, device, value)`: Adjusts the timer interval when the exposure changes.
    - `_on_streaming_timeout()`: Called periodically by the timer to fetch and display new images.
    - `_on_image_snapped(idx, img)`: Handles new images snapped outside of sequences.
    - `_on_frame_ready(idx, event)`: Handles new frames ready during MDA.
    - `_update_images(frames)`: Updates the display with new images from all cores.
    - `_display_image(idx, img)`: Converts and displays a single image in the corresponding label.
    - `_update_image(idx, img)`: Stores a new image for later display.
    - `_adjust_image_data(img)`: Scales image data to `uint8` for display.
    - `_convert_to_qimage(img)`: Converts a NumPy array to a `QImage` for display.


    **Examples with Single and Multiple Cores**
    ------------------------------------
    **With One Core**:
    ```python
    mmc = CMMCorePlus()
    image_preview = ImagePreview(mmcores=[mmc])
    ```

    **With Two Cores**:
    ```python
    mmc1 = CMMCorePlus()
    mmc2 = CMMCorePlus()
    image_preview = ImagePreview(mmcores=[mmc1, mmc2])
    ```

    **Handling Image Contrast and Colormap**
    -------------------------------------
    You can set the contrast limits and colormap as follows:
    ```python
    image_preview.clims = (100, 1000)  # Set contrast limits
    image_preview.cmap = "grayscale"   # Set colormap
    ```

    **Extending to More Cores**
    -----------------------
    While currently designed for up to two cores, the widget can be extended to handle more cores by adjusting the initialization and layout logic.

    **Error Handling**
    ---------------
    The widget raises a `ValueError` if more than two cores are provided or if the `mmcores` list is empty.

    **Performance Considerations**
    --------------------------
    - **Frame Rate**: The default timer interval is set to 10 milliseconds. Adjust the interval for performance.
    - **Resource Management**: Disconnect signals properly by ensuring the `_disconnect()` method is called when the widget is destroyed.

    """

    def __init__(self, parent: QWidget = None, *, 
                 mmcores: List[CMMCorePlus], 
                 use_with_mda: bool = True):
        super().__init__(parent=parent)
        if not mmcores or len(mmcores) > 2:
            raise ValueError("Provide one or two mmc cores.")
        self._mmcores = mmcores  # List of mmc cores
        self._use_with_mda = use_with_mda
        self._num_cores = len(mmcores)
        self._clims: Union[Tuple[float, float], Literal["auto"]] = "auto"
        self._cmap: str = "grayscale"
        self._current_frames = [None] * self._num_cores
        self._frame_locks = [Lock() for _ in range(self._num_cores)]

        # Set up image labels
        self.image_labels = []
        for _ in range(self._num_cores):
            label = QLabel()
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setMinimumSize(512, 512)
            label.setScaledContents(True)  # Allow image scaling
            self.image_labels.append(label)

        # Set up layouts
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        for label in self.image_labels:
            self.layout().addWidget(label)

        # Set up timer
        self.streaming_timer = QTimer(parent=self)
        self.streaming_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.streaming_timer.setInterval(10)  # Default interval; adjust as needed
        self.streaming_timer.timeout.connect(self._on_streaming_timeout)

        # Connect events for each mmc core
        for idx, mmc in enumerate(self._mmcores):
            ev = mmc.events
            ev.imageSnapped.connect(partial(self._on_image_snapped, idx))
            ev.continuousSequenceAcquisitionStarted.connect(partial(self._on_streaming_start, idx))
            ev.sequenceAcquisitionStarted.connect(partial(self._on_streaming_start, idx))
            ev.sequenceAcquisitionStopped.connect(partial(self._on_streaming_stop, idx))
            ev.exposureChanged.connect(partial(self._on_exposure_changed, idx))

            enev = mmc.mda.events
            enev.frameReady.connect(
                partial(self._on_frame_ready, idx),
                type=Qt.ConnectionType.QueuedConnection  # Ensure the slot is called in the main thread
            )

        self.destroyed.connect(self._disconnect)

    def _disconnect(self) -> None:
        # Disconnect events for each mmc core
        for idx, mmc in enumerate(self._mmcores):
            ev = mmc.events
            with suppress(TypeError):
                ev.imageSnapped.disconnect()
                ev.continuousSequenceAcquisitionStarted.disconnect()
                ev.sequenceAcquisitionStarted.disconnect()
                ev.sequenceAcquisitionStopped.disconnect()
                ev.exposureChanged.disconnect()

            enev = mmc.mda.events
            with suppress(TypeError):
                enev.frameReady.disconnect()

    def _on_streaming_start(self, idx: int) -> None:
        if not self.streaming_timer.isActive():
            self.streaming_timer.start()

    def _on_streaming_stop(self, idx: int) -> None:
        # Check if any mmc core is still streaming
        if not any(mmc.isSequenceRunning() for mmc in self._mmcores):
            self.streaming_timer.stop()

    def _on_exposure_changed(self, idx: int, device: str, value: str) -> None:
        # Adjust timer interval if needed
        exposures = [mmc.getExposure() or 10 for mmc in self._mmcores]
        interval = int(max(exposures)) or 10
        self.streaming_timer.setInterval(interval)

    def _on_streaming_timeout(self) -> None:
        # NOTE: This method is called at a rate defined by the timer interval (ie. 10ms)
        frames = []
        for idx, mmc in enumerate(self._mmcores):
            frame = None
            if not mmc.mda.is_running():
                with suppress(RuntimeError, IndexError):
                    frame = mmc.getLastImage()
            else:
                with self._frame_locks[idx]:
                    if self._current_frames[idx] is not None:
                        frame = self._current_frames[idx]
                        self._current_frames[idx] = None
            frames.append(frame)
        # Update the images if frames are available
        self._update_images(frames)

    def _on_image_snapped(self, idx: int, img: np.ndarray) -> None:
        self._update_image(idx, img)

    def _on_frame_ready(self, idx: int, event) -> None:
        frame = event.image  # Adjust based on actual event attributes
        with self._frame_locks[idx]:
            self._current_frames[idx] = frame

    def _update_images(self, frames: List[np.ndarray]) -> None:
        for idx, frame in enumerate(frames):
            if frame is not None:
                self._display_image(idx, frame)

    def _display_image(self, idx: int, img: np.ndarray) -> None:
        if img is None:
            return
        qimage = self._convert_to_qimage(img)
        if qimage is not None:
            pixmap = QPixmap.fromImage(qimage)
            self.image_labels[idx].setPixmap(pixmap)

    def _update_image(self, idx: int, img: np.ndarray) -> None:
        # Update the frame for the specific core
        with self._frame_locks[idx]:
            self._current_frames[idx] = img

    def _adjust_image_data(self, img: np.ndarray) -> np.ndarray:
        # NOTE: This is the default implementation for grayscale images
        # NOTE: This is the most processor-intensive part of this widget
        
        # Ensure the image is in float format for scaling
        img = img.astype(np.float32, copy=False)

        # Apply contrast limits
        if self._clims == "auto":
            min_val, max_val = np.min(img), np.max(img)
        else:
            min_val, max_val = self._clims

        # Avoid division by zero
        scale = 255.0 / (max_val - min_val) if max_val != min_val else 255.0

        # Scale to 0-255
        img = np.clip((img - min_val) * scale, 0, 255).astype(np.uint8, copy=False)
        return img

    def _convert_to_qimage(self, img: np.ndarray) -> QImage:
        """Convert a NumPy array to QImage."""
        if img is None:
            return None
        img = self._adjust_image_data(img)
        img = np.ascontiguousarray(img)
        height, width = img.shape[:2]

        if img.ndim == 2:
            # Grayscale image
            bytes_per_line = width
            qimage = QImage(img.data, width, height, bytes_per_line, QImage.Format.Format_Grayscale8)
        else:
            # Handle other image formats if needed
            return None

        return qimage

    @property
    def clims(self) -> Union[Tuple[float, float], Literal["auto"]]:
        """Get the contrast limits of the image."""
        return self._clims

    @clims.setter
    def clims(self, clims: Union[Tuple[float, float], Literal["auto"]] = "auto") -> None:
        """Set the contrast limits of the image.

        Parameters
        ----------
        clims : tuple[float, float], or "auto"
            The contrast limits to set.
        """
        self._clims = clims

    @property
    def cmap(self) -> str:
        """Get the colormap (lookup table) of the image."""
        return self._cmap

    @cmap.setter
    def cmap(self, cmap: str = "grayscale") -> None:
        """Set the colormap (lookup table) of the image.

        Parameters
        ----------
        cmap : str
            The colormap to use.
        """
        self._cmap = cmap
