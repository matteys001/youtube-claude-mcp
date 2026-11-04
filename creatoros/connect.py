"""Command-line helper: `creatoros-connect` opens Google sign-in and connects a channel.

Use this the first time (or after authorization expires) so the browser step happens
outside Claude. You can also connect from inside Claude with the youtube_connect_channel tool.
"""
from __future__ import annotations

import sys

from . import auth, config
from .errors import CreatorOSError


def main() -> None:
    config.ensure_dirs()
    args = sys.argv[1:]
    try:
        if args and args[0] == "list":
            for c in auth.list_connections():
                print(f"{c.get('title')}  ({c['channel_id']}){'  [default]' if c.get('is_default') else ''}")
            return
        ch = auth.run_connect_flow()
        print(f"\nConnected: {ch['title']}  ({ch['channel_id']})")
        print(f"Encrypted token saved in {config.TOKENS_DIR}")
        print("You can now use CreatorOS from Claude.")
    except CreatorOSError as e:
        print(f"\nCould not connect.\n{e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
