import os
import unittest
from collections import deque
from pathlib import Path
from unittest import TestCase

from common_utility import delete_directory
from context_logger import setup_logging
from gnupg import GPG
from package_repository import RepositoryConfig, DefaultRepositoryCreator, DefaultRepositorySigner, PrivateGpgKey, \
    PublicGpgKey, DefaultRepositoryCache, ReleaseInfo
from tests import create_test_packages, TEST_RESOURCE_ROOT, REPOSITORY_DIR, APPLICATION_NAME, \
    PACKAGE_DIR, RELEASE_TEMPLATE_PATH

PRIVATE_KEY_PATH = Path(f'{TEST_RESOURCE_ROOT}/keys/private-key.asc')
PUBLIC_KEY_PATH = Path(f'{TEST_RESOURCE_ROOT}/keys/public-key.asc')
PUBLIC_KEY_NAME = 'test.gpg.key'
KEY_ID = 'C1AEE2EDBAEC37595801DDFAE15BC62117A4E0F3'
PASSPHRASE = 'test1234'


class RepositorySignerIntegrationTest(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging(APPLICATION_NAME, 'DEBUG', warn_on_overwrite=False)
        delete_directory(PACKAGE_DIR)
        create_test_packages(PACKAGE_DIR, 'trixie')

    def setUp(self):
        print()

    def test_release_file_signed(self):
        # Given
        cache, config, info, gpg, private_key, public_key = create_components()
        creator = DefaultRepositoryCreator(cache, config, info)
        signer = DefaultRepositorySigner(cache, gpg, private_key, public_key, REPOSITORY_DIR)

        creator.initialize()
        signer.initialize()

        creator.create('trixie')

        # When
        signer.sign('trixie')

        # Then
        release_path = f'{REPOSITORY_DIR}/dists/trixie'
        release_file_path = f'{release_path}/Release'
        self.assertTrue(os.path.exists(release_file_path))

        with open(release_file_path) as release_file:
            last_line = deque(release_file, 1)[0]
            self.assertEqual(last_line, f'SignWith: {KEY_ID}')

        signed_release_file_path = f'{release_path}/InRelease'
        self.assertTrue(os.path.exists(signed_release_file_path))

        signature_file_path = f'{release_path}/Release.gpg'
        self.assertTrue(os.path.exists(signature_file_path))

        with (open(PUBLIC_KEY_PATH, 'rb') as public_key_file,
              open(f'{REPOSITORY_DIR}/{PUBLIC_KEY_NAME}', 'rb') as verification_key_file):
            self.assertEqual(public_key_file.read(), verification_key_file.read())

    def test_release_file_resigned(self):
        # Given
        cache, config, info, gpg, private_key, public_key = create_components()
        creator = DefaultRepositoryCreator(cache, config, info)
        signer = DefaultRepositorySigner(cache, gpg, private_key, public_key, REPOSITORY_DIR)

        creator.initialize()
        signer.initialize()

        creator.create('trixie')
        signer.sign('trixie')

        release_path = f'{REPOSITORY_DIR}/dists/trixie'
        release_file_path = f'{release_path}/Release'

        with open(release_file_path, 'a') as release_file:
            release_file.write('\nSignWith: ABCDEFGHIJKLMNOPQRSTUVWXYZ')

        # When
        signer.sign('trixie')

        # Then
        with open(release_file_path) as release_file:
            last_line = deque(release_file, 1)[0]
            self.assertEqual(last_line, f'SignWith: {KEY_ID}')


def create_components():
    distributions = {'bookworm', 'trixie'}
    cache = DefaultRepositoryCache(distributions)
    config = RepositoryConfig(distributions, {'main'}, {'amd64', 'arm64'}, REPOSITORY_DIR, PACKAGE_DIR)
    info = ReleaseInfo(RELEASE_TEMPLATE_PATH, APPLICATION_NAME, APPLICATION_NAME, 'stable', '1.0.0', 'Test repository')
    gpg = GPG()
    private_key = PrivateGpgKey(KEY_ID, PRIVATE_KEY_PATH, PASSPHRASE)
    public_key = PublicGpgKey(KEY_ID, PUBLIC_KEY_PATH, PUBLIC_KEY_NAME)

    return cache, config, info, gpg, private_key, public_key


if __name__ == "__main__":
    unittest.main()
