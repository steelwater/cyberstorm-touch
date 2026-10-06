"""Input-independent bounded camera, using drawable pixels for all operations."""

from .viewport import Viewport, positive


class Camera:
    MIN_ZOOM = 0.25
    MAX_ZOOM = 4.0

    def __init__(self, reference, center, bounds, size):
        self.reference = reference
        self.center = center
        self.bounds = bounds
        self.size = size
        self.zoom = 1.0
        self.integer = True
        self.constrain()

    @property
    def view(self):
        return Viewport.fit(self.size, self.reference, self.center, self.zoom, self.integer)

    def constrain(self):
        view = self.view
        if self.bounds is None:
            return
        left, top, right, bottom = self.bounds
        result = []
        for value, low, high, pixels in zip(self.center, (left, top), (right, bottom), self.size):
            half = pixels / (2 * view.scale)
            result.append((low + high) / 2 if 2 * half >= high - low
                          else min(high - half, max(low + half, value)))
        self.center = tuple(result)

    def resize(self, size):
        self.size = size
        self.constrain()

    def anchor(self, world, screen):
        """Keep world under screen where terrain bounds allow it."""
        view = self.view
        self.center = (world[0] - (screen[0] - view.width / 2) / view.scale,
                       world[1] - (screen[1] - view.height / 2) / view.scale)
        self.constrain()

    def pan(self, start, end):
        self.anchor(self.view.world(start), end)

    def set_zoom(self, zoom, focal=None):
        positive(zoom, 'zoom')
        focal = focal if focal is not None else (self.size[0] / 2, self.size[1] / 2)
        world = self.view.world(focal)
        self.zoom = min(self.MAX_ZOOM, max(self.MIN_ZOOM, zoom))
        self.anchor(world, focal)

    def toggle_integer(self):
        self.integer = not self.integer
        self.constrain()
