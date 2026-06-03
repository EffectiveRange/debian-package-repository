from abc import ABC, abstractmethod
from pathlib import Path

from context_logger import get_logger
from debian.deb822 import Packages
from package_repository import RepositoryCache, MetadataCache


class MetadataLoader(ABC):

    @abstractmethod
    def load(self, distribution: str) -> None: ...


class PackageMetadataLoader(MetadataLoader):

    def __init__(self, repository_cache: RepositoryCache, metadata_cache: MetadataCache,
                 architectures: set[str]) -> None:
        self._repository_cache = repository_cache
        self._metadata_cache = metadata_cache
        self._architectures = architectures
        self.log = get_logger(type(self).__name__)

    def load(self, distribution: str) -> None:
        self.log.info('Loading metadata for distribution', distribution=distribution)

        for architecture in self._architectures:
            packages_path = Path(f'main/binary-{architecture}/Packages')
            packages_content = self._repository_cache.load(distribution, packages_path)

            if packages_content:
                self.log.info('Parsing metadata for architecture', distribution=distribution, architecture=architecture)
                packages = Packages.iter_paragraphs(packages_content)
                for package in packages:
                    self._metadata_cache.store(distribution, architecture, dict(package))

        self._metadata_cache.switch(distribution)
