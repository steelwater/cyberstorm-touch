"""Drawing coordinates only; no selection, navigation, or gameplay rules."""

from dataclasses import dataclass
import math


def positive(value, label):
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f'{label} must be finite and positive')
    return value


@dataclass(frozen=True)
class Viewport:
    width: int
    height: int
    center: tuple[float, float]
    scale: float

    @classmethod
    def fit(cls, size, reference, center, zoom=1.0, integer=True):
        """Use drawable pixels, uniform scaling, and extra world space on wide views."""
        w, h = size
        rw, rh = reference
        for value in (w, h, rw, rh, zoom):
            positive(value, 'viewport dimension or zoom')
        if len(center) != 2 or not all(math.isfinite(v) for v in center):
            raise ValueError('camera center must contain two finite coordinates')
        fit = min(w / rw, h / rh) * zoom
        scale = max(1, math.floor(fit)) if integer and fit >= 1 else fit
        return cls(w, h, tuple(center), scale)

    def screen(self, point):
        return ((point[0] - self.center[0]) * self.scale + self.width / 2,
                (point[1] - self.center[1]) * self.scale + self.height / 2)

    def rectangle(self, position, anchor, size):
        # Round both edges, not the width independently, so adjacent tiles meet.
        x, y = self.screen((position[0] - anchor[0], position[1] - anchor[1]))
        return (round(x), round(y), round(x + size[0] * self.scale) - round(x),
                round(y + size[1] * self.scale) - round(y))

    @property
    def hud_safe_rect(self):
        """Centered 16:9 maximum safe width for later UI, in drawable pixels."""
        width = min(self.width, self.height * 16 / 9)
        return ((self.width - width) / 2, 0, width, self.height)


def hex_origin(column, row):
    """Observed 64-pixel S1P1 hex footprint: 48-pixel columns, staggered 32."""
    return column * 48, row * 64 + (column % 2) * 32


def hex_outline(origin):
    x, y = origin
    return tuple((x + dx, y + dy) for dx, dy in
                 ((16, 0), (48, 0), (64, 32), (48, 64), (16, 64), (0, 32)))


@dataclass
class Timeline:
    """Diagnostic elapsed seconds, independent of game turns and frame rate."""
    elapsed: float = 0.0
    paused: bool = False

    def advance(self, seconds):
        if not math.isfinite(seconds) or seconds < 0:
            raise ValueError('elapsed time must be finite and nonnegative')
        if not self.paused:
            self.elapsed += seconds

    def frame(self, count, fps):
        if count < 1:
            raise ValueError('animation needs at least one frame')
        positive(fps, 'playback rate')
        return math.floor(self.elapsed * fps) % count
