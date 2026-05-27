from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

APPLICATION_NAME = 'debian-package-repository'


def get_argument_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description='Effective Range Scarecrow Server',
        formatter_class=ArgumentDefaultsHelpFormatter
    )

    app_group = parser.add_argument_group('package-repository')
    app_group.add_argument(
        '-c',
        '--config',
        help='configuration file path',
        default=f'/etc/effective-range/{APPLICATION_NAME}/{APPLICATION_NAME}.conf'
    )

    logging_group = parser.add_argument_group('logging')
    logging_group.add_argument(
        '-f',
        '--log-file',
        help='log file path',
        default=f'/var/log/effective-range/{APPLICATION_NAME}/{APPLICATION_NAME}.log'
    )
    logging_group.add_argument(
        '-l',
        '--log-level',
        help='logging level',
        default='INFO'
    )

    server_group = parser.add_argument_group('server')
    server_group.add_argument(
        '--server-host',
        help='web server host to listen on',
        default='*'
    )
    server_group.add_argument(
        '--server-port',
        help='web server port to listen on',
        type=int,
        default=9000
    )
    server_group.add_argument(
        '--server-scheme',
        help='server URL scheme',
        default='http'
    )
    server_group.add_argument(
        '--server-prefix',
        help='server prefix',
        default=''
    )
    server_group.add_argument(
        '--server-threads',
        help='server thread count',
        type=int,
        default=32
    )
    server_group.add_argument(
        '--server-backlog',
        help='server socket backlog',
        type=int,
        default=1024
    )
    server_group.add_argument(
        '--server-connection-limit',
        help='maximum number of concurrent connections',
        type=int,
        default=1000
    )
    server_group.add_argument(
        '--server-channel-timeout',
        help='server channel timeout in seconds',
        type=int,
        default=60
    )

    repository_group = parser.add_argument_group('repository')
    repository_group.add_argument(
        '--distributions',
        help='supported distributions (comma separated)',
        default='bookworm, trixie'
    )
    repository_group.add_argument(
        '--components',
        help='repository components (comma separated)',
        default='main'
    )
    repository_group.add_argument(
        '--architectures',
        help='supported architectures (comma separated)',
        default='amd64, arm64, armhf'
    )
    repository_group.add_argument(
        '--repository-dir',
        help='repository root directory',
        default=f'/etc/{APPLICATION_NAME}'
    )
    repository_group.add_argument(
        '--deb-package-dir',
        help='directory containing .deb packages',
        default='/opt/debs'
    )
    repository_group.add_argument(
        '--repo-create-delay',
        help='delay before repository generation after package changes',
        type=float,
        default=10
    )
    repository_group.add_argument(
        '--directory-template',
        help='template directory path',
        default='templates/directory.j2'
    )

    release_group = parser.add_argument_group('release')
    release_group.add_argument(
        '--release-origin',
        help='Release file Origin value',
        default=APPLICATION_NAME
    )
    release_group.add_argument(
        '--release-label',
        help='Release file Label value',
        default=APPLICATION_NAME
    )
    release_group.add_argument(
        '--release-suite',
        help='Release file Suite value',
        default='stable'
    )
    release_group.add_argument(
        '--release-description',
        help='Release file Description value',
        default='A Debian package repository server'
    )
    release_group.add_argument(
        '--release-template',
        help='Release file Template value',
        default='templates/Release.j2'
    )

    signature_group = parser.add_argument_group('signature')
    signature_group.add_argument(
        '--private-key-id',
        help='private key id used for signing',
        default='C1AEE2EDBAEC37595801DDFAE15BC62117A4E0F3'
    )
    signature_group.add_argument(
        '--private-key-path',
        help='private key path',
        default='tests/keys/private-key.asc'
    )
    signature_group.add_argument(
        '--private-key-pass',
        help='private key passphrase',
        default='test1234'
    )
    signature_group.add_argument(
        '--public-key-path',
        help='public key path',
        default='tests/keys/public-key.asc'
    )
    signature_group.add_argument(
        '--public-key-name',
        help='public key filename in repository',
        default='repository.gpg.key'
    )

    return parser
