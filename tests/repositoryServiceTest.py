import signal
import unittest
from unittest import TestCase
from unittest.mock import MagicMock, call, patch

from context_logger import setup_logging
from package_repository import PackageWatcher, RepositoryCreator, RepositorySigner, RepositoryCache, \
    DefaultRepositoryService, MetadataLoader
from test_utility import wait_for_assertion
from tests import APPLICATION_NAME


class RepositoryServiceTest(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging(APPLICATION_NAME, 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()

    def test_start(self):
        # Given
        watcher, creator, signer, cache, loader = create_components()
        service = DefaultRepositoryService(watcher, creator, signer, cache, loader, {'bookworm', 'trixie'}, 0.1)

        # When
        service.start()

        # Then
        cache.initialize.assert_called_once()
        cache.switch.assert_has_calls([call('bookworm'), call('trixie')], any_order=True)
        creator.initialize.assert_called_once()
        creator.create.assert_has_calls([call('bookworm'), call('trixie')], any_order=True)
        signer.initialize.assert_called_once()
        signer.sign.assert_has_calls([call('bookworm'), call('trixie')], any_order=True)
        watcher.register.assert_called_once_with(service._handle_event)
        watcher.start.assert_called_once()
        loader.load.assert_has_calls([call('bookworm'), call('trixie')], any_order=True)

    def test_stop(self):
        # Given
        watcher, creator, signer, cache, loader = create_components()
        service = DefaultRepositoryService(watcher, creator, signer, cache, loader, {'bookworm', 'trixie'}, 0.1)

        # When
        service.stop()

        # Then
        watcher.deregister.assert_called_once_with(service._handle_event)
        watcher.stop.assert_called_once()

    def test_event_handled(self):
        # Given
        watcher, creator, signer, cache, loader = create_components()
        service = DefaultRepositoryService(watcher, creator, signer, cache, loader, {'bookworm', 'trixie'}, 0.1)

        # When
        service._handle_event('trixie')

        # Then
        wait_for_assertion(1, lambda: cache.switch.assert_called_once_with('trixie'))
        creator.create.assert_called_once_with('trixie')
        signer.sign.assert_called_once_with('trixie')

    def test_event_handled_when_another_event_is_handled(self):
        # Given
        watcher, creator, signer, cache, loader = create_components()
        service = DefaultRepositoryService(watcher, creator, signer, cache, loader, {'bookworm', 'trixie'}, 0.1)

        service._handle_event('trixie')

        # When
        service._handle_event('trixie')

        # Then
        wait_for_assertion(1, lambda: cache.switch.assert_called_once_with('trixie'))
        creator.create.assert_called_once_with('trixie')
        signer.sign.assert_called_once_with('trixie')

    def test_event_not_handled_when_unsupported(self):
        # Given
        watcher, creator, signer, cache, loader = create_components()
        service = DefaultRepositoryService(watcher, creator, signer, cache, loader, {'bookworm', 'trixie'}, 0.1)

        # When
        service._handle_event('unsupported')

        # Then
        creator.create.assert_not_called()
        signer.sign.assert_not_called()
        cache.switch.assert_not_called()

    @patch('package_repository.repositoryService.signal.raise_signal')
    def test_update_repository_when_creator_fails_raises_sigint(self, mock_raise_signal):
        # Given
        watcher, creator, signer, cache, loader = create_components()
        creator.create.side_effect = RuntimeError('boom')
        service = DefaultRepositoryService(watcher, creator, signer, cache, loader, {'bookworm', 'trixie'}, 0.1)

        # When
        service._update_repository('trixie')

        # Then
        mock_raise_signal.assert_called_once_with(signal.SIGINT)
        signer.sign.assert_not_called()
        cache.switch.assert_not_called()


def create_components():
    watcher = MagicMock(spec=PackageWatcher)
    creator = MagicMock(spec=RepositoryCreator)
    signer = MagicMock(spec=RepositorySigner)
    cache = MagicMock(spec=RepositoryCache)
    loader = MagicMock(spec=MetadataLoader)

    return watcher, creator, signer, cache, loader


if __name__ == "__main__":
    unittest.main()
