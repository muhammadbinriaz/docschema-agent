"""Windows-safe entry when Application Control blocks native DLLs."""
from __future__ import annotations

import json
import sys
import types
import uuid


def _stub_orjson() -> None:
    try:
        import orjson

        orjson.dumps({"ok": True})
        return
    except Exception:
        sys.modules.pop("orjson", None)
        sys.modules.pop("orjson.orjson", None)

    stub = types.ModuleType("orjson")
    stub.OPT_NON_STR_KEYS = 1
    stub.OPT_SERIALIZE_NUMPY = 2
    stub.dumps = lambda obj, option=0: json.dumps(obj, default=str).encode("utf-8")
    stub.loads = lambda data: json.loads(
        data.decode("utf-8") if isinstance(data, (bytes, bytearray)) else data
    )
    sys.modules["orjson"] = stub


def _stub_xxhash() -> None:
    try:
        import xxhash

        xxhash.xxh64(b"ok").hexdigest()
        return
    except Exception:
        sys.modules.pop("xxhash", None)
        sys.modules.pop("xxhash._xxhash", None)

    class _H:
        def __init__(self, data: bytes = b""):
            self._d = data

        def update(self, data: bytes) -> None:
            self._d += data

        def hexdigest(self) -> str:
            return uuid.uuid5(uuid.NAMESPACE_OID, self._d.hex()).hex

        def digest(self) -> bytes:
            return bytes.fromhex(self.hexdigest())

        def intdigest(self) -> int:
            return int(self.hexdigest()[:16], 16)

    stub = types.ModuleType("xxhash")
    stub.xxh32 = lambda data=b"", seed=0: _H(data if isinstance(data, bytes) else str(data).encode())
    stub.xxh64 = stub.xxh32
    stub.xxh3_64 = stub.xxh32
    stub.xxh3_128 = stub.xxh32

    def _hex(data=b"", seed=0):
        return stub.xxh64(data).hexdigest()

    stub.xxh3_64_hexdigest = _hex
    stub.xxh3_128_hexdigest = _hex
    stub.xxh64_hexdigest = _hex
    sys.modules["xxhash"] = stub


_stub_orjson()
_stub_xxhash()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8001, reload=False)
