# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

import signal

from common_utility import IReusableTimer, ReusableTimer
from context_logger import get_logger
from package_repository import RepositoryCreator, RepositorySigner, RepositoryCache, PackageWatcher


class RepositoryService:

    def start(self) -> None:
        raise NotImplementedError()

    def stop(self) -> None:
        raise NotImplementedError()


class DefaultRepositoryService(RepositoryService):

    def __init__(self, watcher: PackageWatcher, creator: RepositoryCreator, signer: RepositorySigner,
                 cache: RepositoryCache, distributions: set[str], trigger_delay: float) -> None:
        self._watcher = watcher
        self._creator = creator
        self._signer = signer
        self._cache = cache
        self._distributions = distributions
        self._trigger_delay = trigger_delay
        self._timers: dict[str, IReusableTimer] = {}
        self.log = get_logger(type(self).__name__)

    def start(self) -> None:
        self.log.info('Initializing repository')

        self._cache.initialize()
        self._creator.initialize()
        self._signer.initialize()

        for distribution in self._distributions:
            self._update_repository(distribution)

        self._watcher.register(self._handle_event)
        self._watcher.start()

    def stop(self) -> None:
        self._watcher.deregister(self._handle_event)
        self._watcher.stop()

    def _handle_event(self, distribution: str) -> None:
        if distribution not in self._distributions:
            self.log.warning('Received event for unsupported distribution', distribution=distribution)
            return

        timer = self._get_timer(distribution)

        if timer.is_alive():
            self.log.info('Re-scheduling repository update', distribution=distribution, delay=self._trigger_delay)
            timer.restart()
        else:
            self.log.info('Scheduling repository update', distribution=distribution, delay=self._trigger_delay)
            timer.start(self._trigger_delay, self._update_repository, [distribution])

    def _get_timer(self, distribution: str) -> IReusableTimer:
        timer = self._timers.get(distribution)

        if not timer:
            timer = ReusableTimer()
            self._timers[distribution] = timer

        return timer

    def _update_repository(self, distribution: str) -> None:
        self.log.info('Updating repository', distribution=distribution)

        try:
            self._creator.create(distribution)
            self._signer.sign(distribution)
            self._cache.switch(distribution)
        except Exception as error:
            self.log.error('Failed to update repository', distribution=distribution, error=str(error))
            signal.raise_signal(signal.SIGINT)
