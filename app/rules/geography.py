"""Geography rule: the same card used in two places at once."""

import math
from collections.abc import Sequence

from app.models import Transaction
from app.rules.base import Rule
from app.rules.country_coordinates import COUNTRY_COORDINATES

EARTH_RADIUS_KM = 6371.0


def haversine_km(point_a: tuple[float, float], point_b: tuple[float, float]) -> float:
    """Great-circle distance between two (latitude, longitude) points.

    Straight-line distance would cut through the planet; the haversine
    formula measures along its surface, which is how anyone actually travels.
    """
    lat1, lon1 = (math.radians(value) for value in point_a)
    lat2, lon2 = (math.radians(value) for value in point_b)

    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


class GeographyRule(Rule):
    """Flags travel no human could have made in the time available.

    Rather than a single "different country within an hour" threshold, the
    rule derives its own limit per country pair: distance divided by the
    fastest plausible speed. Poland to Germany in three hours is a trip;
    Poland to the United States in ten minutes is not.
    """

    name = "geography"

    def __init__(self, max_speed_kmh: float = 900.0) -> None:
        # Roughly the cruising speed of a commercial jet. Anything above it
        # is not travel, so the two transactions cannot be the same person.
        self.max_speed_kmh = max_speed_kmh

    def evaluate(
        self, transaction: Transaction, history: Sequence[Transaction]
    ) -> str | None:
        origin = COUNTRY_COORDINATES.get(transaction.country)
        if origin is None:
            # Fail open: an unmapped country is missing data, not evidence.
            # The other rules still assess this transaction.
            return None

        for past in history:
            if past.country == transaction.country:
                continue

            destination = COUNTRY_COORDINATES.get(past.country)
            if destination is None:
                continue

            elapsed_hours = (
                transaction.created_at - past.created_at
            ).total_seconds() / 3600
            if elapsed_hours < 0:
                continue  # out-of-order data, not a fraud signal

            distance_km = haversine_km(origin, destination)
            required_hours = distance_km / self.max_speed_kmh

            if elapsed_hours < required_hours:
                return (
                    f"{past.country} to {transaction.country} "
                    f"({distance_km:.0f} km) in {elapsed_hours * 60:.0f} min, "
                    f"needs at least {required_hours * 60:.0f} min"
                )

        return None
