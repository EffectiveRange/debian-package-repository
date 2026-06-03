import unittest
from unittest import TestCase

from context_logger import setup_logging
from flask import Response
from package_repository import ServerConfig, DefaultDirectoryServer
from test_utility import wait_for_condition
from tests import APPLICATION_NAME


class DirectoryServerTest(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging(APPLICATION_NAME, 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()

    def test_startup_and_shutdown(self):
        # Given
        config = ServerConfig(['*:0'])

        with DefaultDirectoryServer(config) as server:
            # When
            server.start()

            # Then
            wait_for_condition(1, lambda: server.is_running())

        wait_for_condition(1, lambda: not server.is_running())

    def test_returns_200(self):
        # Given
        config = ServerConfig(['*:0'])

        with DefaultDirectoryServer(config) as server:
            # When
            @server.get_app().route('/test', methods=['GET'])
            def get_test() -> Response:
                return Response(status=200, response='Test OK')

            server.start()

            wait_for_condition(1, lambda: server.is_running())

            client = server.get_app().test_client()

            # When
            response = client.get('/test')

            # Then
            self.assertEqual(200, response.status_code)
            self.assertEqual('Test OK', response.data.decode())


if __name__ == '__main__':
    unittest.main()
