import signal
import unittest
from concurrent.futures import ThreadPoolExecutor, Future
from importlib.metadata import version
from pathlib import Path
from threading import Thread, Event
from unittest import TestCase
from unittest.mock import MagicMock

import requests
from common_utility import delete_directory, render_template_file
from context_logger import setup_logging
from gnupg import GPG
from package_repository import DefaultDirectoryService, DefaultRepositoryService, DirectoryConfig, \
    DefaultDirectoryServer, ServerConfig, DefaultRepositoryCache, DefaultRepositorySigner, DefaultRepositoryCreator, \
    RepositoryConfig, DefaultPackageWatcher, PublicGpgKey, PrivateGpgKey, DefaultRepositoryServer, ReleaseInfo
from test_utility import wait_for_condition, compare_lines
from tests import create_test_packages, TEST_RESOURCE_ROOT, RESOURCE_ROOT, REPOSITORY_DIR, APPLICATION_NAME, \
    PACKAGE_DIR, RELEASE_TEMPLATE_PATH
from watchdog.observers import Observer

APP_VERSION = '1.0.0'
PRIVATE_KEY_PATH = Path(f'{TEST_RESOURCE_ROOT}/keys/private-key.asc')
PUBLIC_KEY_PATH = Path(f'{TEST_RESOURCE_ROOT}/keys/public-key.asc')
PUBLIC_KEY_NAME = 'repository.gpg.key'
KEY_ID = 'C1AEE2EDBAEC37595801DDFAE15BC62117A4E0F3'
PASSPHRASE = 'test1234'
SERVER_HOST = 'http://127.0.0.1'
SERVER_PORT = 9000
DIRECTORY_TEMPLATE_PATH = Path(f'{RESOURCE_ROOT}/templates/directory.j2')
DISTRIBUTIONS = {'bookworm', 'trixie'}
COMPONENTS = {'main'}
ARCHITECTURES = {'amd64', 'arm64'}


