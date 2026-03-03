from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ScanConfig:
    days: int = 30
    confirm_test_matches: bool = False
