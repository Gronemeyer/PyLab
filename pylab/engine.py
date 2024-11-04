import pymmcore_plus
import useq
import time


from typing import TYPE_CHECKING, Iterable


if TYPE_CHECKING:
    from pymmcore_plus.core._sequencing import SequencedEvent
    from pymmcore_plus.mda.metadata import FrameMetaV1 # type: ignore
    from numpy.typing import NDArray
    from useq import MDAEvent
    PImagePayload = tuple[NDArray, MDAEvent, FrameMetaV1]
from pymmcore_plus.mda import MDAEngine

from itertools import product


class PupilEngine(MDAEngine):
    
    def setup_event(self, event: useq.MDAEvent) -> None:
        """Prepare state of system (hardware, etc.) for `event`."""
        # do some custom pre-setup
        print('START: pupil custom setup_event')
        super().setup_event(event)  
        print('DONE: pupil custom setup_event')

        # do some custom post-setup

    def exec_event(self, event: useq.MDAEvent) -> object:
        """Prepare state of system (hardware, etc.) for `event`."""
        # do some custom pre-execution
        print(f'START: pupil custom exec_event \n Event type: {type(event)}')
        result = super().exec_event(event)  
        print(f'DONE: pupil custom exec_event \n Event type: {type(event)}')

        # do some custom post-execution
        return result
    
    def exec_sequenced_event(self, event: 'SequencedEvent') -> Iterable['PImagePayload']:
        n_events = len(event.events)

        t0 = event.metadata.get("runner_t0") or time.perf_counter()
        event_t0_ms = (time.perf_counter() - t0) * 1000

        # Start sequence
        # Note that the overload of startSequenceAcquisition that takes a camera
        # label does NOT automatically initialize a circular buffer.  So if this call
        # is changed to accept the camera in the future, that should be kept in mind.
        self._mmc.startSequenceAcquisition(
            n_events,
            0,  # intervalMS  # TODO: add support for this
            True,  # stopOnOverflow
        )
        self.post_sequence_started(event)

        n_channels = self._mmc.getNumberOfCameraChannels()
        count = 0
        expected_images = n_events * n_channels
        print(f'pupil expected images: {expected_images}')
        iter_events = product(event.events, range(n_channels))
        # block until the sequence is done, popping images in the meantime
        while self._mmc.isSequenceRunning():
            if remaining := self._mmc.getRemainingImageCount():
                yield self._next_seqimg_payload(
                    *next(iter_events), remaining=remaining - 1, event_t0=event_t0_ms
                )
                count += 1
            else:
                time.sleep(0.001)
                if count == expected_images:
                    self._mmc.stopSequenceAcquisition()
                    print(f'stopped pupil MDA image overflow: {self._mmc}')
                    

        if self._mmc.isBufferOverflowed():  # pragma: no cover
            raise MemoryError("Buffer overflowed")

        while remaining := self._mmc.getRemainingImageCount():
            yield self._next_seqimg_payload(
                *next(iter_events), remaining=remaining - 1, event_t0=event_t0_ms
            )
            count += 1

    
    def teardown_sequence(self, sequence: useq.MDASequence) -> None:
        """Perform any teardown required after the sequence has been executed."""
        #core = super().mmcore
        #core.stopSequenceAcquisition
        print('DONE: pupil custom teardown')
        #mmcore_dhyana.stopSequenceAcquisition
        pass
    
class MesoEngine(MDAEngine):
    
    # def setup_sequence(self, sequence: useq.MDASequence):
    #     """Setup the hardware for the entire sequence."""
    #     # clear z_correction for new sequence
    #     print('START: meso setup_sequence')
    #     super().setup_sequence(sequence)

    #     return self.get_summary_metadata(mda_sequence=sequence)
    
    def setup_event(self, event: useq.MDAEvent) -> None:
        """Prepare state of system (hardware, etc.) for `event`."""
        # do some custom pre-setup
        print('START: meso custom setup_event')
        super().setup_event(event)  
        print('DONE: meso custom setup_event')

        # do some custom post-setup

    def exec_event(self, event: useq.MDAEvent) -> object:
        """Prepare state of system (hardware, etc.) for `event`."""
        # do some custom pre-execution
        print('START: meso custom exec_event')
        result = super().exec_event(event)  
        print('DONE: meso custom exec_event')

        # do some custom post-execution
        return result
    
    def teardown_sequence(self, sequence: useq.MDASequence) -> None:
        """Perform any teardown required after the sequence has been executed."""
        #core = super().mmcore
        #core.stopSequenceAcquisition
        print('DONE: meso custom teardown')
        #mmcore_thor.stopSequenceAcquisition
        pass

