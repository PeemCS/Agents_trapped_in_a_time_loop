"""Rita's daily state and an evidence gate for shared choices."""

from dataclasses import asdict, dataclass

from .town import RITA_FACTS


_EFFECTS = {
    "kindness": (0.15, 0.15, 0.15, -0.06),
    "performance": (0.15, 0.15, 0.15, -0.04),
    "prank": (-0.08, -0.06, -0.08, 0.05),
    "deception": (-0.08, -0.04, -0.06, 0.20),
}


@dataclass
class Relationship:
    trust: float = 0.20
    attraction: float = 0.15
    respect: float = 0.20
    suspicion: float = 0.0

    def update(self, kind: str, weight: float = 1.0) -> dict[str, float]:
        if kind not in _EFFECTS:
            return {}
        before = asdict(self)
        for (field, old), change in zip(before.items(), _EFFECTS[kind]):
            setattr(self, field, round(min(1.0, max(0.0, old + change * weight)), 4))
        return {field: round(value - before[field], 4) for field, value in asdict(self).items()}

    def gate(self, tick: int) -> int:
        if (self.trust >= 0.60 and self.attraction >= 0.55 and self.respect >= 0.50
                and self.suspicion < 0.30 and tick >= 26):
            return 3
        if self.trust >= 0.45 and self.attraction >= 0.35 and self.suspicion < 0.40:
            return 2
        if self.trust >= 0.30 and self.suspicion < 0.50:
            return 1
        return 0

    def potential(self, tick: int) -> float:
        return (
            0.30 * self.trust + 0.30 * self.attraction + 0.20 * self.respect
            - 0.40 * self.suspicion + 0.25 * self.gate(tick)
        )

    def attitude(self, tick: int) -> str:
        if self.suspicion >= 0.3:
            return "uneasy about how he knows things"
        return (
            "polite and cautious", "open to coffee", "comfortable spending time together",
            "open to staying longer if she chooses",
        )[self.gate(tick)]


def spoken_facts(line: str) -> tuple[str, ...]:
    lowered = line.casefold()
    return tuple(fact for fact, (keyword, _, _) in RITA_FACTS.items() if keyword in lowered)
