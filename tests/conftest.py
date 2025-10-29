from __future__ import annotations

import sys
from types import SimpleNamespace


class _DummySession:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs

    def client(self, *args, **kwargs):  # pragma: no cover - fallback for unexpected calls
        raise RuntimeError("S3 client not stubbed in tests")


def _install_stub(module_name: str, module):
    if module_name not in sys.modules:
        sys.modules[module_name] = module


_install_stub("dotenv", SimpleNamespace(load_dotenv=lambda: None))
_install_stub("boto3", SimpleNamespace(session=SimpleNamespace(Session=_DummySession)))
_install_stub("flask_cors", SimpleNamespace(CORS=lambda *args, **kwargs: None))
