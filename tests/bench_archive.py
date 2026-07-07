#!/usr/bin/env python3
"""Benchmark Hadid archive operations at scale.

Generates synthetic data and measures:
  - Initial bulk insert (100K+ messages)
  - Full-text search (FTS5)
  - Incremental update (append 1 message to existing conversation)
  - list_conversations() with JOIN+COUNT

Usage:
    python3 tests/bench_archive.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hadid.db import Archive  # noqa: E402
from hadid.models import Conversation, Message  # noqa: E402

NUM_CONVERSATIONS = 1_000
MESSAGES_PER_CONV = 100  # → 100,000 messages total

SAMPLE_WORDS = [
    "machine", "learning", "neural", "network", "training", "model",
    "dataset", "accuracy", "gradient", "optimizer", "embedding", "vector",
    "transformer", "attention", "encoder", "decoder", "pipeline", "deploy",
    "inference", "benchmark", "latency", "throughput", "scalability",
    "architecture", "microservice", "container", "kubernetes", "database",
]


def _make_content(conv_idx: int, msg_idx: int) -> str:
    """Generate deterministic pseudo-realistic message content."""
    words = []
    for i in range(20):
        w = SAMPLE_WORDS[(conv_idx * 7 + msg_idx * 3 + i) % len(SAMPLE_WORDS)]
        words.append(w)
    return " ".join(words)


def generate_conversations(
    n_convs: int, msgs_per_conv: int
) -> list[Conversation]:
    """Build synthetic conversations."""
    convs: list[Conversation] = []
    for c in range(n_convs):
        messages: list[Message] = []
        for m in range(msgs_per_conv):
            messages.append({
                "role": "user" if m % 2 == 0 else "assistant",
                "content": _make_content(c, m),
                "created_at": f"2025-01-{(c % 28) + 1:02d}T{m % 24:02d}:00:00Z",
            })
        convs.append({
            "source": "chatgpt",
            "source_id": f"bench-conv-{c:06d}",
            "title": f"Benchmark conversation {c}",
            "created_at": f"2025-01-{(c % 28) + 1:02d}T00:00:00Z",
            "messages": messages,
        })
    return convs


def bench_insert(archive: Archive, convs: list[Conversation]) -> float:
    """Measure bulk insert time."""
    t0 = time.perf_counter()
    for conv in convs:
        archive.add_conversation(conv)
    return time.perf_counter() - t0


def bench_search(archive: Archive, query: str = "transformer attention") -> float:
    """Measure FTS search time."""
    t0 = time.perf_counter()
    results = archive.search(query)
    elapsed = time.perf_counter() - t0
    print(f"  Search returned {len(results)} results")
    return elapsed


def bench_list(archive: Archive) -> float:
    """Measure list_conversations time (JOIN + COUNT)."""
    t0 = time.perf_counter()
    convs = archive.list_conversations()
    elapsed = time.perf_counter() - t0
    print(f"  Listed {len(convs)} conversations")
    return elapsed


def bench_incremental(archive: Archive, conv: Conversation) -> float:
    """Measure incremental update (append 1 message)."""
    # Add one more message to an existing conversation
    extended = dict(conv)
    extended["messages"] = list(conv["messages"]) + [{
        "role": "user",
        "content": "This is the newly appended incremental message for benchmarking",
        "created_at": "2025-06-01T00:00:00Z",
    }]
    t0 = time.perf_counter()
    result = archive.add_conversation(extended)  # type: ignore[arg-type]
    elapsed = time.perf_counter() - t0
    print(f"  Incremental result: {result}")
    return elapsed


def main() -> None:
    total_msgs = NUM_CONVERSATIONS * MESSAGES_PER_CONV
    print("=== Hadid Archive Benchmark ===")
    print(f"Conversations: {NUM_CONVERSATIONS:,}")
    print(f"Messages per conversation: {MESSAGES_PER_CONV}")
    print(f"Total messages: {total_msgs:,}")
    print()

    print("Generating synthetic data...")
    t0 = time.perf_counter()
    convs = generate_conversations(NUM_CONVERSATIONS, MESSAGES_PER_CONV)
    print(f"  Generated in {time.perf_counter() - t0:.3f}s")
    print()

    with Archive(":memory:") as archive:
        # 1. Bulk insert
        print("1. Bulk insert...")
        insert_time = bench_insert(archive, convs)
        print(f"  → {insert_time:.3f}s ({total_msgs / insert_time:,.0f} msgs/sec)")
        print()

        # 2. FTS search
        print("2. FTS search...")
        search_time = bench_search(archive)
        print(f"  → {search_time:.6f}s")
        print()

        # 3. list_conversations (JOIN + COUNT)
        print("3. list_conversations()...")
        list_time = bench_list(archive)
        print(f"  → {list_time:.6f}s")
        print()

        # 4. Incremental update
        print("4. Incremental update (append 1 msg to existing conv)...")
        incr_time = bench_incremental(archive, convs[0])
        print(f"  → {incr_time:.6f}s")
        print()

    # Summary table
    print("=" * 55)
    print(f"{'Operation':<35} {'Time':>10} {'Unit':>8}")
    print("-" * 55)
    print(f"{'Bulk insert (' + f'{total_msgs:,}' + ' msgs)':<35} {insert_time:>10.3f} {'s':>8}")
    print(f"{'FTS search':<35} {search_time:>10.6f} {'s':>8}")
    print(f"{'list_conversations':<35} {list_time:>10.6f} {'s':>8}")
    print(f"{'Incremental update (+1 msg)':<35} {incr_time:>10.6f} {'s':>8}")
    print("=" * 55)


if __name__ == "__main__":
    main()
