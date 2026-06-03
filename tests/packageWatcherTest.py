import unittest
from unittest import TestCase
from unittest.mock import MagicMock

from context_logger import setup_logging
from package_repository import DefaultPackageWatcher, OnPackageEvent
from tests import APPLICATION_NAME, PACKAGE_DIR
from watchdog.events import FileCreatedEvent
from watchdog.observers.api import BaseObserver


class PackageWatcherTest(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging(APPLICATION_NAME, 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()

    def test_start(self):
        # Given
        observer = MagicMock(spec=BaseObserver)
        watcher = DefaultPackageWatcher(observer, PACKAGE_DIR)

        # When
        watcher.start()

        # Then
        observer.schedule.assert_called_once_with(watcher, str(PACKAGE_DIR), recursive=True)
        observer.start.assert_called_once()

    def test_stop(self):
        # Given
        observer = MagicMock(spec=BaseObserver)
        watcher = DefaultPackageWatcher(observer, PACKAGE_DIR)

        # When
        watcher.stop()

        # Then
        observer.stop.assert_called_once()

    def test_register_handler(self):
        # Given
        observer = MagicMock(spec=BaseObserver)
        watcher = DefaultPackageWatcher(observer, PACKAGE_DIR)
        handler = MagicMock(spec=OnPackageEvent)

        # When
        watcher.register(handler)

        # Then
        self.assertIn(handler, watcher._handlers)

    def test_deregister_handler(self):
        # Given
        observer = MagicMock(spec=BaseObserver)
        watcher = DefaultPackageWatcher(observer, PACKAGE_DIR)
        handler = MagicMock(spec=OnPackageEvent)

        watcher.register(handler)

        # When
        watcher.deregister(handler)

        # Then
        self.assertNotIn(handler, watcher._handlers)

    def test_handler_called_when_new_package_added(self):
        # Given
        observer = MagicMock(spec=BaseObserver)
        watcher = DefaultPackageWatcher(observer, PACKAGE_DIR)
        handler = MagicMock(spec=OnPackageEvent)

        watcher.register(handler)

        event = FileCreatedEvent(PACKAGE_DIR / 'trixie/main/new-package.deb')

        # When
        watcher.on_created(event)

        # Then
        handler.assert_called_once_with('trixie')

    def test_handler_called_when_package_renamed(self):
        # Given
        observer = MagicMock(spec=BaseObserver)
        watcher = DefaultPackageWatcher(observer, PACKAGE_DIR)
        handler = MagicMock(spec=OnPackageEvent)

        watcher.register(handler)

        event = FileCreatedEvent(PACKAGE_DIR / 'trixie/main/new-package.deb')

        # When
        watcher.on_moved(event)

        # Then
        handler.assert_called_once_with('trixie')

    def test_handler_called_when_package_removed(self):
        # Given
        observer = MagicMock(spec=BaseObserver)
        watcher = DefaultPackageWatcher(observer, PACKAGE_DIR)
        handler = MagicMock(spec=OnPackageEvent)

        watcher.register(handler)

        event = FileCreatedEvent(PACKAGE_DIR / 'trixie/main/new-package.deb')

        # When
        watcher.on_deleted(event)

        # Then
        handler.assert_called_once_with('trixie')

    def test_no_operation_when_non_package_file_added(self):
        # Given
        observer = MagicMock(spec=BaseObserver)
        watcher = DefaultPackageWatcher(observer, PACKAGE_DIR)
        handler = MagicMock(spec=OnPackageEvent)

        watcher.register(handler)

        event = FileCreatedEvent(PACKAGE_DIR / 'trixie/main/new-package.txt')

        # When
        watcher.on_created(event)

        # Then
        handler.assert_not_called()

    def test_error_handled_when_failed_to_parse_distribution(self):
        # Given
        observer = MagicMock(spec=BaseObserver)
        watcher = DefaultPackageWatcher(observer, PACKAGE_DIR)
        handler = MagicMock(spec=OnPackageEvent)

        watcher.register(handler)

        event = FileCreatedEvent('trixie/main/new-package.deb')

        # When
        watcher.on_moved(event)

        # Then
        handler.assert_not_called()

    def test_error_handled_when_failed_to_execute_handler(self):
        # Given
        observer = MagicMock(spec=BaseObserver)
        watcher = DefaultPackageWatcher(observer, PACKAGE_DIR)
        handler1 = MagicMock(spec=OnPackageEvent)
        handler1.side_effect = Exception('Handler execution failed')
        handler2 = MagicMock(spec=OnPackageEvent)

        watcher.register(handler1)
        watcher.register(handler2)

        event = FileCreatedEvent(PACKAGE_DIR / 'trixie/main/new-package.deb')

        # When
        watcher.on_deleted(event)

        # Then
        handler1.assert_called_once_with('trixie')
        handler2.assert_called_once_with('trixie')


if __name__ == "__main__":
    unittest.main()
