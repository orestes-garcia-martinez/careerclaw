from __future__ import annotations

import sys

from careerclaw import briefing as briefing_mod


def main() -> None:
    # Expect: careerclaw briefing [flags...]
    argv = sys.argv[1:]

    if not argv or argv[0] in ("-h", "--help"):
        print(
            "Usage:\n"
            "  careerclaw briefing [--resume-text PATH | --resume-pdf PATH] [options]\n\n"
            "Commands:\n"
            "  briefing   Run the CareerClaw daily briefing pipeline\n"
        )
        raise SystemExit(0)

    cmd = argv[0]
    if cmd in ("briefing", "brief"):
        # Make briefing.py parse only the flags, not the subcommand
        sys.argv = [sys.argv[0], *argv[1:]]
        briefing_mod.main()
        return

    print(f"Unknown command: {cmd}\nRun `careerclaw --help` for usage.")
    raise SystemExit(2)