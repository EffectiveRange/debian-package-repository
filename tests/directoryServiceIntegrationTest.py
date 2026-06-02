import gzip
import os
import unittest
from io import BytesIO
from pathlib import Path
from unittest import TestCase

from common_utility import delete_directory, create_file, create_directory
from context_logger import setup_logging
from package_repository import DefaultDirectoryServer, ServerConfig, DirectoryConfig, DefaultDirectoryService, \
    DefaultRepositoryCache
from test_utility import wait_for_condition
from tests import (
    create_test_packages,
    TEST_RESOURCE_ROOT,
    RESOURCE_ROOT, REPOSITORY_DIR, APPLICATION_NAME
)

PACKAGE_DIR = Path(f'{TEST_RESOURCE_ROOT}/test-debs')


class DirectoryServiceTest(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging(APPLICATION_NAME, 'DEBUG', warn_on_overwrite=False)
        delete_directory(REPOSITORY_DIR)
        delete_directory(PACKAGE_DIR)
        create_test_packages(PACKAGE_DIR, 'trixie')
        create_directory(REPOSITORY_DIR)
        os.symlink(PACKAGE_DIR, REPOSITORY_DIR / 'pool', target_is_directory=True)

    def setUp(self):
        print()

    def test_startup_and_shutdown(self):
        # Given
        web_server, cache, config = create_components()

        with DefaultDirectoryService(web_server, cache, config) as directory_service:
            # When
            directory_service.start()

            # Then
            wait_for_condition(1, lambda: web_server.is_running())

        wait_for_condition(1, lambda: not web_server.is_running())

    def test_returns_200_when_accessing_public_directory(self):
        # Given
        web_server, cache, config = create_components()

        with DefaultDirectoryService(web_server, cache, config) as directory_service:
            # When
            directory_service.start()

            wait_for_condition(1, lambda: web_server.is_running())

            client = web_server._app.test_client()

            # When
            response = client.get('/')

            # Then
            self.assertEqual(200, response.status_code)

    def test_returns_200_when_accessing_public_text_file(self):
        # Given
        web_server, cache, config = create_components()
        file_path = PACKAGE_DIR / 'trixie/info.txt'
        file_content = 'This is a test file.'
        create_file(file_path, file_content)

        with DefaultDirectoryService(web_server, cache, config) as directory_service:
            # When
            directory_service.start()

            wait_for_condition(1, lambda: web_server.is_running())

            client = web_server._app.test_client()

            # When
            response = client.get('/pool/trixie/info.txt')

            # Then
            self.assertEqual(200, response.status_code)
            self.assertEqual(file_content.encode(), response.data)

    def test_returns_200_when_accessing_public_binary_file(self):
        # Given
        web_server, cache, config = create_components()

        with DefaultDirectoryService(web_server, cache, config) as directory_service:
            # When
            directory_service.start()

            wait_for_condition(1, lambda: web_server.is_running())

            client = web_server._app.test_client()

            # When
            response = client.get('/pool/trixie/main/hello-world_0.0.1-1_amd64.deb')

            # Then
            self.assertEqual(200, response.status_code)
            with open(PACKAGE_DIR / 'trixie/main/hello-world_0.0.1-1_amd64.deb', 'rb') as file:
                self.assertEqual(file.read(), response.data)

    def test_returns_404_when_accessing_non_cached_file(self):
        # Given
        web_server, cache, config = create_components()

        with DefaultDirectoryService(web_server, cache, config) as directory_service:
            # When
            directory_service.start()

            wait_for_condition(1, lambda: web_server.is_running())

            client = web_server._app.test_client()

            # When
            response = client.get('/dists/trixie/info')

            # Then
            self.assertEqual(404, response.status_code)

    def test_returns_200_when_accessing_cached_extensionless_file(self):
        # Given
        web_server, cache, config = create_components()
        file_path = REPOSITORY_DIR / 'dists/trixie/info'
        file_content = b'This is a test file.'
        cache._read_cache['trixie'][file_path] = file_content

        with DefaultDirectoryService(web_server, cache, config) as directory_service:
            # When
            directory_service.start()

            wait_for_condition(1, lambda: web_server.is_running())

            client = web_server._app.test_client()

            # When
            response = client.get('/dists/trixie/info')

            # Then
            self.assertEqual(200, response.status_code)
            self.assertEqual('text/plain; charset=utf-8', response.content_type)
            self.assertEqual(file_content, response.data)

    def test_returns_200_when_accessing_cached_text_file(self):
        # Given
        web_server, cache, config = create_components()
        file_path = REPOSITORY_DIR / 'dists/trixie/info.txt'
        file_content = b'This is a test file.'
        cache._read_cache['trixie'][file_path] = file_content

        with DefaultDirectoryService(web_server, cache, config) as directory_service:
            # When
            directory_service.start()

            wait_for_condition(1, lambda: web_server.is_running())

            client = web_server._app.test_client()

            client.get('/dists/trixie/info.txt')

            # When
            response = client.get('/dists/trixie/info.txt')

            # Then
            self.assertEqual(200, response.status_code)
            self.assertEqual('text/plain; charset=utf-8', response.content_type)
            self.assertEqual(file_content, response.data)

    def test_returns_200_when_accessing_cached_binary_file(self):
        # Given
        web_server, cache, config = create_components()
        compressed_path = REPOSITORY_DIR / 'dists/trixie/info.gz'
        file_content = b'This is a test file.'
        buffer = BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode='wb') as gz:
            gz.write(file_content)
        cache._read_cache['trixie'][compressed_path] = buffer.getvalue()

        with DefaultDirectoryService(web_server, cache, config) as directory_service:
            # When
            directory_service.start()

            wait_for_condition(1, lambda: web_server.is_running())

            client = web_server._app.test_client()

            client.get('/dists/trixie/info.gz')

            # When
            response = client.get('/dists/trixie/info.gz')

            # Then
            self.assertEqual(200, response.status_code)
            self.assertEqual('gzip', response.headers['Content-Encoding'])
            self.assertEqual('attachment; filename="info.gz"', response.headers['Content-Disposition'])
            self.assertEqual(cache._read_cache['trixie'][compressed_path], response.data)

    def test_returns_404_when_accessing_non_existing_path(self):
        # Given
        web_server, cache, config = create_components()

        with DefaultDirectoryService(web_server, cache, config) as directory_service:
            # When
            directory_service.start()

            wait_for_condition(1, lambda: web_server.is_running())

            client = web_server._app.test_client()

            # When
            response = client.get('/trixie/invalid')

            # Then
            self.assertEqual(404, response.status_code)

    def test_returns_404_when_accessing_reserved_api_path(self):
        # Given
        web_server, cache, config = create_components()

        with DefaultDirectoryService(web_server, cache, config) as directory_service:
            # When
            directory_service.start()

            wait_for_condition(1, lambda: web_server.is_running())

            client = web_server._app.test_client()

            # When
            response = client.get('/api/health')

            # Then
            self.assertEqual(404, response.status_code)


def create_components():
    web_server = DefaultDirectoryServer(ServerConfig(['*:0']))
    cache = DefaultRepositoryCache({'bookworm', 'trixie'})
    cache.initialize()
    config = DirectoryConfig(REPOSITORY_DIR, '1.0.0', Path(f'{RESOURCE_ROOT}/templates/directory.j2'))
    return web_server, cache, config


if __name__ == '__main__':
    unittest.main()
