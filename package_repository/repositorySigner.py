# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

import shutil
from abc import ABC, abstractmethod
from pathlib import Path

from context_logger import get_logger
from gnupg import GPG, ImportResult, Sign, Verify
from package_repository import RepositoryCache


class GpgException(Exception):

    def __init__(self, message: str, result: ImportResult | Sign | Verify) -> None:
        super().__init__(message)
        self.operation = type(result).__name__.replace('Result', '')
        self.code = result.returncode
        self.status = result.status if hasattr(result, 'status') else None
        self.error = result.stderr if hasattr(result, 'stderr') else None


class GpgKey(object):

    def __init__(self, key_id: str, key_path: Path) -> None:
        self.id = key_id
        self.path = key_path


class PrivateGpgKey(GpgKey):

    def __init__(self, key_id: str, key_path: Path, passphrase: str) -> None:
        super().__init__(key_id, key_path)
        self.passphrase = passphrase


class PublicGpgKey(GpgKey):

    def __init__(self, key_id: str, key_path: Path, public_name: str) -> None:
        super().__init__(key_id, key_path)
        self.public_name = public_name


class RepositorySigner(ABC):

    @abstractmethod
    def initialize(self) -> None: ...

    @abstractmethod
    def sign(self, distribution: str) -> None: ...


class DefaultRepositorySigner(RepositorySigner):

    def __init__(self, cache: RepositoryCache, gpg: GPG, private_key: PrivateGpgKey, public_key: PublicGpgKey,
                 repository_dir: Path) -> None:
        self._cache = cache
        self._gpg = gpg
        self._private_key = private_key
        self._public_key = public_key
        self._repository_dir = repository_dir
        self.log = get_logger(type(self).__name__)

    def initialize(self) -> None:
        self._import_private_key()
        self._add_public_key()

    def sign(self, distribution: str) -> None:
        dist_path = self._repository_dir / 'dists' / distribution
        release_path = dist_path / 'Release'

        self._update_release_file(distribution, release_path)

        self._clearsign_release_file(distribution, release_path)

        self._create_detached_signature(distribution, release_path)

    def _add_public_key(self) -> None:
        target_path = self._repository_dir / self._public_key.public_name
        shutil.copyfile(self._public_key.path, target_path)
        self.log.info('Added public key file', file=str(target_path))

    def _import_private_key(self) -> None:
        key_id = self._private_key.id
        key_path = self._private_key.path

        if self._is_key_available():
            self.log.debug('Private key already present', key_id=key_id)
        else:
            result: ImportResult = self._gpg.import_keys_file(str(key_path))

            if result.returncode != 0:
                self.log.error('Failed to import private key', file=str(key_path), key_id=key_id)
                raise GpgException('Failed to import private key', result)
            else:
                self.log.info('Imported private key', key_id=key_id)

    def _is_key_available(self) -> bool:
        for key in self._gpg.list_keys():
            if key['fingerprint'] == self._private_key.id:
                return True

        return False

    def _update_release_file(self, distribution: str, release_path: Path) -> None:
        sign_with = 'SignWith'
        signed_with = f'{sign_with}: {self._private_key.id}'

        with open(release_path, 'r') as release_file:
            release_lines = release_file.readlines()

        if sign_with in release_lines[-1]:
            release_lines[-1] = signed_with
        else:
            release_lines.append(f'\n{signed_with}')

        release_content = ''.join(release_lines).encode()

        self._create_file(distribution, release_path, release_content)

    def _clearsign_release_file(self, distribution: str, release_path: Path) -> None:
        in_release_path = release_path.parent / 'InRelease'

        self._create_signature(distribution, release_path, in_release_path, detach=False)

        self.log.info('Created signed Release file', file=str(in_release_path))

    def _create_detached_signature(self, distribution: str, release_path: Path) -> None:
        signature_path = Path(f'{release_path}.gpg')

        self._create_signature(distribution, release_path, signature_path, detach=True)

        self.log.info('Created signature file', file=str(signature_path))

    def _create_signature(self, distribution: str, release_path: Path, signature_path: Path, detach: bool) -> None:
        result: Sign = self._gpg.sign_file(
            str(release_path),
            keyid=self._private_key.id,
            passphrase=self._private_key.passphrase,
            detach=detach
        )

        if result.returncode != 0 or result.on_data_failure:
            self.log.error('Failed to create signature', file=str(release_path), signature=str(signature_path),
                           return_code=result.returncode, data_failure=result.on_data_failure)
            raise GpgException('Failed to create signature', result)
        else:
            self._create_file(distribution, signature_path, result.data)
            self.log.debug('Created signature', file=str(signature_path))

        self._verify_signature(release_path, signature_path, detached=detach)

    def _create_file(self, distribution: str, file_path: Path, content: bytes) -> None:
        self._cache.store(distribution, file_path, content)

        with open(file_path, 'wb') as file:
            file.write(content)

    def _verify_signature(self, release_path: Path, signature_path: Path, detached: bool) -> None:
        with open(signature_path, 'rb') as signature_file:
            result: Verify = self._gpg.verify_file(signature_file, str(release_path) if detached else None)

        if result.returncode != 0 or result.on_data_failure:
            self.log.error('Failed to verify signature', file=str(release_path), signature=str(signature_path),
                           return_code=result.returncode, data_failure=result.on_data_failure)
            raise GpgException('Failed to verify signature', result)
        else:
            self.log.debug('Verified signature', file=str(signature_path))
