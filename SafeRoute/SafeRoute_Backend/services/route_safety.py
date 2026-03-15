"""Route Safety Scoring algorithm.

Implements:
1) Per-feature scoring for each segment
2) Weighted segment safety score
3) Route-level average safety score
4) Safest-route selection
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from typing import Iterable, List


@dataclass
class Segment:
    """Represents a road segment and computes its weighted safety score.

    Inputs:
    - time_score: pre-calculated score in [0, 1]
    - connecting_roads: number of connecting roads at the junction
    - many_nearby_places: True if many shops/houses are nearby, else False
    - cctv_available: True if CCTV is present, else False
    - previously_traveled: True if user has traveled this path before, else False
    """

    time_score: float
    connecting_roads: int
    many_nearby_places: bool
    cctv_available: bool
    previously_traveled: bool

    @property
    def junction_score(self) -> float:
        """Escape availability score.

        Rule:
        - If more than 2 connecting roads -> 1.0
        - If only 1 connecting road -> 0.5

        Note:
        - For exactly 2 connecting roads, this implementation treats it as 1.0
          (safer than only 1 exit).
        """
        return 1.0 if self.connecting_roads > 1 else 0.5

    @property
    def shop_score(self) -> float:
        """People presence score."""
        return 1.0 if self.many_nearby_places else 0.5

    @property
    def cctv_score(self) -> float:
        """CCTV availability score."""
        return 1.0 if self.cctv_available else 0.5

    @property
    def familiar_score(self) -> float:
        """Familiarity score."""
        return 1.0 if self.previously_traveled else 0.7

    def safety_score(self) -> float:
        """Compute weighted segment safety score.

        Formula:
        Safety Score =
          (0.3 * time_score) +
          (0.2 * junction_score) +
          (0.2 * shop_score) +
          (0.15 * cctv_score) +
          (0.15 * familiar_score)
        """
        return (
            0.3 * self.time_score
            + 0.2 * self.junction_score
            + 0.2 * self.shop_score
            + 0.15 * self.cctv_score
            + 0.15 * self.familiar_score
        )


@dataclass
class Route:
    """Represents a route made of multiple road segments."""

    name: str
    segments: List[Segment]

    def total_safety_score(self) -> float:
        """Average of all segment safety scores in this route."""
        if not self.segments:
            raise ValueError(f"Route '{self.name}' must contain at least one segment.")

        total = sum(segment.safety_score() for segment in self.segments)
        return total / len(self.segments)


def safest_route(routes: Iterable[Route]) -> Route:
    """Return the route with the highest total safety score."""
    route_list = list(routes)
    if not route_list:
        raise ValueError("At least one route is required.")
    return max(route_list, key=lambda r: r.total_safety_score())


def round_down(value: float, decimals: int = 2) -> float:
    """Round down to match examples that truncate (e.g., 0.7375 -> 0.73)."""
    quant = Decimal("1." + ("0" * decimals))
    return float(Decimal(str(value)).quantize(quant, rounding=ROUND_DOWN))


def build_segment_from_target_score(target_score: float) -> Segment:
    """Create a segment whose weighted score equals `target_score`.

    We search all valid discrete feature combinations (junction/shop/cctv/familiar)
    and solve for time_score:
      target = 0.3*time + weighted_other_features
      time   = (target - weighted_other_features)/0.3
    """
    junction_options = [(3, 1.0), (1, 0.5)]
    shop_options = [(True, 1.0), (False, 0.5)]
    cctv_options = [(True, 1.0), (False, 0.5)]
    familiar_options = [(True, 1.0), (False, 0.7)]

    for connecting_roads, junction_score in junction_options:
        for many_nearby_places, shop_score in shop_options:
            for cctv_available, cctv_score in cctv_options:
                for previously_traveled, familiar_score in familiar_options:
                    weighted_others = (
                        0.2 * junction_score
                        + 0.2 * shop_score
                        + 0.15 * cctv_score
                        + 0.15 * familiar_score
                    )
                    time = (target_score - weighted_others) / 0.3
                    if 0.0 <= time <= 1.0:
                        return Segment(
                            time_score=time,
                            connecting_roads=connecting_roads,
                            many_nearby_places=many_nearby_places,
                            cctv_available=cctv_available,
                            previously_traveled=previously_traveled,
                        )

    raise ValueError(f"Cannot build a valid segment for target score: {target_score}")


def demo() -> None:
    """Sample execution with the exact Route A/B/C scoring example."""
    # Route A has 4 segment scores: 0.78, 0.65, 0.82, 0.70
    route_a = Route(
        name="Route A",
        segments=[
            build_segment_from_target_score(0.78),
            build_segment_from_target_score(0.65),
            build_segment_from_target_score(0.82),
            build_segment_from_target_score(0.70),
        ],
    )

    # Route B overall score: 0.82 (single segment here for a simple demo)
    route_b = Route(name="Route B", segments=[build_segment_from_target_score(0.82)])

    # Route C overall score: 0.48 (single segment here for a simple demo)
    route_c = Route(name="Route C", segments=[build_segment_from_target_score(0.48)])

    routes = [route_a, route_b, route_c]

    print("Route Safety Scores:")
    for route in routes:
        score = route.total_safety_score()
        print(f"- {route.name}: {score:.4f} (display/truncated: {round_down(score, 2):.2f})")

    best = safest_route(routes)
    print(f"\nRecommended Safe Route: {best.name} ({best.total_safety_score():.4f})")


if __name__ == "__main__":
    demo()
