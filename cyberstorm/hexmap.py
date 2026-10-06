"""Battlefield geometry in odd-column offset coordinates; no input or SDL types."""

from dataclasses import dataclass
import math


@dataclass(frozen=True, order=True)
class Hex:
    column: int
    row: int

    @property
    def origin(self):
        """Observed 64×64 footprint, 48-pixel columns and 32-pixel stagger."""
        return self.column * 48, self.row * 64 + (self.column % 2) * 32

    @property
    def center(self):
        x, y = self.origin
        return x + 32, y + 32

    @property
    def outline(self):
        x, y = self.origin
        return tuple((x + dx, y + dy) for dx, dy in
                     ((16, 0), (48, 0), (64, 32), (48, 64), (16, 64), (0, 32)))

    def contains(self, point):
        x, y = self.center
        dx, dy = abs(point[0] - x), abs(point[1] - y)
        return dy <= 32 + 1e-9 and 2 * dx + dy <= 64 + 1e-9


class HexMap:
    def __init__(self, cells):
        self.cells = frozenset(cells)
        vertices = [point for cell in self.cells for point in cell.outline]
        self.bounds = ((min(p[0] for p in vertices), min(p[1] for p in vertices),
                        max(p[0] for p in vertices), max(p[1] for p in vertices))
                       if vertices else None)

    def pick(self, point):
        """Test only neighboring footprints; ties choose lowest column then row.

        Membership is explicit so empty maps, holes and outer scallops never
        produce invented cells. Picking matches the displayed polygon geometry.
        """
        x, y = point
        if not all(math.isfinite(v) for v in point):
            return None
        column = math.floor(x / 48)
        for c in range(column - 1, column + 1):
            row = math.floor((y - (c % 2) * 32) / 64)
            for r in range(row - 1, row + 1):
                cell = Hex(c, r)
                if cell in self.cells and cell.contains(point):
                    return cell
        return None
