# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

import os
import signal
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path
from threading import Event
from typing import Any

from arguments import APPLICATION_NAME, get_argument_parser
from common_utility import ConfigLoader
from context_logger import get_logger, setup_logging
from gnupg import GPG
from package_repository import (RepositoryService, DirectoryService, PublicGpgKey, PrivateGpgKey,
                                DefaultPackageWatcher, DefaultRepositoryCache, RepositoryConfig, ReleaseInfo,
                                DefaultRepositoryCreator, DefaultRepositorySigner, DefaultRepositoryService,
                                ServerConfig, DefaultDirectoryServer, DirectoryConfig, DefaultDirectoryService,
                                PackageMetadataCache, PackageMetadataLoader)
from watchdog.observers import Observer

log = get_logger('RepositoryServerApp')

DEFAULT_CONFIG_PATH = Path(f'/etc/effective-range/{APPLICATION_NAME}/{APPLICATION_NAME}.conf.default')


class RepositoryServer:

    def run(self) -> None:
        raise NotImplementedError()

    def shutdown(self) -> None:
        raise NotImplementedError()


class DefaultRepositoryServer(RepositoryServer):

    def __init__(self, repository_service: RepositoryService, directory_service: DirectoryService) -> None:
        self._repository_service = repository_service
        self._directory_service = directory_service
        self._shutdown_event = Event()
        self.log = get_logger(type(self).__name__)

    def __enter__(self) -> RepositoryServer:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.shutdown()

    def run(self) -> None:
        self.log.info('Starting service', service='repository-service')
        self._repository_service.start()

        self.log.info('Starting service', service='directory-service')
        self._directory_service.start()

        self._shutdown_event.wait()

    def shutdown(self) -> None:
        self._repository_service.stop()
        self._directory_service.stop()
        self._shutdown_event.set()


def main() -> None:
    setup_logging(APPLICATION_NAME)

    argument_parser = get_argument_parser()

    config = ConfigLoader(DEFAULT_CONFIG_PATH).load(argument_parser)

    setup_logging(APPLICATION_NAME, config.log_level, config.log_file, warn_on_overwrite=False)

    log.info(f'Started {APPLICATION_NAME}')

    app_version = _get_version(APPLICATION_NAME)
    distributions = {dist.strip() for dist in config.distributions.split(',')}
    components = {comp.strip() for comp in config.components.split(',')}
    architectures = {arch.strip() for arch in config.architectures.split(',')}
    repository_dir = _get_absolute_path(config.repository_dir)
    deb_package_dir = _get_absolute_path(config.deb_package_dir)
    release_template = _get_absolute_path(config.release_template)
    directory_template = _get_absolute_path(config.directory_template)

    public_key_path = _get_absolute_path(config.public_key_path)
    public_key = PublicGpgKey(config.private_key_id, public_key_path, config.public_key_name)
    private_key_path = _get_absolute_path(config.private_key_path)
    private_key = PrivateGpgKey(config.private_key_id, private_key_path, config.private_key_pass)

    file_observer = Observer()
    package_watcher = DefaultPackageWatcher(file_observer, deb_package_dir)
    repository_cache = DefaultRepositoryCache(distributions)
    repository_config = RepositoryConfig(distributions, components, architectures, repository_dir, deb_package_dir)
    release_info = ReleaseInfo(release_template, config.release_origin, config.release_label, config.release_suite,
                               app_version, config.release_description)

    repository_creator = DefaultRepositoryCreator(repository_cache, repository_config, release_info)
    repository_signer = DefaultRepositorySigner(repository_cache, GPG(), private_key, public_key, repository_dir)

    metadata_cache = PackageMetadataCache()
    metadata_loader = PackageMetadataLoader(repository_cache, metadata_cache, architectures)

    repository_service = DefaultRepositoryService(package_watcher, repository_creator, repository_signer,
                                                  repository_cache, metadata_loader, distributions,
                                                  config.repo_create_delay)

    server_config = ServerConfig([f'{config.server_host}:{config.server_port}'], config.server_scheme,
                                 config.server_prefix, config.server_threads, config.server_backlog,
                                 config.server_connection_limit, config.server_channel_timeout)
    directory_server = DefaultDirectoryServer(server_config)
    directory_config = DirectoryConfig(repository_dir, app_version, directory_template)
    directory_service = DefaultDirectoryService(directory_server, repository_cache, metadata_cache, directory_config)

    repository_server = DefaultRepositoryServer(repository_service, directory_service)

    def signal_handler(signum: int, frame: Any) -> None:
        log.info('Shutting down', signum=signum)
        repository_server.shutdown()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    repository_server.run()


def _get_resource_root() -> Path:
    return Path(os.path.dirname(__file__)).parent.absolute()


def _get_absolute_path(path: str) -> Path:
    if path.startswith('/'):
        return Path(path)
    else:
        return _get_resource_root() / path


def _get_version(application_name: str) -> str:
    try:
        return version(application_name)
    except PackageNotFoundError:
        return 'none'


if __name__ == '__main__':
    main()
