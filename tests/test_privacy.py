from __future__ import annotations

from pathlib import Path


def test_product_source_contains_no_frame_persistence_or_network_server_apis() -> None:
    """Adding a frame writer or listener would violate Posturely's core promise."""
    source_root = Path("src/posturely")
    source = "\n".join(path.read_text(encoding="utf-8") for path in source_root.rglob("*.py"))
    forbidden = (
        "imwrite(",
        "VideoWriter(",
        "imencode(",
        "pickle.dump(",
        "socket.listen(",
        "HTTPServer(",
    )

    assert not [token for token in forbidden if token in source]
