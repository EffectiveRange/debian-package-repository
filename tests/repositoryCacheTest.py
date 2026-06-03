import unittest
from pathlib import Path
from unittest import TestCase

from context_logger import setup_logging
from package_repository import DefaultRepositoryCache
from tests import APPLICATION_NAME


class DefaultRepositoryCacheTest(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging(APPLICATION_NAME, 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()

    def test_initialize(self):
        # Given
        cache = DefaultRepositoryCache({'bookworm', 'trixie'})

        # When
        cache.initialize()

        # Then
        self.assertIsNotNone(cache._write_cache.get('trixie'))
        self.assertIsNotNone(cache._write_cache.get('bookworm'))
        self.assertIsNotNone(cache._read_cache.get('trixie'))
        self.assertIsNotNone(cache._read_cache.get('bookworm'))

    def test_store(self):
        # Given
        cache = DefaultRepositoryCache({'bookworm', 'trixie'})
        cache.initialize()

        # When
        cache.store('trixie', Path('test.txt'), b'Test content')

        # Then
        self.assertEqual(b'Test content', cache._write_cache.get('trixie').get(Path('test.txt')))

    def test_store_when_distribution_is_invalid(self):
        # Given
        cache = DefaultRepositoryCache({'bookworm', 'trixie'})
        cache.initialize()

        # When
        cache.store('invalid', Path('test.txt'), b'Test content')

        # Then
        self.assertIsNone(cache._write_cache.get('trixie').get(Path('test.txt')))

    def test_load(self):
        # Given
        cache = DefaultRepositoryCache({'bookworm', 'trixie'})
        cache.initialize()
        cache._read_cache['trixie'][Path('test.txt')] = b'Test content'

        # When
        content = cache.load('trixie', Path('test.txt'))

        # Then
        self.assertEqual(b'Test content', content)

    def test_load_when_distribution_is_invalid(self):
        # Given
        cache = DefaultRepositoryCache({'bookworm', 'trixie'})
        cache.initialize()

        # When
        content = cache.load('invalid', Path('test.txt'))

        # Then
        self.assertIsNone(content)

    def test_switch(self):
        # Given
        cache = DefaultRepositoryCache({'bookworm', 'trixie'})
        cache.initialize()
        cache._write_cache['trixie'][Path('test.txt')] = b'Test content'

        # When
        cache.switch('trixie')

        # Then
        self.assertEqual(b'Test content', cache._read_cache.get('trixie').get(Path('test.txt')))
        self.assertIsNone(cache._write_cache.get('trixie').get(Path('test.txt')))

    def test_switch_when_distribution_is_invalid(self):
        # Given
        cache = DefaultRepositoryCache({'bookworm', 'trixie'})
        cache.initialize()
        cache._write_cache['trixie'][Path('test.txt')] = b'Test content'

        # When
        cache.switch('invalid')

        # Then
        self.assertIsNone(cache._read_cache.get('trixie').get(Path('test.txt')))
        self.assertEqual(b'Test content', cache._write_cache.get('trixie').get(Path('test.txt')))


if __name__ == "__main__":
    unittest.main()
