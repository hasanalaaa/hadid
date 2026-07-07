"""Hadid command-line interface."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
import sys
import zipfile
from pathlib import Path

from . import __version__
from .db import DEFAULT_DB_PATH, Archive
from .export import conversation_to_markdown, safe_filename
from .importers import (
    chatgpt,
    claude,
    detect_platform,
    gemini,
    load_json_from_path,
)

IMPORTERS = {
    "chatgpt": chatgpt.parse_data,
    "claude": claude.parse_data,
    "gemini": gemini.parse_data,
}


def cmd_import(args: argparse.Namespace) -> None:
    data = load_json_from_path(args.file)
    platform = args.platform
    if platform == "auto":
        platform = detect_platform(data)
        print(f"Detected platform: {platform}")
    added = updated = skipped = messages = 0
    print("Importing conversations, this might take a moment...")
    with Archive(args.db) as archive:
        for i, conv in enumerate(IMPORTERS[platform](data)):
            if i > 0 and i % 500 == 0:
                print(f"  ...processed {i} conversations", file=sys.stderr)
            if conv.get("_source_id_generated"):
                print(
                    "Warning: "
                    f"{conv['source']} conversation {conv['title']!r} has no "
                    "original id; generated deterministic source_id "
                    f"{conv['source_id']}.",
                    file=sys.stderr,
                )
            result = archive.add_conversation(conv)
            if result is None:
                skipped += 1
            elif result[0] == "added":
                added += 1
                messages += result[1]
            else:
                updated += 1
                messages += result[1]
    print(
        f"Added {added}, updated {updated}, skipped {skipped} "
        f"conversation(s); {messages} new message(s)."
    )


def cmd_search(args: argparse.Namespace) -> None:
    with Archive(args.db) as archive:
        results = archive.search(args.query, source=args.source, limit=args.limit)
    if not results:
        print("No results.")
        return
    for r in results:
        print(f"[{r['source']}] {r['title']}  (conversation #{r['conversation_id']})")
        print(f"  {r['role']}: {r['snippet']}")
        print()


def cmd_list(args: argparse.Namespace) -> None:
    with Archive(args.db) as archive:
        convs = archive.list_conversations(
            source=args.source, favorites_only=args.favorites
        )
    if not convs:
        print("Archive is empty. Run: hadid import auto <export file>")
        return
    for c in convs:
        star = "\u2605" if c["favorite"] else " "
        date = (c["created_at"] or "")[:10]
        print(
            f"{star} #{c['id']:>4}  [{c['source']}]  {date}  {c['title']}  "
            f"({c['message_count']} msgs)"
        )


def cmd_stats(args: argparse.Namespace) -> None:
    with Archive(args.db) as archive:
        s = archive.stats()
    print(f"Conversations: {s['conversations']}")
    print(f"Messages:      {s['messages']}")
    print(f"Favorites:     {s['favorites']}")
    for source, n in sorted(s["by_source"].items()):
        print(f"  {source}: {n} conversation(s)")


def cmd_export(args: argparse.Namespace) -> None:
    with Archive(args.db) as archive:
        if args.all:
            convs = archive.list_conversations()
            os.makedirs(args.dir, exist_ok=True)
            for c in convs:
                conv = archive.get_conversation(c["id"])
                if conv is None:  # pragma: no cover - race safety
                    continue
                name = f"{c['id']:04d}-{safe_filename(conv['title'])}.md"
                Path(args.dir, name).write_text(
                    conversation_to_markdown(conv), encoding="utf-8"
                )
            print(f"Exported {len(convs)} conversation(s) to {args.dir}/")
            return
        if args.id is None:
            raise ValueError("provide a conversation id or use --all")
        conv = archive.get_conversation(args.id)
    if conv is None:
        raise ValueError(f"conversation #{args.id} not found")
    md = conversation_to_markdown(conv)
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
        print(f"Exported to {args.out}")
    else:
        print(md)


def cmd_favorite(args: argparse.Namespace) -> None:
    with Archive(args.db) as archive:
        value = archive.toggle_favorite(args.id)
    if value is None:
        raise ValueError(f"conversation #{args.id} not found")
    state = "added to" if value else "removed from"
    print(f"Conversation #{args.id} {state} favorites.")


def cmd_serve(args: argparse.Namespace) -> None:
    from .web import serve

    serve(db_path=args.db, host=args.host, port=args.port)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="hadid",
        description="Own your AI conversations - local archive and search.",
    )
    p.add_argument("--version", action="version", version=f"hadid {__version__}")
    p.add_argument("--db", default=DEFAULT_DB_PATH, help="Path to the archive database")
    p.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug logging"
    )
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("import", help="Import a platform export file or ZIP")
    sp.add_argument("platform", choices=[*sorted(IMPORTERS), "auto"])
    sp.add_argument("file", help="Path to the export JSON or ZIP file")
    sp.set_defaults(func=cmd_import)

    sp = sub.add_parser("search", help="Full-text search across all messages")
    sp.add_argument("query")
    sp.add_argument("--source", choices=sorted(IMPORTERS), help="Filter by platform")
    sp.add_argument("--limit", type=int, default=20)
    sp.set_defaults(func=cmd_search)

    sp = sub.add_parser("list", help="List archived conversations")
    sp.add_argument("--source", choices=sorted(IMPORTERS), help="Filter by platform")
    sp.add_argument("--favorites", action="store_true", help="Only favorites")
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("stats", help="Show archive statistics")
    sp.set_defaults(func=cmd_stats)

    sp = sub.add_parser("export", help="Export conversations to Markdown")
    sp.add_argument("id", nargs="?", type=int, help="Conversation id")
    sp.add_argument("--all", action="store_true", help="Export every conversation")
    sp.add_argument("--out", help="Output file (single conversation)")
    sp.add_argument("--dir", default="hadid-exports", help="Output directory for --all")
    sp.set_defaults(func=cmd_export)

    sp = sub.add_parser("favorite", help="Toggle a conversation's favorite flag")
    sp.add_argument("id", type=int)
    sp.set_defaults(func=cmd_favorite)

    sp = sub.add_parser("serve", help="Start the local web app")
    sp.add_argument("--host", default="127.0.0.1")
    sp.add_argument("--port", type=int, default=8642)
    sp.set_defaults(func=cmd_serve)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    try:
        args.func(args)
    except FileNotFoundError as e:
        print(
            f"Error: File not found: {e.filename}. Please check the path and try again.",
            file=sys.stderr,
        )
        return 1
    except PermissionError as e:
        print(f"Error: Permission denied. Cannot access {e.filename}.", file=sys.stderr)
        return 1
    except zipfile.BadZipFile:
        print(
            "Error: The ZIP file appears to be corrupted or is not a valid ZIP archive.",
            file=sys.stderr,
        )
        return 1
    except json.JSONDecodeError:
        print("Error: The JSON file is invalid or corrupted.", file=sys.stderr)
        return 1
    except sqlite3.Error as e:
        print(f"Database Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
