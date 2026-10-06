"""Preset metadata kept separate from the backwards-compatible Format geometry."""
from dataclasses import asdict, dataclass
from importlib.resources import files
import json
import re
from .core import Format, finite

CATEGORIES = {"digital_sensor", "roll_film", "sheet_film", "holder_opening"}


@dataclass(frozen=True)
class FormatPreset:
    id: str
    display_name: str
    legacy_name: str
    category: str
    active_width_mm: float
    active_height_mm: float
    notes: str
    nominal_width_mm: float | None = None
    nominal_height_mm: float | None = None
    units: str = "mm"
    source: str | None = None

    def __post_init__(self):
        if not isinstance(self.id, str) or not re.fullmatch(r"[a-z][a-z0-9_-]*", self.id):
            raise ValueError("Preset ID must be a stable lowercase identifier.")
        if self.category not in CATEGORIES or self.units != "mm":
            raise ValueError("Invalid preset category or units.")
        if any(not isinstance(v, str) or not v.strip() for v in (self.display_name, self.legacy_name, self.notes)):
            raise ValueError("Preset names and notes are required.")
        for key in ("active_width_mm", "active_height_mm"):
            object.__setattr__(self, key, finite(getattr(self, key), key, positive=True))
        if (self.nominal_width_mm is None) != (self.nominal_height_mm is None):
            raise ValueError("Both nominal dimensions must be supplied together.")
        if self.category == "sheet_film" and self.nominal_width_mm is None:
            raise ValueError("Sheet-film presets need nominal sheet dimensions.")
        if self.nominal_width_mm is not None:
            for key in ("nominal_width_mm", "nominal_height_mm"):
                object.__setattr__(self, key, finite(getattr(self, key), key, positive=True))
            # Rectangles may be rotated; there is no universal landscape rule.
            active = sorted((self.active_width_mm, self.active_height_mm))
            nominal = sorted((self.nominal_width_mm, self.nominal_height_mm))
            if any(a > n for a, n in zip(active, nominal)):
                raise ValueError("Active area must fit inside the nominal sheet.")

    def as_format(self):
        return Format(self.legacy_name, self.active_width_mm, self.active_height_mm, self.notes)


def load_catalog(data):
    if data.get("schema_version") != 2:
        raise ValueError("Unsupported preset schema version.")
    items = [FormatPreset(**item) for item in data["presets"]]
    if len({p.id for p in items}) != len(items) or len({p.legacy_name for p in items}) != len(items):
        raise ValueError("Duplicate preset IDs or legacy names.")
    return {p.id: p for p in items}


def preset_catalog():
    return load_catalog(json.loads(files("cet").joinpath("data/formats.json").read_text(encoding="utf-8")))


def format_record(fmt):
    """Keep legacy dimensions and add explicit active-area metadata to exports."""
    preset = next((p for p in preset_catalog().values() if p.legacy_name == fmt.name
                   and (p.active_width_mm, p.active_height_mm) == (fmt.width_mm, fmt.height_mm)), None)
    return {**asdict(fmt), "preset_id": preset.id if preset else None,
            "category": preset.category if preset else "custom",
            "active_width_mm": fmt.width_mm, "active_height_mm": fmt.height_mm,
            "nominal_width_mm": preset.nominal_width_mm if preset else None,
            "nominal_height_mm": preset.nominal_height_mm if preset else None,
            "units": "mm", "source": preset.source if preset else None}
