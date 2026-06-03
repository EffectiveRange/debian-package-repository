from abc import ABC, abstractmethod

from context_logger import get_logger
from debian.deb822 import Deb822Dict
from debian.debian_support import Version


class MetadataCache(ABC):

    @abstractmethod
    def load(self, distribution: str, architecture: str, package: str) -> Deb822Dict | None: ...

    @abstractmethod
    def store(self, distribution: str, architecture: str, metadata: Deb822Dict) -> None: ...

    @abstractmethod
    def switch(self, distribution: str) -> None: ...


class PackageMetadataCache(MetadataCache):

    def __init__(self) -> None:
        self._write_cache: dict[str, dict[str, dict[str, Deb822Dict]]] = {}
        self._read_cache: dict[str, dict[str, dict[str, Deb822Dict]]] = {}
        self.log = get_logger(type(self).__name__)

    def load(self, distribution: str, architecture: str, package: str) -> Deb822Dict | None:
        architectures = self._read_cache.get(distribution, {})
        packages = architectures.get(architecture, {})
        return packages.get(package)

    def store(self, distribution: str, architecture: str, metadata: Deb822Dict) -> None:
        if distribution not in self._write_cache:
            self._write_cache[distribution] = {}
        if architecture not in self._write_cache[distribution]:
            self._write_cache[distribution][architecture] = {}

        package = metadata['Package']

        if cached := self._write_cache[distribution][architecture].get(package):
            if Version(metadata['Version']) < Version(cached['Version']):
                return

        self._write_cache[distribution][architecture][package] = metadata

    def switch(self, distribution: str) -> None:
        if distribution in self._write_cache:
            self.log.info('Switching metadata cache for distribution', distribution=distribution)
            self._read_cache[distribution] = self._write_cache[distribution]
            self._write_cache[distribution] = {}
        else:
            self.log.warning('Attempted to switch unsupported metadata cache', distribution=distribution)
