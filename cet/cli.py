"""Small optional CLI; the primary interface is app.py."""
import argparse
from cet.core import Format, fov, sensor
from cet.export import report, to_json


def main():
    parser = argparse.ArgumentParser(description="Camera Engineering Toolkit")
    parser.add_argument("tool", choices=["fov", "sensor"])
    parser.add_argument("--width", type=float, default=48)
    parser.add_argument("--height", type=float, default=36)
    parser.add_argument("--focal", type=float, default=80)
    args = parser.parse_args()
    try:
        fmt = Format("Custom", args.width, args.height)
        result = fov(fmt, args.focal) if args.tool == "fov" else sensor(fmt)
    except ValueError as exc:
        parser.error(str(exc))
    print(to_json(report(args.tool, vars(args), result)))


if __name__ == "__main__":
    main()
