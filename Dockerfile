FROM debian:trixie-slim

RUN apt update && apt upgrade -y
RUN apt install -y python3-venv python3-pip git gnupg

# Install debian-package-repository
COPY dist/*.whl /tmp/debian-package-repository/
RUN python3 -m venv --system-site-packages /opt/venv
RUN /opt/venv/bin/pip3 install /tmp/debian-package-repository/*.whl

# Start debian-package-repository
ENTRYPOINT ["/opt/venv/bin/python3", "/opt/venv/bin/debian-package-repository", "--private-key-path", "/etc/effective-range/debian-package-repository/keys/private-key.asc", "--public-key-path", "/etc/effective-range/debian-package-repository/keys/public-key.asc"]
