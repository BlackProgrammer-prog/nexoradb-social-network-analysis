"""File import service for three-column relationship format.

This module handles parsing, validation, and processing of the three-column
file format used to import user relationships into the graph.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple, List, Set

from schemas import ImportResponse


def parse_line(line: str) -> Optional[Tuple[str, str]]:
    """Parse a single line from the three-column file format.

    Expected format: "U01 U02 1" (user_a, user_b, flag)
    Returns sorted (user_a, user_b) tuple or None if invalid.

    Rules:
    - Flag must be exactly "1" (mutual relationship)
    - user_a and user_b must be non-empty
    - user_a and user_b cannot be the same (self-loop rejected)
    - Order is normalized (sorting) to detect reverse duplicates
    """
    line = line.strip()
    if not line:
        return None

    parts = re.split(r'[\s\t]+', line)
    if len(parts) != 3:
        return None

    user_a, user_b, flag = parts[0].strip(), parts[1].strip(), parts[2].strip()

    if not user_a or not user_b:
        return None
    if user_a == user_b:
        return None
    if flag != "1":
        return None

    # Normalize order for duplicate detection
    if user_a > user_b:
        user_a, user_b = user_b, user_a

    return user_a, user_b


def validate_file(content: str) -> List[str]:
    """Validate the entire file before any write operation.

    Returns a list of error messages. Empty list means the file is valid.
    """
    errors = []
    lines = content.splitlines()

    for i, line in enumerate(lines, 1):
        if not line.strip():
            continue
        parsed = parse_line(line)
        if parsed is None:
            errors.append(f"Line {i}: Invalid format")

    return errors


def extract_unique_users(content: str) -> Set[str]:
    """Extract unique user IDs from the file content."""
    users = set()
    for line in content.splitlines():
        if not line.strip():
            continue
        parsed = parse_line(line)
        if parsed:
            users.add(parsed[0])
            users.add(parsed[1])
    return users


def extract_unique_pairs(content: str) -> Set[str]:
    """Extract unique relationship pairs (order-independent)."""
    pairs = set()
    for line in content.splitlines():
        if not line.strip():
            continue
        parsed = parse_line(line)
        if parsed:
            pair_id = f"{parsed[0]}__{parsed[1]}"
            pairs.add(pair_id)
    return pairs


def process_import(content: str) -> ImportResponse:
    """Process the file and generate import statistics.

    This function validates the file and returns statistics without
    actually executing any database operations.
    """
    lines = [l for l in content.splitlines() if l.strip()]

    # Validate the file
    errors = validate_file(content)
    if errors:
        return ImportResponse(
            lines_read=len(lines),
            unique_users=0,
            unique_pairs=0,
            directed_edges_created=0,
            duplicates_skipped=0,
            errors=errors
        )

    # Extract unique data
    users = extract_unique_users(content)
    pairs = extract_unique_pairs(content)

    # Detect duplicates
    seen_pairs = set()
    duplicates = 0
    for line in content.splitlines():
        if not line.strip():
            continue
        parsed = parse_line(line)
        if parsed:
            pair_id = f"{parsed[0]}__{parsed[1]}"
            if pair_id in seen_pairs:
                duplicates += 1
            seen_pairs.add(pair_id)

    return ImportResponse(
        lines_read=len(lines),
        unique_users=len(users),
        unique_pairs=len(pairs),
        directed_edges_created=len(pairs) * 2,
        duplicates_skipped=duplicates,
        errors=[]
    )


def generate_insert_queries(content: str) -> List[str]:
    """Generate safe INSERT queries from the file content.

    This function assumes the file has already been validated.
    """
    queries = []
    seen_pairs = set()
    seen_users = set()

    for line in content.splitlines():
        if not line.strip():
            continue
        parsed = parse_line(line)
        if not parsed:
            continue

        a, b = parsed
        pair_id = f"{a}__{b}"

        if pair_id in seen_pairs:
            continue
        seen_pairs.add(pair_id)

        # Insert users (idempotent: only if not seen)
        if a not in seen_users:
            seen_users.add(a)
            queries.append(
                f"INSERT INTO professor_users VALUES ('{{\"_id\":\"{a}\",\"username\":\"{a}\"}}')"
            )
        if b not in seen_users:
            seen_users.add(b)
            queries.append(
                f"INSERT INTO professor_users VALUES ('{{\"_id\":\"{b}\",\"username\":\"{b}\"}}')"
            )

        # Create two directed edges (mutual relationship)
        queries.append(
            f"INSERT INTO professor_follows VALUES ('{{\"_id\":\"rel_{a}_{b}_ab\",\"pair_id\":\"{pair_id}\",\"from_id\":\"{a}\",\"to_id\":\"{b}\"}}')"
        )
        queries.append(
            f"INSERT INTO professor_follows VALUES ('{{\"_id\":\"rel_{a}_{b}_ba\",\"pair_id\":\"{pair_id}\",\"from_id\":\"{b}\",\"to_id\":\"{a}\"}}')"
        )

    return queries