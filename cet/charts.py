"""Small Matplotlib figures; no global plotting state shared between sessions."""
from matplotlib.figure import Figure
from matplotlib.patches import Circle, Rectangle
import numpy as np

COLORS = ["#168b99", "#dd9740", "#7c79c9", "#cc6882", "#4e9d72", "#559ac5"]


def canvas(dark=False, size=(8, 3.8)):
    fig = Figure(figsize=size, layout="constrained")
    ax = fig.subplots()
    bg, fg = ("#131b27", "#dbe5f2") if dark else ("#f7f9fc", "#304057")
    fig.set_facecolor(bg)
    ax.set_facecolor(bg)
    ax.tick_params(colors=fg, labelsize=9)
    ax.xaxis.label.set_color(fg)
    ax.yaxis.label.set_color(fg)
    ax.title.set_color(fg)
    for spine in ax.spines.values():
        spine.set_color("#536075" if dark else "#d5dce7")
    ax.grid(alpha=.13, color=fg)
    ax.set_axisbelow(True)
    return fig, ax, fg


def format_rectangles(formats, dark=False):
    fig, ax, fg = canvas(dark)
    width = max(f.width_mm for f in formats)
    height = max(f.height_mm for f in formats)
    for i, fmt in enumerate(formats):
        ax.add_patch(Rectangle((-fmt.width_mm / 2, -fmt.height_mm / 2), fmt.width_mm, fmt.height_mm,
                               fill=False, lw=2, edgecolor=COLORS[i % len(COLORS)], label=fmt.name))
    ax.set(xlim=(-width * .65, width * .65), ylim=(-height * .8, height * .8),
           xlabel="Image width (mm)", ylabel="Image height (mm)")
    ax.set_aspect("equal")
    ax.legend(loc="upper left", fontsize=8, facecolor=fig.get_facecolor(), labelcolor=fg)
    return fig


def fov_plot(fmt, focal, dark=False):
    fig, ax, fg = canvas(dark)
    distance = 1.0
    for size, label, color in [(fmt.width_mm, "Horizontal field", COLORS[0]),
                                (fmt.height_mm, "Vertical field", COLORS[1])]:
        extent = size / (2 * focal)
        ax.fill([0, distance, distance], [0, -extent, extent], color=color, alpha=.08)
        ax.plot([distance, 0, distance], [-extent, 0, extent], color=color, lw=1.8, label=label)
    ax.axvline(1, color=fg, alpha=.4, ls=":")
    ax.scatter([0], [0], color=fg, s=24)
    ax.set(xlim=(-.04, 1.08), xlabel="Distance from projection centre (m)", ylabel="Field extent (m)")
    ax.legend(fontsize=9, facecolor=fig.get_facecolor(), labelcolor=fg, loc="upper left")
    return fig


def coverage_plot(fmt, circle, dx, dy, dark=False):
    fig, ax, fg = canvas(dark)
    ax.add_patch(Circle((0, 0), circle / 2, fc=COLORS[0], alpha=.08))
    ax.add_patch(Circle((0, 0), circle / 2, fill=False, ec=COLORS[0], lw=2, label="Image circle"))
    ax.add_patch(Rectangle((dx - fmt.width_mm / 2, dy - fmt.height_mm / 2), fmt.width_mm,
                           fmt.height_mm, fill=False, lw=2, ec=COLORS[1], label="Shifted image area"))
    ax.axhline(0, color=fg, lw=.6, alpha=.4)
    ax.axvline(0, color=fg, lw=.6, alpha=.4)
    reach = max(circle / 2, abs(dx) + fmt.width_mm / 2, abs(dy) + fmt.height_mm / 2) * 1.15
    ax.set(xlim=(-reach, reach), ylim=(-reach, reach), xlabel="Horizontal position (mm)",
           ylabel="Vertical position (mm)")
    ax.set_aspect("equal")
    ax.legend(fontsize=8, facecolor=fig.get_facecolor(), labelcolor=fg)
    return fig


def stack_plot(components, target, dark=False):
    fig, ax, fg = canvas(dark)
    position = 0
    for i, c in enumerate(components):
        delta = c.sign * c.nominal_mm
        ax.barh(i, delta, left=position, color=COLORS[i % len(COLORS)], height=.55)
        position += delta
    ax.axvline(target, color=fg, ls="--", label=f"Target {target:g} mm")
    ax.set_yticks(range(len(components)), [c.name for c in components])
    ax.invert_yaxis()
    ax.set_xlabel("Signed cumulative position from lens flange (mm)")
    ax.legend(fontsize=8, facecolor=fig.get_facecolor(), labelcolor=fg)
    return fig


def histogram(errors, low, high, dark=False):
    fig, ax, fg = canvas(dark)
    ax.hist(errors, bins=60, color=COLORS[0], alpha=.8, edgecolor=fig.get_facecolor(), lw=.3)
    ax.axvline(low, color=COLORS[1], ls="--", lw=2, label="Specification limits")
    ax.axvline(high, color=COLORS[1], ls="--", lw=2)
    ax.axvline(float(np.mean(errors)), color=fg, lw=1, label="Sample mean")
    ax.set(xlabel="Sensor-plane error (mm)", ylabel="Sample count")
    ax.legend(fontsize=9, facecolor=fig.get_facecolor(), labelcolor=fg)
    return fig
