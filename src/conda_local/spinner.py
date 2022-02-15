import sys
from errno import EPIPE, ESHUTDOWN
from itertools import cycle
from threading import Event, Thread
from time import sleep
from typing import Final, TextIO


class Spinner:

    _indicator_cycle: Final = cycle(r"/-\|")

    def __init__(
        self, message: str, enabled: bool = True, stream: TextIO = sys.stdout
    ) -> None:
        self.message = message
        self._stop_running = Event()
        self._spinner_thread = Thread(target=self._task)
        self._indicator_length = len(next(self._indicator_cycle)) + 1
        self._stream = stream
        self._show_spin = enabled

    def start(self) -> None:
        if self._show_spin:
            self._write(f"{self.message}: ")
            self._spinner_thread.start()

    def stop(self) -> None:
        if self._show_spin:
            self._stop_running.set()
            self._spinner_thread.join()
            self._write("\r")

    def _task(self) -> None:
        try:
            while not self._stop_running.is_set():
                indicator = next(self._indicator_cycle)
                self._write(indicator.ljust(self._indicator_length))
                sleep(0.10)
                self._write("\b" * self._indicator_length)
        except EnvironmentError as e:
            if e.errno in (EPIPE, ESHUTDOWN):
                self.stop()
            else:
                raise

    def _write(self, text: str) -> None:
        self._stream.write(text)
        self._stream.flush()

    def __enter__(self) -> None:
        self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        if exc_type or exc_val:
            pass


if __name__ == "__main__":
    enabled = True
    if len(sys.argv) > 1:
        enabled = False
    with Spinner("Testing Custom Spinner", enabled=enabled):
        sleep(5)
