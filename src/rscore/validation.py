"""Validation reports: every problem found, in plain English, never repaired silently."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Issue:
    level: str  # "error" or "warning"
    table: str
    where: str  # row number in the batch, or the row's key
    message: str

    def __str__(self) -> str:
        return f"{self.level}: {self.table} {self.where}: {self.message}"


@dataclass
class Report:
    issues: list[Issue] = field(default_factory=list)

    def error(self, table: str, where: str, message: str) -> None:
        self.issues.append(Issue("error", table, where, message))

    def warning(self, table: str, where: str, message: str) -> None:
        self.issues.append(Issue("warning", table, where, message))

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def __str__(self) -> str:
        return "\n".join(str(i) for i in self.issues) or "no issues"


class ValidationError(ValueError):
    """Raised when rows fail validation. Nothing is written when it is raised."""

    def __init__(self, report: Report):
        self.report = report
        first = report.errors[:5]
        more = len(report.errors) - len(first)
        text = "\n".join(str(i) for i in first) + (f"\n... and {more} more" if more > 0 else "")
        super().__init__(text)
