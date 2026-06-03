# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

import mimetypes
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

from context_logger import get_logger
from flask import send_from_directory, abort, request, Response, render_template, jsonify
from package_repository import RepositoryCache, DirectoryServer, MetadataCache


@dataclass
class DirectoryConfig:
    root_dir: Path
    version: str
    html_template: Path


class DirectoryService:

    def start(self) -> None:
        raise NotImplementedError()

    def stop(self) -> None:
        raise NotImplementedError()


class DefaultDirectoryService(DirectoryService):

    def __init__(self, web_server: DirectoryServer, repository_cache: RepositoryCache, metadata_cache: MetadataCache,
                 config: DirectoryConfig) -> None:
        self._web_server = web_server
        self._repository_cache = repository_cache
        self._metadata_cache = metadata_cache
        self._config = config
        self.log = get_logger(type(self).__name__)

        self._register_routes()

    def __enter__(self) -> 'DefaultDirectoryService':
        return self

    def __exit__(self, exc_type: type, exc_val: Exception, exc_tb: Any) -> None:
        self.stop()

    def start(self) -> None:
        self._web_server.start()

    def stop(self) -> None:
        self._web_server.stop()

    def _register_routes(self) -> None:
        app = self._web_server.get_app()

        app.template_folder = str(self._config.html_template.parent)

        @app.route('/', defaults={'path': ''}, methods=['GET'])
        @app.route('/<path:path>', methods=['GET'])
        def serve_file_or_directory(path: str) -> Response:
            relative_path = Path(path)

            # Reserve /api for explicit API routes instead of static file serving.
            if path.startswith('api/'):
                self.log.debug('Reserved API path requested from file endpoint', path=path)
                return abort(404)

            full_path = self._config.root_dir / relative_path

            if full_path.is_dir():
                self.log.debug('Listing directory', path=str(full_path))
                return self._list_directory(relative_path, full_path)
            elif relative_path.parts[0] == 'dists':
                distribution = relative_path.parts[1]
                cache_path = Path(*relative_path.parts[2:])
                self.log.debug('Serving cached file', distribution=distribution, path=str(cache_path))
                return self._load_from_cache(distribution, cache_path)
            elif full_path.is_file():
                self.log.debug('Serving file', path=str(full_path))
                return send_from_directory(self._config.root_dir, path, as_attachment=False, mimetype='text/plain')
            else:
                self.log.debug('File or directory not found', path=str(full_path))
                return abort(404)

        @app.route('/api/<distribution>/<architecture>/<package>', methods=['GET'])
        def serve_package_metadata(distribution: str, architecture: str, package: str) -> Response:
            return self._load_metadata(distribution, architecture, package)

        @app.route('/api/<distribution>/<architecture>/<package>/<key>', methods=['GET'])
        def serve_package_metadata2(distribution: str, architecture: str, package: str, key: str) -> Response:
            return self._load_metadata(distribution, architecture, package, key)

    def _load_metadata(self, distribution: str, architecture: str, package: str, key: str | None = None) -> Response:
        self.log.debug('API request for package metadata',
                       distribution=distribution, architecture=architecture, package=package, key=key)

        metadata = self._metadata_cache.load(distribution, architecture, package)

        if metadata is None:
            self.log.debug('Package metadata not found in cache',
                           distribution=distribution, architecture=architecture, package=package, key=key)
            return abort(404)

        if key is None:
            return jsonify(metadata)

        value = metadata.get(key)

        if value is None:
            return Response(f"Key '{key}' not found in package '{package}' metadata")

        return Response(value)

    def _load_from_cache(self, distribution: str, full_path: Path) -> Response:
        content = self._repository_cache.load(distribution, full_path)

        if not content:
            self.log.error('Failed to load file from cache', distribution=distribution, path=str(full_path))
            return abort(404)

        mimetype, encoding = mimetypes.guess_type(full_path)

        headers = {}

        if encoding:
            headers['Content-Encoding'] = encoding
            headers['Content-Disposition'] = f'attachment; filename="{full_path.name}"'
        elif not mimetype:
            mimetype = 'text/plain'

        return Response(content, mimetype=mimetype, headers=headers)

    def _list_directory(self, path: Path, full_path: Path) -> Response:
        sort_by = request.args.get('sort', 'name')
        reverse = request.args.get('desc', '0') == '1'

        entries = []

        for item in sorted(os.listdir(full_path)):
            entries.append(self._create_child_entry(full_path, path, item, sort_by))

        entries.sort(
            key=lambda x: x['sort_key'] if isinstance(x['sort_key'], tuple) else (str(x['sort_key'])), reverse=reverse
        )

        if path:
            entries.insert(0, self._create_parent_entry(path))

        breadcrumbs = self._create_breadcrumbs(path)

        return Response(render_template(self._config.html_template.name, items=entries, path=path,
                                        breadcrumbs=breadcrumbs, sort_by=sort_by, reverse=reverse,
                                        version=self._config.version))

    def _create_parent_entry(self, path: Path) -> dict[str, Any]:
        parent_path = '/' + quote(str(path.parent)) + '/'
        return {
            'name': '../',
            'href': parent_path,
            'is_parent': True,
            'date': '',
            'size': '',
            'sort_key': (True, '..', '', 0)
        }

    def _create_child_entry(self, full_path: Path, path: Path, item: str, sort_by: str) -> dict[str, Any]:
        item_path = os.path.join(full_path, item)
        is_dir = os.path.isdir(item_path)
        stat = os.stat(item_path)
        size = stat.st_size
        date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_mtime))
        href = '/' + quote(os.path.join(path, item).replace(os.sep, '/'))
        if is_dir:
            href += '/'
        sort_key = (not is_dir, item.lower(), date, 0 if is_dir else size)
        return {
            'name': item + ('/' if is_dir else ''),
            'href': href,
            'is_parent': False,
            'is_dir': is_dir,
            'date': date,
            'size': '-' if is_dir else f'{size:,} bytes',
            'sort_key': sort_key
        }

    def _create_breadcrumbs(self, path: Path) -> list[dict[str, str]]:
        breadcrumbs = []
        path_accum = ''
        for part in str(path).split('/') if path else []:
            path_accum = os.path.join(path_accum, part)
            breadcrumbs.append({
                'name': part,
                'href': '/' + quote(path_accum.replace(os.sep, '/')) + '/'
            })
        return breadcrumbs
