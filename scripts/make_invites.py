"""One private link per reviewer, so three people's answers stay apart.

    python3 scripts/make_invites.py "med-college-friend" "school-friend-12th-med" "spare"

Each link carries a short random token. The reviewer never sees a label and never types a name —
you know who got which link, and the answers separate on the token. The mapping is written to
`docs/review/invites.txt`, which is gitignored, because it is the one file that connects a real
person to an opinion."""

import secrets
import sys
from pathlib import Path

OUT = Path("docs/review/invites.txt")
BASE = "https://survey.kgbnetwork.com/?r="


def main(labels):
    if not labels:
        labels = ["reviewer-1", "reviewer-2", "reviewer-3"]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines, show = [], []
    for label in labels:
        token = secrets.token_hex(3)          # 6 hex chars: short enough to survive a chat app
        lines.append(f"{token}\t{label}")
        show.append((label, f"{BASE}{token}"))
    OUT.write_text("# token\tyour label for whoever you sent it to\n"
                   "# gitignored on purpose: this is the only file linking a person to a reply\n"
                   + "\n".join(lines) + "\n")
    width = max(len(l) for l, _ in show)
    for label, link in show:
        print(f"  {label.ljust(width)}  {link}")
    print(f"\nmapping saved to {OUT} (gitignored)")
    print("replies land in /data/replies.jsonl on the box; read them with "
          "scripts/read_replies.py")


if __name__ == "__main__":
    main(sys.argv[1:])
