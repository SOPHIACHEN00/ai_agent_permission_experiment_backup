"""No-API test boundary and metadata-only dependency guard (never reads .env)."""
from pathlib import Path
import socket


def dependency_inventory(parent):
    inventory = {}
    for folder in ('s-qstn', 'mock_tools'):
        root = Path(parent) / folder
        inventory[folder] = tuple(sorted((str(p.relative_to(root)), p.stat().st_size, p.stat().st_mtime_ns)
                                         for p in root.rglob('*') if p.is_file()))
    return inventory


class NetworkBlock:
    def __init__(self): self.attempts, self._original = 0, []

    def __enter__(self):
        def denied(*args, **kwargs):
            self.attempts += 1
            raise RuntimeError('network disabled in no-API functional run')
        for owner, name in ((socket, 'getaddrinfo'), (socket, 'create_connection'), (socket.socket, 'connect'),
                            (socket.socket, 'connect_ex'), (socket.socket, 'sendto')):
            self._original.append((owner, name, getattr(owner, name)))
            setattr(owner, name, denied)
        return self

    def __exit__(self, *args):
        for owner, name, value in reversed(self._original): setattr(owner, name, value)
