from __future__ import annotations

from unittest import mock
from typing import Any

import pytest


@pytest.fixture
def mocker():
    patchers: list[Any] = []

    class PatchProxy:
        def object(self, target, attribute, *args, **kwargs):
            patcher = mock.patch.object(target, attribute, *args, **kwargs)
            patched = patcher.start()
            patchers.append(patcher)
            return patched

    class Mocker:
        Mock = mock.Mock
        call = mock.call
        patch = PatchProxy()

    try:
        yield Mocker()
    finally:
        for patcher in reversed(patchers):
            patcher.stop()
