"""The sole pygame/SDL boundary: upload, drawing, window and input events."""

import pygame
from pygame._sdl2.video import Renderer, Texture

from .camera import Camera
from .navigation import Navigation
from .scene import number
from .viewport import Timeline


def image_surface(image, palette, key=None):
    """Resolve palette indices before upload; transparency is explicit per asset."""
    if len(palette) != 256 or any(len(c) != 3 or any(type(v) is not int or not 0 <= v <= 255 for v in c)
                                  for c in palette):
        raise ValueError('expected 256 RGB palette entries')
    if key is not None:
        number(key, 'transparency index', 0, 255, integer=True)
    colors = tuple(bytes((*rgb, 0 if i == key else 255)) for i, rgb in enumerate(palette))
    rgba = b''.join(colors[index] for index in image.pixels)
    return pygame.image.frombytes(rgba, (image.width, image.height), 'RGBA')


class BattlefieldWindow:
    def __init__(self, scene, size=(1024, 768), *, hidden=False, software=False):
        self.scene = scene
        self.window = None
        self.textures = {}
        self.terrain_texture = None
        self.timeline = Timeline()
        self.camera = Camera(scene.reference, scene.center, scene.hexmap.bounds, size)
        self.navigation = Navigation(self.camera, scene.hexmap, size)
        self.grid = True
        self.fullscreen = False
        self.running = True
        pygame.display.init()
        try:
            self.window = pygame.Window(scene.title, size=size, resizable=True,
                                        allow_high_dpi=True, hidden=hidden)
            self.renderer = Renderer(self.window, accelerated=0 if software else -1, vsync=False)
            for name, asset in scene.assets.items():
                uploaded = []
                for frame in asset.frames:
                    surface = image_surface(frame.image, frame.palette, asset.key)
                    texture = Texture(self.renderer, surface.get_size(), scale_quality=0)
                    texture.update(surface)
                    texture.blend_mode = pygame.BLENDMODE_BLEND
                    uploaded.append(texture)
                self.textures[name] = uploaded
            if scene.terrain:
                # Sample the joined hex coverage once when scaling. Scaling each
                # transparent tile separately leaves one-pixel cracks at fractional
                # zoom because adjacent masks round on different source grids.
                width = max(item.position[0] + 64 for item in scene.terrain)
                height = max(item.position[1] + 64 for item in scene.terrain)
                if width > 4096 or height > 4096:
                    raise ValueError('terrain composite exceeds 4096 pixels per axis')
                ground = pygame.Surface((width, height), pygame.SRCALPHA)
                surfaces = {}
                for item in scene.terrain:
                    key = (item.asset, item.frame)
                    if key not in surfaces:
                        asset = scene.assets[item.asset]
                        frame = asset.frames[item.frame]
                        surfaces[key] = image_surface(frame.image, frame.palette, asset.key)
                    ground.blit(surfaces[key], item.position)
                self.terrain_texture = Texture(self.renderer, ground.get_size(), scale_quality=0)
                self.terrain_texture.update(ground)
                self.terrain_texture.blend_mode = pygame.BLENDMODE_BLEND
        except BaseException:
            self.close()
            raise

    def close(self):
        self.textures.clear()
        self.terrain_texture = None
        # Release SDL resources while their owner window still exists.
        self.renderer = None
        if self.window is not None:
            self.window.destroy()
            self.window = None
        pygame.display.quit()

    def _sync_size(self):
        self.renderer.set_viewport(None)
        output = self.renderer.get_viewport()
        if min(output.size) < 1 or min(self.window.size) < 1:
            self.navigation.cancel()
            return False
        self.navigation.resize(self.window.size, output.size)
        return True

    def events(self):
        self._sync_size()
        for event in pygame.event.get():
            if event.type in (pygame.QUIT, pygame.WINDOWCLOSE):
                self.running = False
            elif event.type in (pygame.WINDOWFOCUSLOST, pygame.WINDOWLEAVE,
                                pygame.WINDOWMINIMIZED):
                self.navigation.cancel()
            elif event.type in (pygame.WINDOWSIZECHANGED, pygame.WINDOWRESIZED):
                self._sync_size()
            elif event.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
                point = (event.x * self.window.size[0], event.y * self.window.size[1])
                identifier = (event.touch_id, event.finger_id)
                action = {pygame.FINGERDOWN: self.navigation.finger_down,
                          pygame.FINGERMOTION: self.navigation.finger_move,
                          pygame.FINGERUP: self.navigation.finger_up}[event.type]
                action(identifier, point)
            elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP,
                                pygame.MOUSEMOTION, pygame.MOUSEWHEEL):
                # SDL can synthesize mouse events from fingers. Process them once.
                if event.touch:
                    continue
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.navigation.mouse_down(event.button, event.pos)
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.navigation.mouse_up(event.button, event.pos)
                elif event.type == pygame.MOUSEMOTION:
                    self.navigation.mouse_move(event.pos)
                else:
                    point = event.pos if event.pos is not None else pygame.mouse.get_pos()
                    self.navigation.wheel(event.precise_y, point)
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS,
                                 pygame.K_MINUS, pygame.K_KP_MINUS, pygame.K_0, pygame.K_i):
                    self.navigation.cancel()
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    self.camera.set_zoom(self.camera.zoom * 2)
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    self.camera.set_zoom(self.camera.zoom / 2)
                elif event.key == pygame.K_0:
                    self.camera.set_zoom(1.0)
                elif event.key == pygame.K_i:
                    self.camera.toggle_integer()
                elif event.key == pygame.K_g:
                    self.grid = not self.grid
                elif event.key == pygame.K_SPACE:
                    self.timeline.paused = not self.timeline.paused
                elif event.key == pygame.K_f:
                    if self.fullscreen:
                        self.window.set_windowed()
                    else:
                        self.window.set_fullscreen(desktop=True)
                    self.fullscreen = not self.fullscreen
                    self.navigation.cancel()
                    self._sync_size()

    def draw(self):
        if not self._sync_size():
            return None
        view = self.camera.view
        self.renderer.draw_color = (19, 24, 30, 255)
        self.renderer.clear()
        if self.terrain_texture is not None:
            texture = self.terrain_texture
            rectangle = view.rectangle((0, 0), (0, 0), (texture.width, texture.height))
            texture.draw(dstrect=rectangle)
        if self.grid:
            self.renderer.draw_color = (74, 83, 73, 255)
            for cell in sorted(self.scene.hexmap.cells):
                self._draw_outline(cell, view)
        for item in self.scene.objects:
            self._draw_item(item, view)
        for cell, color in ((self.navigation.hover, (115, 205, 245, 255)),
                            (self.navigation.selected, (255, 225, 75, 255))):
            if cell is not None:
                self.renderer.draw_color = color
                self._draw_outline(cell, view)
        selected = self.navigation.selected
        selection = f'{selected.column},{selected.row}' if selected is not None else 'none'
        self.window.title = (f'{self.scene.title} | {view.scale:.2f}x '
                             f'{"integer" if self.camera.integer else "fractional"} | '
                             f'{"paused" if self.timeline.paused else "diagnostic playback"} | hex {selection}')
        return view

    def _draw_outline(self, cell, view):
        points = [tuple(round(v) for v in view.screen(p)) for p in cell.outline]
        for i in range(len(points)):
            self.renderer.draw_line(points[i - 1], points[i])

    def _draw_item(self, item, view):
        asset = self.scene.assets[item.asset]
        index = item.frame if item.frame is not None else self.timeline.frame(len(asset.frames), asset.fps)
        image = asset.frames[index].image
        rectangle = view.rectangle(item.position, asset.anchor, (image.width, image.height))
        x, y, w, h = rectangle
        if w > 0 and h > 0 and x < view.width and y < view.height and x + w > 0 and y + h > 0:
            self.textures[item.asset][index].draw(dstrect=rectangle)

    def run(self, max_frames=None):
        clock = pygame.time.Clock()
        count = 0
        try:
            while self.running and (max_frames is None or count < max_frames):
                delta = clock.tick(60) / 1000
                self.events()
                self.timeline.advance(delta)
                if self.draw() is not None:
                    self.renderer.present()
                count += 1
        finally:
            self.close()