class RepositoryServerIntegrationTest(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging(APPLICATION_NAME, 'DEBUG', warn_on_overwrite=False)
        delete_directory(PACKAGE_DIR)
        create_test_packages(PACKAGE_DIR, 'bookworm')
        create_test_packages(PACKAGE_DIR, 'trixie')

    def setUp(self):
        print()

    def test_http_server_repository_tree_mapping(self):
        # Given
        repository_service, directory_service, directory_server = create_components()

        with DefaultRepositoryServer(repository_service, directory_service) as repository_server:
            Thread(target=repository_server.run).start()
            wait_for_condition(5, lambda: directory_server.is_running())

            # When
            response = requests.get(f'{SERVER_HOST}:{SERVER_PORT}/dists/trixie/Release', timeout=0.1)

            # Then
            self.assertEqual(200, response.status_code)
            expected_lines = render_template_file(
                RELEASE_TEMPLATE_PATH,
                {
                    'origin': APPLICATION_NAME,
                    'label': APPLICATION_NAME,
                    'codename': 'trixie',
                    'version': version(APPLICATION_NAME),
                    'architectures': 'all amd64 arm64',
                    'components': 'main',
                },
            ).splitlines(True)
            expected_lines.append(f'SignWith: {KEY_ID}')
            actual_lines = response.content.decode(response.apparent_encoding).splitlines(True)
            exclusions = ['', 'Date', 'Packages']
            all_matches = compare_lines(expected_lines, actual_lines, exclusions)

            self.assertTrue(all_matches)

        wait_for_condition(1, lambda: not directory_server.is_running())

    def test_http_server_verification_key_mapping(self):
        # Given
        repository_service, directory_service, directory_server = create_components()

        with DefaultRepositoryServer(repository_service, directory_service) as repository_server:
            Thread(target=repository_server.run).start()
            wait_for_condition(5, lambda: directory_server.is_running())

            # When
            response = requests.get(f'{SERVER_HOST}:{SERVER_PORT}/{PUBLIC_KEY_NAME}', timeout=0.1)

            # Then
            self.assertEqual(200, response.status_code)
            with open(PUBLIC_KEY_PATH, 'r') as expected_file:
                expected_content = expected_file.read()
                actual_content = response.content.decode(response.apparent_encoding)

                self.assertEqual(expected_content, actual_content)

        wait_for_condition(1, lambda: not directory_server.is_running())

    def test_http_server_package_file_mapping(self):
        # Given
        repository_service, directory_service, directory_server = create_components()

        with DefaultRepositoryServer(repository_service, directory_service) as repository_server:
            Thread(target=repository_server.run).start()
            wait_for_condition(3, lambda: directory_server.is_running())

            response = requests.get(f'{SERVER_HOST}:{SERVER_PORT}/dists/trixie/main/binary-amd64/Packages', timeout=0.1)
            self.assertEqual(200, response.status_code)
            packages_lines = response.content.decode(response.apparent_encoding).splitlines()
            package_path = filter(lambda x: x.startswith('Filename:'), packages_lines).__next__().split(' ')[1]

            # When
            response = requests.get(f'{SERVER_HOST}:{SERVER_PORT}/{package_path}', timeout=0.1)

            # Then
            self.assertEqual(200, response.status_code)
            with open(f'{PACKAGE_DIR}/trixie/main/hello-world_0.0.1-1_amd64.deb', 'rb') as expected_file:
                expected_content = expected_file.read()
                actual_content = response.content

                self.assertEqual(expected_content, actual_content)

        wait_for_condition(1, lambda: not directory_server.is_running())

    def test_http_server_with_multiple_concurrent_requests(self):
        # Given
        repository_service, directory_service, directory_server = create_components()

        with DefaultRepositoryServer(repository_service, directory_service) as repository_server:
            Thread(target=repository_server.run).start()
            wait_for_condition(3, lambda: directory_server.is_running())
            request_count = 100
            executor = ThreadPoolExecutor(max_workers=request_count)
            timeout = 1
            futures: list[Future] = []
            responses = []

            def send_request():
                try:
                    response = requests.get(
                        f'{SERVER_HOST}:{SERVER_PORT}/dists/trixie/main/binary-amd64/Packages', timeout=timeout)
                    responses.append(response)
                except requests.exceptions.RequestException as e:
                    print(f'Exception raised: {e}')

            # When
            for index in range(request_count):
                future = executor.submit(send_request)
                futures.append(future)

            # Then
            for future in futures:
                future.result(timeout)
            self.assertEqual(request_count, len(responses))
            for response in responses:
                self.assertEqual(200, response.status_code)

        wait_for_condition(1, lambda: not directory_server.is_running())

    def test_update_repository_when_creation_fails_sends_sigint(self):
        # Given
        repository_service, _, _ = create_components()
        repository_service._creator.create = MagicMock(side_effect=RuntimeError('mocked failure'))
        handler_called = Event()
        original_handler = signal.getsignal(signal.SIGINT)

        def mock_signal_handler(signum, frame):
            if signum == signal.SIGINT:
                handler_called.set()

        signal.signal(signal.SIGINT, mock_signal_handler)

        try:
            # When
            repository_service._update_repository('trixie')

            # Then
            wait_for_condition(1, lambda: handler_called.is_set())
        finally:
            # Restore original (test runner) signal handler
            signal.signal(signal.SIGINT, original_handler)


def create_components():
    file_observer = Observer()
    package_watcher = DefaultPackageWatcher(file_observer, PACKAGE_DIR)
    repository_cache = DefaultRepositoryCache({'bookworm', 'trixie'})
    repository_config = RepositoryConfig(DISTRIBUTIONS, COMPONENTS, ARCHITECTURES, REPOSITORY_DIR, PACKAGE_DIR)
    release_info = ReleaseInfo(RELEASE_TEMPLATE_PATH, APPLICATION_NAME, APPLICATION_NAME,
                               'stable', APP_VERSION, 'Test repository')
    repository_creator = DefaultRepositoryCreator(repository_cache, repository_config, release_info)
    private_key = PrivateGpgKey(KEY_ID, PRIVATE_KEY_PATH, PASSPHRASE)
    public_key = PublicGpgKey(KEY_ID, PUBLIC_KEY_PATH, PUBLIC_KEY_NAME)
    repository_signer = DefaultRepositorySigner(repository_cache, GPG(), private_key, public_key, REPOSITORY_DIR)
    repository_service = DefaultRepositoryService(package_watcher, repository_creator, repository_signer,
                                                  repository_cache, DISTRIBUTIONS, 0.1)

    server_config = ServerConfig([f'*:{SERVER_PORT}'], 'http', "", 32, 1024, 1000, 60)
    directory_server = DefaultDirectoryServer(server_config)
    directory_config = DirectoryConfig(REPOSITORY_DIR, APP_VERSION, DIRECTORY_TEMPLATE_PATH)
    directory_service = DefaultDirectoryService(directory_server, repository_cache, directory_config)

    return repository_service, directory_service, directory_server


if __name__ == "__main__":
    unittest.main()
