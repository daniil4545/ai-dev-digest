import argparse
import json
import logging
import re
import sys
from dataclasses import asdict
from pathlib import Path

from src.collect import collect_all, normalize_url
from src.config import get_config
from src.models import NewsItem
from src.storage import Storage

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "digest.db"

_LINK = re.compile(r"https?://[^\s<>]+")
# Punctuation that ends a sentence or wraps a link, not part of the URL
_LINK_TAIL = ".,;:!?>]`\"'»"


def collect_candidates(storage: Storage, max_item_hours: int) -> list[NewsItem]:
    """Collect fresh items that have not appeared in any digest yet."""
    seen: set[str] = set()
    candidates: list[NewsItem] = []
    for item in collect_all(max_item_hours=max_item_hours):
        if item.url in seen or storage.was_link_sent(item.url):
            continue
        seen.add(item.url)
        candidates.append(item)
    return candidates


def _trim_link(link: str) -> str:
    """Cut wrapping punctuation; ")" only when unbalanced, as in Foo_(bar)."""
    while link:
        last = link[-1]
        unbalanced = last == ")" and link.count("(") < link.count(")")
        if last not in _LINK_TAIL and not unbalanced:
            break
        link = link[:-1]
    return link


def mark_digest(storage: Storage, digest_path: Path) -> int:
    """Record every link of a written digest, so later runs skip it."""
    text = digest_path.read_text(encoding="utf-8")
    links = {normalize_url(_trim_link(m)) for m in _LINK.findall(text)}
    for link in links:
        storage.mark_link_sent(link)
    return len(links)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m src.main",
        description="Candidates for the /digest skill and the record of used links.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("collect", help="print fresh candidates as JSON")
    mark = commands.add_parser("mark", help="record the links of a digest file")
    mark.add_argument("digest", type=Path)
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stderr,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    storage = Storage(str(DB_PATH))
    try:
        if args.command == "collect":
            items = collect_candidates(storage, get_config().max_item_hours)
            logger.info("Candidates after dedup: %d", len(items))
            json.dump([asdict(i) for i in items], sys.stdout, ensure_ascii=False)
            print()
            return 0

        try:
            count = mark_digest(storage, args.digest)
        except FileNotFoundError:
            print(f"digest file not found: {args.digest}", file=sys.stderr)
            return 1
        print(count)
        return 0
    finally:
        storage.close()


if __name__ == "__main__":
    sys.exit(main())
