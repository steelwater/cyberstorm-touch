"""Mouse/touch gesture state. Camera and map never depend on these input rules.

Positions are logical window points; the adapter supplies drawable dimensions.
The 8-point drag threshold therefore stays consistent on high-DPI displays.
"""

from dataclasses import dataclass
import math


@dataclass
class Contact:
    start: tuple[float, float]
    position: tuple[float, float]
    dragged: bool = False


class Navigation:
    DRAG_THRESHOLD = 8

    def __init__(self, camera, hexmap, logical_size):
        self.camera = camera
        self.hexmap = hexmap
        self.logical_size = logical_size
        self.selected = None
        self.hover = None
        self.mouse = None
        self.mouse_button = None
        self.fingers = {}
        self.multitouch = False
        self.pinch = None

    def drawable(self, point):
        return tuple(p * pixels / logical for p, pixels, logical in
                     zip(point, self.camera.size, self.logical_size))

    def pick(self, point):
        if not (0 <= point[0] < self.logical_size[0] and 0 <= point[1] < self.logical_size[1]):
            return None
        return self.hexmap.pick(self.camera.view.world(self.drawable(point)))

    def cancel(self):
        self.mouse = None
        self.mouse_button = None
        self.fingers.clear()
        self.multitouch = False
        self.pinch = None
        self.hover = None

    def resize(self, logical_size, drawable_size):
        if logical_size != self.logical_size or drawable_size != self.camera.size:
            self.cancel()
            self.logical_size = logical_size
            self.camera.resize(drawable_size)

    def mouse_down(self, button, point):
        if button in (1, 2, 3) and not self.fingers and self.mouse is None:
            self.mouse = Contact(point, point)
            self.mouse_button = button

    def _drag(self, contact, point):
        old = contact.position
        contact.position = point
        if not contact.dragged:
            if math.dist(contact.start, point) < self.DRAG_THRESHOLD:
                return
            contact.dragged = True
            old = contact.start
        self.camera.pan(self.drawable(old), self.drawable(point))

    def mouse_move(self, point):
        if self.fingers:
            return
        if self.mouse is not None:
            self._drag(self.mouse, point)
        self.hover = self.pick(point)

    def mouse_up(self, button, point):
        if self.mouse is None or button != self.mouse_button:
            return
        self._drag(self.mouse, point)
        if button == 1 and not self.mouse.dragged:
            self.selected = self.pick(point)
        self.mouse = None
        self.mouse_button = None
        self.hover = self.pick(point)

    def wheel(self, amount, point):
        if self.fingers:
            return
        # Cap a single event before exponentiation; repeated events still reach limits.
        self.camera.set_zoom(self.camera.zoom * 1.25 ** max(-20, min(20, amount)),
                             self.drawable(point))
        if self.mouse is not None:
            self.mouse.dragged = True
        self.hover = self.pick(point)

    def _pinch_geometry(self):
        first, second = list(self.fingers.values())[:2]
        a, b = first.position, second.position
        return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), math.dist(a, b)

    def _start_pinch(self):
        self.pinch = None
        if len(self.fingers) == 2:
            midpoint, distance = self._pinch_geometry()
            if distance > 0:
                self.pinch = (distance, self.camera.zoom,
                              self.camera.view.world(self.drawable(midpoint)))

    def finger_down(self, identifier, point):
        if identifier in self.fingers:
            return
        self.mouse = None
        self.mouse_button = None
        self.hover = None
        self.fingers[identifier] = Contact(point, point)
        if len(self.fingers) > 1:
            self.multitouch = True
            for contact in self.fingers.values():
                contact.dragged = True
        self._start_pinch()

    def finger_move(self, identifier, point):
        if identifier not in self.fingers:
            return
        contact = self.fingers[identifier]
        if len(self.fingers) == 1:
            self._drag(contact, point)
        else:
            contact.position = point
            # Freeze while >2 fingers are down; rebase when returning to two.
            if len(self.fingers) == 2:
                midpoint, distance = self._pinch_geometry()
                if self.pinch is None:
                    self._start_pinch()
                elif distance > 0:
                    initial_distance, zoom, world = self.pinch
                    self.camera.set_zoom(zoom * distance / initial_distance)
                    self.camera.anchor(world, self.drawable(midpoint))

    def finger_up(self, identifier, point):
        if identifier not in self.fingers:
            return
        self.finger_move(identifier, point)
        contact = self.fingers.pop(identifier)
        if not self.multitouch and not contact.dragged:
            self.selected = self.pick(point)
        if not self.fingers:
            self.multitouch = False
        self._start_pinch()
