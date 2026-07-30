from __future__ import annotations

from posturely.private_launch import build_private_command


def test_private_launch_denies_all_network_and_preserves_cli_arguments() -> None:
    command = build_private_command(
        ["--camera", "0", "--model", "pose.task"],
        python="/project/.venv/bin/python",
    )

    assert command[:2] == ["/usr/bin/sandbox-exec", "-p"]
    assert "(deny network*)" in command[2]
    assert command[3:6] == ["/project/.venv/bin/python", "-m", "posturely"]
    assert command[6:] == ["--camera", "0", "--model", "pose.task"]
