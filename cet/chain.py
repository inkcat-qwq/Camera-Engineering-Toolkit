"""One dimension-chain model for nominal design and statistical analysis."""
from dataclasses import dataclass
from .core import Component, check_components, finite, stack_up, monte_carlo

DEFAULT_ROWS = [dict(name="Body register", nominal_mm=40.0, tolerance_mm=.05, sign=1, distribution="Uniform"),
                dict(name="Adapter", nominal_mm=10.0, tolerance_mm=.03, sign=1, distribution="Uniform"),
                dict(name="Back to sensor", nominal_mm=20.0, tolerance_mm=.02, sign=1, distribution="Uniform")]


@dataclass(frozen=True)
class DimensionChain:
    components: tuple[Component, ...]
    target_mm: float = 70.0

    def __post_init__(self):
        check_components(self.components)
        object.__setattr__(self, "target_mm", finite(self.target_mm, "Target sensor plane"))

    @classmethod
    def from_records(cls, rows, target_mm):
        return cls(tuple(Component(**row) for row in rows), target_mm)

    def summary(self):
        return stack_up(self.components, self.target_mm)

    def simulate(self, low, high, samples, seed):
        return monte_carlo(self.components, self.target_mm, low, high, samples, seed)
