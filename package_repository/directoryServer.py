# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

from dataclasses import dataclass
from threading import Thread, Lock
from typing import Any

from context_logger import get_logger
from flask import Flask
from waitress.server import create_server


@dataclass
class ServerConfig:
    listen: list[str]
    url_scheme: str = 'http'
    url_prefix: str = ''
    threads: int = 32
    backlog: int = 1024
    connection_limit: int = 1000
    channel_timeout: int = 60


class DirectoryServer:

    def start(self) -> None:
        raise NotImplementedError()

    def stop(self) -> None:
        raise NotImplementedError()

    def is_running(self) -> bool:
        raise NotImplementedError()

    def get_app(self) -> Flask:
        raise NotImplementedError()


class DefaultDirectoryServer(DirectoryServer):

    def __init__(self, config: ServerConfig) -> None:
        self._config = config
        self._app = Flask(__name__)
        self._server = create_server(self._app,
                                     listen=' '.join(config.listen),
                                     url_scheme=config.url_scheme,
                                     url_prefix=config.url_prefix,
                                     threads=config.threads,
                                     backlog=config.backlog,
                                     connection_limit=config.connection_limit,
                                     channel_timeout=config.channel_timeout)
        self._thread: Thread | None = None
        self._lock = Lock()
        self.log = get_logger(type(self).__name__)

    def __enter__(self) -> DirectoryServer:
        return self

    def __exit__(self, exc_type: type, exc_val: Exception, exc_tb: Any) -> None:
        self.stop()

    def start(self) -> None:
        if self._thread:
            self.stop()

        with self._lock:
            self._thread = Thread(target=self._start_server)
            self._thread.start()

    def stop(self) -> None:
        with self._lock:
            self.log.info('Stopping server')
            self._server.close()
            if self._thread:
                self._thread.join(1)
                self._thread = None

    def is_running(self) -> bool:
        with self._lock:
            return self._thread is not None and self._thread.is_alive()

    def get_app(self) -> Flask:
        return self._app

    def _start_server(self) -> None:
        try:
            self.log.info('Starting server', config=self._config)
            self._server.run()
        except Exception as error:
            self.log.info('Shutdown', reason=error)
