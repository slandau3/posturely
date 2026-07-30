from posturely.__main__ import build_parser


def test_parser_exposes_runtime_modes() -> None:
    """Removing a supported runtime mode must break the public CLI contract."""
    help_text = build_parser().format_help()

    for flag in ("--demo", "--camera", "--model", "--mirror", "--no-preview"):
        assert flag in help_text
