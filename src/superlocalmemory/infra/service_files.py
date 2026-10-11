"""Service definitions share the registry's pinned, no-follow atomic IO."""

from __future__ import annotations

import os
from pathlib import Path

from superlocalmemory.infra.mcp_registry_files import (
    RegistryFiles,
    _open_root,
    _owned,
    _windows_pin,
)


class ServiceFiles(RegistryFiles):
    def __init__(self, directory: Path, *, create: bool = False):
        super().__init__(directory.parent, create=create)
        self.path = directory

    def __enter__(self):
        try:
            if self.path.resolve() != self.path.absolute():
                raise OSError("Service definition directory is redirected")
            if os.name == "nt":
                if self.create:
                    self.path.mkdir(parents=True, exist_ok=True)
                self._pins.enter_context(_windows_pin(self.path))
            else:
                self.fd = _open_root(self.path, create=self.create)
                _owned(os.fstat(self.fd), directory=True)
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise
