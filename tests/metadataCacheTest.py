import unittest
from unittest import TestCase

from context_logger import setup_logging

from package_repository import PackageMetadataCache
from tests import APPLICATION_NAME


class PackageMetadataCacheTest(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging(APPLICATION_NAME, 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()

    def test_store(self):
        # Given
        cache = PackageMetadataCache()
        metadata = {'Package': 'hello-world', 'Version': '1.0.0'}

        # When
        cache.store('trixie', 'amd64', metadata)

        # Then
        self.assertEqual(metadata, cache._write_cache['trixie']['amd64']['hello-world'])

    def test_load(self):
        # Given
        cache = PackageMetadataCache()
        metadata = {'Package': 'hello-world', 'Version': '1.0.0'}
        cache._read_cache['trixie'] = {'amd64': {'hello-world': metadata}}

        # When
        loaded = cache.load('trixie', 'amd64', 'hello-world')

        # Then
        self.assertEqual(metadata, loaded)

    def test_load_when_distribution_is_invalid(self):
        # Given
        cache = PackageMetadataCache()

        # When
        loaded = cache.load('invalid', 'amd64', 'hello-world')

        # Then
        self.assertEqual({}, loaded)

    def test_load_when_architecture_is_invalid(self):
        # Given
        cache = PackageMetadataCache()
        metadata = {'Package': 'hello-world', 'Version': '1.0.0'}
        cache._read_cache['trixie'] = {'amd64': {'hello-world': metadata}}

        # When
        loaded = cache.load('trixie', 'arm64', 'hello-world')

        # Then
        self.assertEqual({}, loaded)

    def test_switch(self):
        # Given
        cache = PackageMetadataCache()
        metadata = {'Package': 'hello-world', 'Version': '1.0.0'}
        cache._read_cache['trixie'] = {}
        cache._write_cache['trixie'] = {'amd64': {'hello-world': metadata}}

        # When
        cache.switch('trixie')

        # Then
        self.assertEqual(metadata, cache._read_cache['trixie']['amd64']['hello-world'])
        self.assertEqual({}, cache._write_cache['trixie'])

    def test_switch_when_distribution_is_invalid(self):
        # Given
        cache = PackageMetadataCache()
        metadata = {'Package': 'hello-world', 'Version': '1.0.0'}
        cache._read_cache['trixie'] = {}
        cache._write_cache['trixie'] = {'amd64': {'hello-world': metadata}}

        # When
        cache.switch('invalid')

        # Then
        self.assertEqual({}, cache._read_cache['trixie'])
        self.assertEqual(metadata, cache._write_cache['trixie']['amd64']['hello-world'])


if __name__ == '__main__':
    unittest.main()

