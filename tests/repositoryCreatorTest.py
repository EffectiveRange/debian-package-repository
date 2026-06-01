import gzip
import os
import subprocess
import unittest
from unittest import TestCase
from unittest.mock import MagicMock, patch

from common_utility import delete_directory, render_template_file, create_directory
from context_logger import setup_logging
from package_repository import RepositoryConfig, DefaultRepositoryCreator, RepositoryCache, ReleaseInfo
from test_utility import compare_lines
from tests import (
    create_test_packages,
    TEST_RESOURCE_ROOT,
    REPOSITORY_DIR,
    RESOURCE_ROOT, PACKAGE_DIR, APPLICATION_NAME, RELEASE_TEMPLATE_PATH
)


class RepositoryCreatorTest(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging(APPLICATION_NAME, 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()
        delete_directory(PACKAGE_DIR)
        create_test_packages(PACKAGE_DIR, 'bookworm')
        create_test_packages(PACKAGE_DIR, 'trixie')
        create_directory(REPOSITORY_DIR)

    def test_initialize_when_repository_tree_is_missing(self):
        # Given
        delete_directory(REPOSITORY_DIR)

        cache, config, info = create_components()
        creator = DefaultRepositoryCreator(cache, config, info)

        # When
        creator.initialize()

        # Then
        self.assertTrue(os.path.isdir(REPOSITORY_DIR))
        self.assertTrue(os.path.islink(f'{REPOSITORY_DIR}/pool'))

    def test_initialize_when_package_dir_is_missing(self):
        # Given
        delete_directory(PACKAGE_DIR)

        cache, config, info = create_components()
        creator = DefaultRepositoryCreator(cache, config, info)

        # When
        creator.initialize()

        # Then
        self.assertTrue(os.path.isdir(PACKAGE_DIR))
        self.assertTrue(os.path.islink(f'{REPOSITORY_DIR}/pool'))

    def test_create_assert_packages_files_generated(self):
        # Given
        expected_packages = render_template_file(
            f'{TEST_RESOURCE_ROOT}/expected/Packages.template',
            {'distribution': 'trixie', 'component': 'main', 'architecture': 'amd64'},
        ).splitlines()

        cache, config, info = create_components()
        creator = DefaultRepositoryCreator(cache, config, info)
        creator.initialize()

        # When
        creator.create('trixie')

        # Then
        self.assertTrue(os.path.isdir(REPOSITORY_DIR))
        self.assertTrue(os.path.isfile(f'{REPOSITORY_DIR}/dists/trixie/main/binary-all/Packages'))
        self.assertTrue(os.path.isfile(f'{REPOSITORY_DIR}/dists/trixie/main/binary-all/Packages.gz'))
        self.assertTrue(os.path.isfile(f'{REPOSITORY_DIR}/dists/trixie/main/binary-amd64/Packages'))
        self.assertTrue(os.path.isfile(f'{REPOSITORY_DIR}/dists/trixie/main/binary-amd64/Packages.gz'))
        self.assertTrue(os.path.isfile(f'{REPOSITORY_DIR}/dists/trixie/main/binary-arm64/Packages'))
        self.assertTrue(os.path.isfile(f'{REPOSITORY_DIR}/dists/trixie/main/binary-arm64/Packages.gz'))

        packages_path = f'{REPOSITORY_DIR}/dists/trixie/main/binary-amd64/Packages'
        packages = open(packages_path, 'r').read().splitlines()

        exclusions = ['Size', 'MD5sum', 'SHA1', 'SHA256']
        all_matches = compare_lines(expected_packages, packages, exclusions)

        self.assertTrue(all_matches)

        with gzip.open(f'{REPOSITORY_DIR}/dists/trixie/main/binary-amd64/Packages.gz', 'rt') as gz_file:
            gz_packages = gz_file.read().splitlines()
            all_matches_gz = compare_lines(packages, gz_packages)
            self.assertTrue(all_matches_gz)

    def test_create_assert_release_file_generated(self):
        # Given
        expected_release = render_template_file(
            f'{RESOURCE_ROOT}/templates/Release.j2',
            {
                'origin': APPLICATION_NAME,
                'label': APPLICATION_NAME,
                'suite': 'stable',
                'version': '1.0.0',
                'description': 'Test repository',
                'codename': 'trixie',
                'architectures': 'all amd64 arm64',
                'components': 'main',
                'md5_checksums': 'Packages',
                'sha1_checksums': 'Packages',
                'sha256_checksums': 'Packages'
            },
        ).splitlines()

        cache, config, info = create_components()
        creator = DefaultRepositoryCreator(cache, config, info)
        creator.initialize()

        # When
        creator.create('trixie')

        # Then
        release_file_path = f'{REPOSITORY_DIR}/dists/trixie/Release'
        self.assertTrue(os.path.exists(release_file_path))

        release = open(release_file_path, 'r').read().splitlines()

        exclusions = ['Date', 'Packages']

        all_matches = compare_lines(expected_release, release, exclusions)
        self.assertTrue(all_matches)

    @patch('package_repository.repositoryCreator.subprocess.run')
    def test_create_when_scanpackages_returns_non_zero_raises_error(self, mock_run):
        # Given
        mock_run.return_value = subprocess.CompletedProcess(
            args=['dpkg-scanpackages'],
            returncode=1,
            stdout=b'',
            stderr=b'mocked error\n',
        )

        cache, config, info = create_components()
        creator = DefaultRepositoryCreator(cache, config, info)
        creator.initialize()

        # When / Then
        with self.assertRaises(RuntimeError):
            creator.create('trixie')

        self.assertTrue(mock_run.called)


def create_components():
    cache = MagicMock(spec=RepositoryCache)
    config = RepositoryConfig({'bookworm', 'trixie'}, {'main'}, {'amd64', 'arm64'},
                              REPOSITORY_DIR, PACKAGE_DIR)
    info = ReleaseInfo(RELEASE_TEMPLATE_PATH, APPLICATION_NAME, APPLICATION_NAME, 'stable', '1.0.0', 'Test repository')
    return cache, config, info


if __name__ == "__main__":
    unittest.main()
