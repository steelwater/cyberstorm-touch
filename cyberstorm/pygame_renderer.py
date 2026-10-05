"""The sole pygame/SDL boundary: upload, drawing, window and input events."""

import pygame
from pygame._sdl2.video import Renderer, Texture

from .scene import number
from .viewport import Timeline, Viewport


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
        self.zoom = 1.0
        self.integer = True
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

    def events(self):
        for event in pygame.event.get():
            if event.type in (pygame.QUIT, pygame.WINDOWCLOSE):
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    self.zoom = min(4.0, self.zoom * 2)
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    self.zoom = max(0.25, self.zoom / 2)
                elif event.key == pygame.K_0:
                    self.zoom = 1.0
                elif event.key == pygame.K_i:
                    self.integer = not self.integer
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

    def draw(self):
        # Reset to the complete drawable after resize. Do not use logical window
        # points as framebuffer pixels, or retain SDL's old logical-size viewport.
        self.renderer.set_viewport(None)
        output = self.renderer.get_viewport()
        if output.width < 1 or output.height < 1:
            return None  # Minimized windows can temporarily have no drawable.
        view = Viewport.fit(output.size, self.scene.reference, self.scene.center,
                            self.zoom, self.integer)
        self.renderer.draw_color = (19, 24, 30, 255)
        self.renderer.clear()
        if self.terrain_texture is not None:
            texture = self.terrain_texture
            rectangle = view.rectangle((0, 0), (0, 0), (texture.width, texture.height))
            texture.draw(dstrect=rectangle)
        if self.grid:
            self.renderer.draw_color = (74, 83, 73, 255)
            for outline in self.scene.outlines:
                points = [tuple(round(v) for v in view.screen(p)) for p in outline]
                for i in range(len(points)):
                    self.renderer.draw_line(points[i - 1], points[i])
        for item in self.scene.objects:
            self._draw_item(item, view)
        self.window.title = (f'{self.scene.title} | {view.scale:.2f}x '
                             f'{"integer" if self.integer else "fractional"} | '
                             f'{"paused" if self.timeline.paused else "diagnostic playback"}')
        return view

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
