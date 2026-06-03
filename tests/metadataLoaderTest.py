import unittest
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, call

from package_repository import PackageMetadataLoader, RepositoryCache, MetadataCache


class MetadataLoaderTest(TestCase):

    def test_load_parses_and_stores_package_metadata(self):
        # Given
        repository_cache = MagicMock(spec=RepositoryCache)
        metadata_cache = MagicMock(spec=MetadataCache)
        architectures = {'amd64', 'arm64'}
        loader = PackageMetadataLoader(repository_cache, metadata_cache, architectures)

        amd64_content = b'Package: hello-world\nVersion: 1.0\n\n'

        def load_side_effect(distribution, packages_path):
            if packages_path == Path('main/binary-amd64/Packages'):
                return amd64_content
            return None

        repository_cache.load.side_effect = load_side_effect
        # When
        loader.load('trixie')

        # Then
        repository_cache.load.assert_has_calls([
            call('trixie', Path('main/binary-amd64/Packages')),
            call('trixie', Path('main/binary-arm64/Packages')),
        ], any_order=True)
        metadata_cache.store.assert_called_once_with(
            'trixie',
            'amd64',
            {'Package': 'hello-world', 'Version': '1.0'},
        )
        metadata_cache.switch.assert_called_once()

    def test_load_when_no_packages_content_does_not_parse_or_store(self):
        # Given
        repository_cache = MagicMock(spec=RepositoryCache)
        metadata_cache = MagicMock(spec=MetadataCache)
        architectures = {'amd64'}
        loader = PackageMetadataLoader(repository_cache, metadata_cache, architectures)
        repository_cache.load.return_value = None

        # When
        loader.load('trixie')

        # Then
        repository_cache.load.assert_called_once_with('trixie', Path('main/binary-amd64/Packages'))
        metadata_cache.store.assert_not_called()


if __name__ == '__main__':
    unittest.main()
