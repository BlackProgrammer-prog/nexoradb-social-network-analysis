from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class RelationshipPair:
    user_a: str
    user_b: str

    @classmethod
    def normalized(cls, first: str, second: str) -> "RelationshipPair":
        a, b = sorted((first.strip(), second.strip()))
        return cls(a, b)

    @property
    def pair_id(self) -> str:
        return f"{self.user_a}__{self.user_b}"


@dataclass(frozen=True)
class ParsedFile:
    lines_read: int
    users: tuple[str, ...]
    pairs: tuple[RelationshipPair, ...]
    duplicates_skipped: int


class FileFormatError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("\n".join(errors))


def parse_relationship_file(content: bytes) -> ParsedFile:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise FileFormatError(["فایل باید با UTF-8 ذخیره شده باشد."]) from exc

    errors: list[str] = []
    pairs: set[RelationshipPair] = set()
    users: set[str] = set()
    duplicates = 0
    non_empty_lines = 0

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        non_empty_lines += 1
        columns = line.split()
        if len(columns) != 3:
            errors.append(f"خط {line_number}: دقیقاً سه ستون لازم است.")
            continue

        first, second, mutual = columns
        if not first or not second:
            errors.append(f"خط {line_number}: شناسه‌ی کاربر خالی است.")
            continue
        if first == second:
            errors.append(f"خط {line_number}: ارتباط کاربر با خودش مجاز نیست.")
            continue
        if mutual != "1":
            errors.append(f"خط {line_number}: ستون سوم فقط می‌تواند 1 باشد.")
            continue

        pair = RelationshipPair.normalized(first, second)
        if pair in pairs:
            duplicates += 1
            continue
        pairs.add(pair)
        users.update((first, second))

    if not non_empty_lines:
        errors.append("فایل خالی است.")
    if errors:
        raise FileFormatError(errors[:100])

    return ParsedFile(
        lines_read=non_empty_lines,
        users=tuple(sorted(users)),
        pairs=tuple(sorted(pairs)),
        duplicates_skipped=duplicates,
    )

