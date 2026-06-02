# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

from pathlib import Path

from context_logger import get_logger


class RepositoryCache:

    def initialize(self) -> None:
        raise NotImplementedError()

    def store(self, distribution: str, path: Path, content: bytes) -> None:
        raise NotImplementedError()

    def load(self, distribution: str, path: Path) -> bytes | None:
        raise NotImplementedError()

    def switch(self, distribution: str) -> None:
        raise NotImplementedError()


class DefaultRepositoryCache(RepositoryCache):

    def __init__(self, distributions: set[str]) -> None:
        self._distributions = distributions
        self._write_cache: dict[str, dict[Path, bytes]] = {}
        self._read_cache: dict[str, dict[Path, bytes]] = {}
        self.log = get_logger(type(self).__name__)

    def initialize(self) -> None:
        for distribution in self._distributions:
            self._write_cache[distribution] = {}
            self._read_cache[distribution] = {}

    def store(self, distribution: str, path: Path, content: bytes) -> None:
        if distribution in self._write_cache:
            self.log.debug('Storing content to cache', distribution=distribution, path=str(path))
            self._write_cache[distribution][path] = content
        else:
            self.log.warning('Attempted to store to unsupported cache', distribution=distribution, path=str(path))

    def load(self, distribution: str, path: Path) -> bytes | None:
        if distribution in self._read_cache:
            self.log.debug('Loading content from cache', distribution=distribution, path=str(path))
            return self._read_cache[distribution].get(path)
        else:
            self.log.warning('Attempted to load from unsupported cache', distribution=distribution, path=str(path))
            return None

    def switch(self, distribution: str) -> None:
        if distribution in self._read_cache:
            self.log.info('Switching cache for distribution', distribution=distribution)
            self._read_cache[distribution] = self._write_cache[distribution]
            self._write_cache[distribution] = {}
        else:
            self.log.warning('Attempted to switch unsupported cache', distribution=distribution)
