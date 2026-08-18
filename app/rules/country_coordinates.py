"""Approximate geographic centre of each supported country.

Data, deliberately kept apart from the rule logic that uses it.

Country centroids are a coarse approximation: a transaction in Alaska and
one in Florida both count as "US". That is acceptable here, because the
rule only has to catch travel that is impossible by an order of magnitude,
not to measure distance precisely. A production system would work with the
merchant's actual coordinates instead.
"""

# ISO 3166-1 alpha-2 code -> (latitude, longitude) in degrees.
COUNTRY_COORDINATES: dict[str, tuple[float, float]] = {
    "AE": (24.0, 54.0),
    "AT": (47.5, 14.5),
    "AU": (-25.0, 133.0),
    "BE": (50.6, 4.6),
    "BR": (-10.0, -55.0),
    "CA": (60.0, -96.0),
    "CH": (46.8, 8.2),
    "CN": (35.0, 105.0),
    "CZ": (49.8, 15.5),
    "DE": (51.0, 9.0),
    "DK": (56.0, 10.0),
    "ES": (40.0, -4.0),
    "FI": (64.0, 26.0),
    "FR": (46.2, 2.2),
    "GB": (54.0, -2.0),
    "GR": (39.0, 22.0),
    "HU": (47.2, 19.5),
    "IE": (53.0, -8.0),
    "IN": (21.0, 78.0),
    "IT": (42.8, 12.8),
    "JP": (36.2, 138.3),
    "LT": (55.2, 23.9),
    "MX": (23.0, -102.0),
    "NL": (52.2, 5.5),
    "NO": (61.0, 8.0),
    "PL": (52.0, 19.0),
    "PT": (39.5, -8.0),
    "RO": (45.9, 25.0),
    "SE": (62.0, 15.0),
    "SG": (1.35, 103.8),
    "SK": (48.7, 19.5),
    "TR": (39.0, 35.0),
    "UA": (48.4, 31.2),
    "US": (39.8, -98.6),
    "ZA": (-29.0, 24.0),
}
