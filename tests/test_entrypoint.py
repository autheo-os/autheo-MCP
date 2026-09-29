"""Protect the installed console-script target against missing entry points."""
from autheo_mcp import server


def test_console_entrypoint_starts_stdio(monkeypatch):
    calls = []
    monkeypatch.setattr(server.mcp, "run", lambda **kwargs: calls.append(kwargs))
    server.main()
    assert calls == [{"transport": "stdio"}]
