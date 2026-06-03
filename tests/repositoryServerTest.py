import unittest
from threading import Thread
from unittest import TestCase
from unittest.mock import MagicMock

from context_logger import setup_logging
from package_repository import RepositoryService, DirectoryService, DefaultRepositoryServer
from test_utility import wait_for_assertion
from tests import APPLICATION_NAME


class RepositoryServerTest(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging(APPLICATION_NAME, 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()

    def test_startup_and_shutdown(self):
        # Given
        repository_service, directory_service = create_components()

        with DefaultRepositoryServer(repository_service, directory_service) as repository_server:
            # When
            Thread(target=repository_server.run).start()

            # Then
            wait_for_assertion(1, lambda: repository_service.start.assert_called_once())
            wait_for_assertion(1, lambda: directory_service.start.assert_called_once())

        repository_service.stop.assert_called_once()
        directory_service.start.assert_called_once()


def create_components():
    repository_service = MagicMock(spec=RepositoryService)
    directory_service = MagicMock(spec=DirectoryService)
    return repository_service, directory_service


if __name__ == "__main__":
    unittest.main()
