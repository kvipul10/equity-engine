"""Project paths. The project root defaults to the repository root (parent of engine/), overridable with
the EQUITY_ENGINE_ROOT environment variable or the CLI's --root option (used by tests)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Paths:
    root: Path

    @classmethod
    def default(cls, root: "str | Path | None" = None) -> "Paths":
        if root is None:
            root = os.environ.get("EQUITY_ENGINE_ROOT") or Path(__file__).resolve().parent.parent
        return cls(Path(root).resolve())

    @property
    def raw_dir(self) -> Path:
        return self.root / "data" / "raw" / "screener"

    @property
    def vintages_dir(self) -> Path:
        return self.raw_dir / "vintages"

    @property
    def manual_dir(self) -> Path:
        return self.root / "data" / "manual"

    @property
    def processed_dir(self) -> Path:
        return self.root / "data" / "processed"

    @property
    def reports_dir(self) -> Path:
        return self.root / "reports"

    @property
    def config_dir(self) -> Path:
        return self.root / "config"

    @property
    def universe_csv(self) -> Path:
        return self.root / "data" / "universe.csv"

    def raw_file(self, ticker: str) -> Path:
        return self.raw_dir / f"{ticker}.xlsx"

    def manual_file(self, ticker: str) -> Path:
        return self.manual_dir / f"{ticker}_kpis.csv"
