"""Build dist/ascii2svg.skill: the installable Claude skill (a zip holding ascii2svg/SKILL.md
and ascii2svg/scripts/ascii2svg.py). Only what Claude needs at run time goes in; tests, docs
and demo images stay in the repo.

    python3 tools/package_skill.py
"""
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = ["SKILL.md", "scripts/ascii2svg.py"]
STAMP = (2026, 1, 1, 0, 0, 0)                  # fixed timestamps: the same sources give the same bytes


def main():
    skill = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
    front = re.match(r"---\n(.*?)\n---\n", skill, re.S)
    if not front or not re.search(r"^name: ascii2svg$", front.group(1), re.M) \
            or not re.search(r"^description: .{50,}", front.group(1), re.M):
        sys.exit("SKILL.md needs frontmatter with name: ascii2svg and a description")
    out = os.path.join(ROOT, "dist", "ascii2svg.skill")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in FILES:
            info = zipfile.ZipInfo(f"ascii2svg/{rel}", STAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, open(os.path.join(ROOT, rel), "rb").read())
    print(f"{out}  ({os.path.getsize(out) // 1024} KB: {', '.join(FILES)})")


if __name__ == "__main__":
    main()
