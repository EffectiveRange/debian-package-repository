from abc import ABC, abstractmethod

from context_logger import get_logger


class MetadataCache(ABC):

    @abstractmethod
    def load(self, distribution: str, architecture: str, package: str) -> dict[str, str]: ...

    @abstractmethod
    def store(self, distribution: str, architecture: str, metadata: dict[str, str]) -> None: ...

    @abstractmethod
    def switch(self, distribution: str) -> None: ...


class PackageMetadataCache(MetadataCache):

    def __init__(self):
        self._write_cache: dict[str, dict[str, dict[str, dict[str, str]]]] = {}
        self._read_cache: dict[str, dict[str, dict[str, dict[str, str]]]] = {}
        self.log = get_logger(type(self).__name__)

    def load(self, distribution: str, architecture: str, package: str) -> dict[str, str]:
        architectures = self._read_cache.get(distribution, {})
        packages = architectures.get(architecture, {})
        return packages.get(package, {})

    def store(self, distribution: str, architecture: str, metadata: dict[str, str]) -> None:
        if distribution not in self._write_cache:
            self._write_cache[distribution] = {}
        if architecture not in self._write_cache[distribution]:
            self._write_cache[distribution][architecture] = {}
        self._write_cache[distribution][architecture][metadata['Package']] = metadata

    def switch(self, distribution: str) -> None:
        if distribution in self._read_cache:
            self.log.info('Switching metadata cache for distribution', distribution=distribution)
            self._read_cache[distribution] = self._write_cache[distribution]
            self._write_cache[distribution] = {}
        else:
            self.log.warning('Attempted to switch unsupported metadata cache', distribution=distribution)
