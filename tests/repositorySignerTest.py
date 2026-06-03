import unittest
from pathlib import Path
from unittest import TestCase, mock
from unittest.mock import MagicMock

from common_utility import delete_directory, create_file, render_template_file
from context_logger import setup_logging
from gnupg import GPG, Sign, Verify, ImportResult
from package_repository import DefaultRepositorySigner, GpgException, PublicGpgKey, PrivateGpgKey, RepositoryCache
from tests import TEST_RESOURCE_ROOT, REPOSITORY_DIR, APPLICATION_NAME, RELEASE_TEMPLATE_PATH

RELEASE_DIR = f'{REPOSITORY_DIR}/dists/trixie'
PRIVATE_KEY_PATH = f'{TEST_RESOURCE_ROOT}/keys/private-key.asc'
PUBLIC_KEY_PATH = f'{TEST_RESOURCE_ROOT}/keys/public-key.asc'
PUBLIC_KEY_NAME = 'repository.gpg.key'
KEY_ID = 'C1AEE2EDBAEC37595801DDFAE15BC62117A4E0F3'
PASSPHRASE = 'test1234'


class RepositorySignerTest(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging(APPLICATION_NAME, 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()
        delete_directory(REPOSITORY_DIR)
        create_files()

    def test_initialize_when_key_already_present(self):
        # Given
        cache, gpg, private_key, public_key = create_components()
        gpg.list_keys.return_value = [{'fingerprint': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'}, {'fingerprint': KEY_ID}]
        signer = DefaultRepositorySigner(cache, gpg, private_key, public_key, REPOSITORY_DIR)

        # When
        signer.initialize()

        # Then
        gpg.import_keys_file.assert_not_called()
        with (open(PUBLIC_KEY_PATH, 'rb') as public_key_file,
              open(f'{REPOSITORY_DIR}/{PUBLIC_KEY_NAME}', 'rb') as verification_key_file):
            self.assertEqual(public_key_file.read(), verification_key_file.read())

    def test_initialize_when_key_is_imported(self):
        # Given
        cache, gpg, private_key, public_key = create_components()
        signer = DefaultRepositorySigner(cache, gpg, private_key, public_key, REPOSITORY_DIR)

        # When
        signer.initialize()

        # Then
        gpg.import_keys_file.assert_called_once_with(PRIVATE_KEY_PATH)
        with (open(PUBLIC_KEY_PATH, 'rb') as public_key_file,
              open(f'{REPOSITORY_DIR}/{PUBLIC_KEY_NAME}', 'rb') as verification_key_file):
            self.assertEqual(public_key_file.read(), verification_key_file.read())

    def test_initialize_when_fails_to_import_key(self):
        # Given
        cache, gpg, private_key, public_key = create_components(import_code=1)
        signer = DefaultRepositorySigner(cache, gpg, private_key, public_key, REPOSITORY_DIR)

        # When
        self.assertRaises(GpgException, signer.initialize)

        # Then
        gpg.import_keys_file.assert_called_once_with(PRIVATE_KEY_PATH)
        gpg.sign_file.assert_not_called()

    def test_sign(self):
        # Given
        cache, gpg, private_key, public_key = create_components()
        signer = DefaultRepositorySigner(cache, gpg, private_key, public_key, REPOSITORY_DIR)
        signer.initialize()

        # When
        signer.sign('trixie')

        # Then
        gpg.sign_file.assert_has_calls(
            [
                mock.call(
                    f'{RELEASE_DIR}/Release',
                    keyid=KEY_ID,
                    passphrase=PASSPHRASE,
                    detach=False,
                ),
                mock.call(
                    f'{RELEASE_DIR}/Release',
                    keyid=KEY_ID,
                    passphrase=PASSPHRASE,
                    detach=True,
                ),
            ]
        )
        gpg.verify_file.assert_called()

    def test_sign_when_fails_to_create_signature(self):
        # Given
        cache, gpg, private_key, public_key = create_components(sign_codes=[1, 0])
        signer = DefaultRepositorySigner(cache, gpg, private_key, public_key, REPOSITORY_DIR)
        signer.initialize()

        # When
        self.assertRaises(GpgException, signer.sign, 'trixie')

        # Then
        gpg.sign_file.assert_called_once()
        gpg.verify_file.assert_not_called()

    def test_sign_when_fails_to_verify_signature(self):
        # Given
        cache, gpg, private_key, public_key = create_components(verify_codes=[1, 0])
        signer = DefaultRepositorySigner(cache, gpg, private_key, public_key, REPOSITORY_DIR)
        signer.initialize()

        # When
        self.assertRaises(GpgException, signer.sign, 'trixie')

        # Then
        gpg.sign_file.assert_called_once()
        gpg.verify_file.assert_called_once()

    def test_sign_when_fails_to_create_detached_signature(self):
        # Given
        cache, gpg, private_key, public_key = create_components(sign_codes=[0, 1])
        signer = DefaultRepositorySigner(cache, gpg, private_key, public_key, REPOSITORY_DIR)
        signer.initialize()

        # When
        self.assertRaises(GpgException, signer.sign, 'trixie')

        # Then
        gpg.sign_file.assert_called()
        gpg.verify_file.assert_called_once()

    def test_sign_when_failed_to_verify_detached_signature(self):
        # Given
        cache, gpg, private_key, public_key = create_components(verify_codes=[0, 1])
        signer = DefaultRepositorySigner(cache, gpg, private_key, public_key, REPOSITORY_DIR)
        signer.initialize()

        # When
        self.assertRaises(GpgException, signer.sign, 'trixie')

        # Then
        gpg.sign_file.assert_called()
        gpg.verify_file.assert_called()


def create_components(import_code=0, sign_codes=None, verify_codes=None):
    cache = MagicMock(spec=RepositoryCache)

    gpg = MagicMock(spec=GPG)
    gpg.list_keys.return_value = [{'fingerprint': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'}]

    import_result = ImportResult(gpg)
    import_result.returncode = import_code
    import_result.status = 'imported'
    gpg.import_keys_file.return_value = import_result

    if sign_codes is None:
        sign_codes = [0, 0]
    sign_result1 = Sign(gpg)
    sign_result1.returncode = sign_codes[0]
    sign_result1.status = 'signed'
    sign_result1.data = b'Signed data 1'
    sign_result2 = Sign(gpg)
    sign_result2.returncode = sign_codes[1]
    sign_result2.status = 'signed'
    sign_result2.data = b'Signed data 2'
    gpg.sign_file.side_effect = [sign_result1, sign_result2]

    if verify_codes is None:
        verify_codes = [0, 0]
    verify_result1 = Verify(gpg)
    verify_result1.returncode = verify_codes[0]
    verify_result1.status = 'verified'
    verify_result2 = Verify(gpg)
    verify_result2.returncode = verify_codes[1]
    verify_result2.status = 'verified'
    gpg.verify_file.side_effect = [verify_result1, verify_result2]

    private_key = PrivateGpgKey(KEY_ID, Path(PRIVATE_KEY_PATH), PASSPHRASE)
    public_key = PublicGpgKey(KEY_ID, Path(PUBLIC_KEY_PATH), PUBLIC_KEY_NAME)

    return cache, gpg, private_key, public_key


def create_files():
    release = render_template_file(
        RELEASE_TEMPLATE_PATH,
        {'origin': APPLICATION_NAME, 'label': APPLICATION_NAME, 'version': '1.1.3', 'architectures': 'all amd64'},
    )

    create_file(f'{REPOSITORY_DIR}/dists/trixie/Release', release)
    create_file(f'{REPOSITORY_DIR}/dists/trixie/InRelease', '')
    create_file(f'{REPOSITORY_DIR}/dists/trixie/Release.gpg', '')


if __name__ == "__main__":
    unittest.main()
