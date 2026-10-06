"""Portable exports: explicit units, inputs, schema, and JSON-safe infinity."""
import csv
from datetime import datetime, timezone
import io
import json
import math

from cet import __version__


def clean(value):
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return "Infinity" if value == math.inf else "-Infinity" if value == -math.inf else None
    return value


def report(tool, inputs, results):
    return clean({"schema_version": 2, "toolkit_version": __version__, "tool": tool,
                  "created_utc": datetime.now(timezone.utc).isoformat(),
                  "inputs": inputs, "results": results})


def to_json(payload):
    return json.dumps(clean(payload), indent=2, ensure_ascii=False, allow_nan=False)


def to_csv(payload):
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["section", "parameter", "value"])

    def walk(value, prefix="", section="metadata"):
        if isinstance(value, dict):
            for key, child in value.items():
                walk(child, f"{prefix}.{key}" if prefix else key, section)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{prefix}[{index}]", section)
        else:
            # Avoid spreadsheet formula execution in user-supplied names.
            item = clean(value)
            if isinstance(item, str) and item.startswith(("=", "+", "-", "@", "\t", "\r", "\n")):
                item = "'" + item
            writer.writerow([section, prefix, item])

    for key, value in payload.items():
        walk(value, "" if key in ("inputs", "results") else key,
             key if key in ("inputs", "results") else "metadata")
    return output.getvalue()
