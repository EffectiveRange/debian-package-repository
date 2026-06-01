# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

from pathlib import Path
from typing import Protocol

from context_logger import get_logger
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers.api import BaseObserver


class OnPackageEvent(Protocol):
    def __call__(self, distribution: str) -> None: ...


class PackageWatcher:

    def start(self) -> None:
        raise NotImplementedError()

    def stop(self) -> None:
        raise NotImplementedError()

    def register(self, handler: OnPackageEvent) -> None:
        raise NotImplementedError()

    def deregister(self, handler: OnPackageEvent) -> None:
        raise NotImplementedError()


class DefaultPackageWatcher(PackageWatcher, FileSystemEventHandler):

    def __init__(self, observer: BaseObserver, deb_package_dir: Path) -> None:
        self._observer = observer
        self._deb_package_dir = deb_package_dir
        self._handlers: list[OnPackageEvent] = []
        self.log = get_logger(type(self).__name__)

    def start(self) -> None:
        deb_package_dir = str(self._deb_package_dir)
        self.log.info('Watching package pool for changes', directory=deb_package_dir)
        self._observer.schedule(self, deb_package_dir, recursive=True)
        self._observer.start()

    def stop(self) -> None:
        self._observer.stop()

    def register(self, handler: OnPackageEvent) -> None:
        self._handlers.append(handler)

    def deregister(self, handler: OnPackageEvent) -> None:
        self._handlers.remove(handler)

    def on_created(self, event: FileSystemEvent) -> None:
        self._on_changed(event)

    def on_moved(self, event: FileSystemEvent) -> None:
        self._on_changed(event)

    def on_deleted(self, event: FileSystemEvent) -> None:
        self._on_changed(event)

    def _on_changed(self, event: FileSystemEvent) -> None:
        if str(event.src_path).endswith('.deb'):
            self.log.debug('File change event detected for package', event_type=event.event_type, file=event.src_path)

            try:
                relative_path = Path(str(event.src_path)).relative_to(self._deb_package_dir)
                distribution = relative_path.parts[0]

                for handler in self._handlers:
                    self._execute_handler(handler, distribution)
            except Exception as error:
                self.log.error('Could not determine distribution from file path', error=error, file=event.src_path)
        else:
            self.log.debug('File change event, ignoring as not a package',
                           event_type=event.event_type, file=event.src_path)

    def _execute_handler(self, handler: OnPackageEvent, distribution: str) -> None:
        try:
            handler(distribution)
        except Exception as error:
            self.log.error('Error when executing package event handler', error=error, distribution=distribution)
