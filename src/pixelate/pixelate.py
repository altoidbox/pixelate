#!/usr/bin/env python3
import pygame
import threading
from pygame import Surface
import random
import logging
from dataclasses import dataclass
from .config import *


CLEAR = pygame.Color(0, 0, 0, 0)
WHITE = pygame.Color(255, 255, 255, 255)
LOGGER = logging.getLogger('pixelate')
LOGGER.setLevel('INFO')
LOGGER.addHandler(logging.StreamHandler())


@dataclass
class SquarePixel:
    size: int
    inner_border_color: pygame.Color = ColorConfig(default=(40, 40, 40))
    inner_border_size: int = 1
    outer_border_color: pygame.Color = ColorConfig(default=(0, 0, 0))
    outer_border_size: int = 1

    def render(self, color, background):
        surface = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        surface.fill(background)
        border_size = self.inner_border_size + self.outer_border_size
        pygame.draw.rect(surface, color, (border_size, border_size, self.size -
                         border_size * 2, self.size - border_size * 2))
        if self.inner_border_size > 0:
            pygame.draw.rect(surface, self.inner_border_color, (self.outer_border_size, self.outer_border_size,
                             self.size - self.outer_border_size * 2, self.size - self.outer_border_size * 2), width=self.inner_border_size)
        if self.outer_border_size > 0:
            pygame.draw.rect(surface, self.outer_border_color,
                             (0, 0, self.size, self.size), width=self.outer_border_size)
        return surface


@dataclass
class RoundPixel:
    size: int
    inner_border_color: pygame.Color = ColorConfig(default=(40, 40, 40))
    inner_border_size: int = 1
    outer_border_color: pygame.Color = ColorConfig(default=(0, 0, 0))
    outer_border_size: int = 1

    def render(self, color, background):
        surface = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        surface.fill(background)
        border_size = self.inner_border_size + self.outer_border_size
        pygame.draw.circle(surface, color, (self.size // 2, self.size // 2), self.size // 2 - border_size)
        if self.inner_border_size > 0:
            pygame.draw.circle(
                surface, self.inner_border_color, (self.size // 2, self.size // 2), self.size // 2 - self.outer_border_size, width=self.inner_border_size)
        if self.outer_border_size > 0:
            pygame.draw.circle(
                surface, self.outer_border_color, (self.size // 2, self.size // 2), self.size // 2, width=self.outer_border_size)
        return surface


def iter_rect(rect: pygame.Rect):
    return ((x, y) for x in range(rect.left, rect.right) for y in range(rect.top, rect.bottom))


def join_horizontal(surfaces, yalign=0, xpadding=0):
    if len(surfaces) == 1:
        return surfaces[0]
    width = sum(surf.get_width() for surf in surfaces) + (xpadding * (len(surfaces) - 1))
    height = max(surf.get_height() for surf in surfaces)
    full_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    full_surface.fill(CLEAR)
    full_rect = full_surface.get_rect()
    x = 0
    for surf in surfaces:
        loc = align_surface(surf, rel_to=full_rect, yalign=yalign, offset=(x, 0))
        full_surface.blit(surf, loc.topleft)
        x += surf.get_width() + xpadding
    return full_surface


def join_vertical(surfaces, xalign=0, ypadding=0):
    if len(surfaces) == 1:
        return surfaces[0]
    width = max(surf.get_width() for surf in surfaces)
    height = sum(surf.get_height() for surf in surfaces) + (ypadding * (len(surfaces) - 1))
    full_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    full_surface.fill(CLEAR)
    full_rect = full_surface.get_rect()
    y = 0
    for surf in surfaces:
        loc = align_surface(surf, rel_to=full_rect, xalign=xalign, offset=(0, y))
        full_surface.blit(surf, loc.topleft)
        y += surf.get_height() + ypadding
    return full_surface


def align_surface(rect: pygame.Rect | pygame.Surface, rel_to: pygame.Rect | pygame.Surface,
                  xalign: float | int = 0, yalign: float | int = 0, padding=0, offset=None):
    if isinstance(rel_to, pygame.Surface):
        rel_to = rel_to.get_rect()
    if isinstance(rect, pygame.Surface):
        rect = rect.get_rect()
    else:
        rect = rect.copy()
    if padding:
        rel_to = rel_to.inflate(-2*padding, -2*padding)
    within = rel_to.width - rect.width
    rect.left = rel_to.left + within * xalign / 100
    within = rel_to.height - rect.height
    rect.top = rel_to.top + within * yalign / 100
    if offset:
        rect.move_ip(offset)
    return rect


def align_surface_center(rect: pygame.Rect | pygame.Surface, rel_to: pygame.Rect | pygame.Surface,
                         xalign: float | int = 0, yalign: float | int = 0, padding=0, offset=None):
    if isinstance(rel_to, pygame.Surface):
        rel_to = rel_to.get_rect()
    if isinstance(rect, pygame.Surface):
        rect = rect.get_rect()
    else:
        rect = rect.copy()
    if padding:
        rel_to = rel_to.inflate(-2*padding, -2*padding)
    center = rel_to.width * (xalign / 100)
    rect.left = rel_to.left + center - rect.width / 2
    center = rel_to.height * (yalign / 100)
    rect.top = rel_to.top + center - rect.height / 2
    if offset:
        rect.move_ip(offset)
    return rect


def with_lock(func):
    def _func_with_lock(*args, **kwargs):
        nonlocal func
        with args[0].lock:
            func(*args, **kwargs)
    _func_with_lock.__name__ = func.__name__
    return _func_with_lock


class Pixelate:
    DEFAULT_WIDTH = 64
    REQUIRED_EVENTS = (pygame.KEYDOWN, pygame.QUIT)

    def __init__(self, preferred_width=None, preferred_height=None):
        self.lock = threading.RLock()
        pygame.init()
        pygame.display.init()
        self.screen_width, self.screen_height = pygame.display.get_desktop_sizes()[0]
        self.preferred_width = preferred_width
        self.preferred_height = preferred_height

        self.clock = pygame.time.Clock()
        self.effect = None
        self.apps = []
        self.displays = {}
        self.next_display_id = 0
        self.active_display = self.create_display(self)
        self.active_app: PixelateApp = None
        print(f"Displ size: {self.screen_width}x{self.screen_height}")
        print(f"Pixel disp: {self.active_display.width}x{self.active_display.height}")
        print(f"Pixel size: {self.active_display.pixel_width}x{self.active_display.pixel_width}")
        self.running = False
        self.screen = pygame.display.set_mode(size=(self.screen_width, self.screen_height),
                                              flags=pygame.FULLSCREEN | pygame.SCALED)  # | pygame.NOFRAME
        self.switch_app(PixelateApp(self))

    def create_display(self, owner, preferred_width=None, preferred_height=None):
        if preferred_width is None and preferred_height is None:
            preferred_width = self.preferred_width
            preferred_height = self.preferred_height
        ident = self.next_display_id
        self.next_display_id += 1
        new_display = PixelateDisplay(owner, ident, self.screen_width, self.screen_height,
                                      preferred_width, preferred_height)
        self.displays[ident] = new_display
        return new_display

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key in (pygame.K_q, pygame.K_ESCAPE)):
            self.running = False
            return True
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_a:
                app_index = self.apps.index(self.active_app)
                next_app = self.apps[(app_index + 1) % len(self.apps)]
                self.switch_app(next_app)
                return True
        return False

    def enable_effect(self, effect):
        self.effect = effect
        effect.start()
        effect.activate()

    def start_app(self, app: 'PixelateApp', activate=False):
        self.apps.append(app)
        app.start()
        if activate:
            self.switch_app(app)

    def switch_app(self, app: 'PixelateApp'):
        if app is self.active_app:
            return
        #pygame.event.set_blocked(None)
        #pygame.event.set_allowed(self.REQUIRED_EVENTS)
        if self.active_app is not None:
            self.active_app.deactivate()
        self.active_app = app
        self.active_app.activate()
        self.active_display.needs_redraw = True

    def eventloop(self):
        self.running = True
        while self.running:
            self.clock.tick(30)
            event = pygame.event.wait()
            while event.type != pygame.NOEVENT:
                if not self.handle_event(event):
                    self.active_app.handle_event(event)
                    if self.effect:
                        self.effect.handle_event(event)
                event = pygame.event.poll()
            self.active_display.paint(self.screen)
            pygame.display.flip()
        pygame.quit()


class PixelateDisplay:
    def __init__(self, owner, ident, screen_width, screen_height, preferred_width=None, preferred_height=None):
        self.owner = owner
        self.id = ident
        self.lock = threading.RLock()

        if preferred_width is None and preferred_height is None:
            preferred_width = Pixelate.DEFAULT_WIDTH

        if preferred_width is not None:
            self.width = preferred_width
            self.pixel_width = screen_width // self.width
            self.height = screen_height // self.pixel_width
        elif preferred_height is not None:
            self.height = preferred_height
            self.pixel_width = screen_height // self.height
            self.width = screen_width // self.pixel_width
        self.rect = pygame.Rect(0, 0, self.width, self.height)

        self.background = []
        self.foreground = []
        self.style = []
        self.dirty = set()
        self.needs_redraw = True
        self.layers = [self.background, self.foreground, self.style]
        self.styles = [SquarePixel(self.pixel_width), RoundPixel(self.pixel_width)]
        for y in range(self.height):
            y += 1
            self.background.append([pygame.Color(min(y*2, 255), min(y*5, 255), min(y*8, 255), 255)] * self.width)
            self.foreground.append([CLEAR] * self.width)
            self.style.append([self.styles[0]] * self.width)

    @with_lock
    def set_color(self, coord, color, layer=1):
        x, y = coord
        if layer < 0 or layer >= len(self.layers):
            return
        if not self.rect.collidepoint(coord):
            return
        old_color = self.layers[layer][y][x]
        if old_color == color:
            return old_color
        self.layers[layer][y][x] = color
        self.dirty.add(coord)
        return old_color

    @with_lock
    def draw_surface(self, coord, surface: Surface, layer=1, ignore_clear=True):
        x, y = coord
        surface.lock()
        for point in iter_rect(surface.get_rect()):
            color = surface.get_at(point)
            if color == surface.get_colorkey() or color.a == 0:
                if ignore_clear:
                    continue
                color = CLEAR
            self.set_color((point[0] + x, point[1] + y), color, layer)
        surface.unlock()

    @with_lock
    def style_surface(self, coord, surface: Surface, style):
        x, y = coord
        surface.lock()
        for point in iter_rect(surface.get_rect()):
            color = surface.get_at(point)
            if color == surface.get_colorkey() or color.a == 0:
                continue
            self.set_color((point[0] + x, point[1] + y), style, layer=2)
        surface.unlock()

    @with_lock
    def fill(self, rect: pygame.Rect, color, layer=1):
        for coord in iter_rect(rect):
            self.set_color(coord, color, layer)

    @with_lock
    def paint(self, screen: pygame.Surface):
        if self.needs_redraw:
            draw_set = iter_rect(pygame.Rect(0, 0, self.width, self.height))
        elif self.dirty:
            draw_set = self.dirty
        else:
            return
        self.dirty = set()
        self.needs_redraw = False
        for (x, y) in draw_set:
            coord = (x*self.pixel_width, y*self.pixel_width, self.pixel_width, self.pixel_width)
            pixel = self.style[y][x].render(self.foreground[y][x], (0, 0, 0))
            pygame.draw.rect(screen, self.background[y][x], coord)
            screen.blit(pixel, coord)


class PixelateApp:
    def __init__(self, pxl8: Pixelate):
        """
        Called when the app is created.
        You may want to register your app with the Pixelate instance here.
        """
        pass

    def activate(self):
        """
        Called when the app is placed into the foreground.
        """
        pass

    def deactivate(self):
        """
        Called when the app is placed into the background.
        The app may want to reduce CPU when in the background.
        e.g., a clock that blinks a cursor every second may just want to update its display each minute when in the background
        """
        pass

    def handle_event(self, event: pygame.event.Event):
        """
        Called when an event occurs.
        Most apps should be primarily event driven
        If needed, apps can create a new thread during 'start' and generate pygame events to be handled in the main loop
        @see pygame.event.post
        """
        pass

    def start(self):
        """
        Called when the app is started. Generally, this would be called after __init__ and before activate 
        to indicate that the app can beginning running.
        """
        pass

    def stop(self):
        """
        Called when the app is closed/stopped.
        The app should de-register any callbacks so it can cleanup nicely
        """
        pass


class ShimmerEffect(PixelateApp):
    class Pixel:
        def __init__(self, display, pixel, loc):
            self.display = display
            self.pixel = pixel
            self.state = 0
            self.loc = loc

        def render(self, color, background):
            surf: pygame.Surface = self.pixel.render(color, background)
            if self.display.foreground[self.loc[1]][self.loc[0]].a == 0:
                return surf
            if self.state == 1:
                flag = pygame.BLEND_RGB_ADD
            else:
                flag = pygame.BLEND_RGB_SUB
            surf.fill((50, 50, 50), special_flags=flag)
            return surf

    def __init__(self, pxl8: 'Pixelate'):
        self.pxl8 = pxl8
        self.timer_event = pygame.event.custom_type()
        self.display = None
        self.shimmering = []

    def activate(self):
        print('ShimmerEffect', 'activate')
        self.display = self.pxl8.active_display
        # pygame.time.set_timer(self.timer_event, random.randrange(2000, 20000))
        pygame.time.set_timer(self.timer_event, 2000)

    def deactivate(self):
        print('ShimmerEffect', 'deactivate')
        pygame.time.set_timer(self.timer_event, 0)
        for pixel in self.shimmering:
            self.restore_pixel(pixel)

    def add_pixel(self, x, y):
        if x >= self.display.width or y < 0:
            return
        pixel = ShimmerEffect.Pixel(self.display, self.display.style[y][x], (x, y))
        self.display.set_color(pixel.loc, pixel, layer=2)
        self.shimmering.append(pixel)

    def restore_pixel(self, pixel):
        self.display.set_color(pixel.loc, pixel.pixel, layer=2)

    def progress_pixel(self, pixel):
        x, y = pixel.loc
        if pixel.state == 0:
            self.add_pixel(x + 1, y)
            if x == 0:
                self.add_pixel(x, y - 1)
        pixel.state += 1
        if pixel.state >= 3:
            self.restore_pixel(pixel)
        else:
            self.shimmering.append(pixel)

    def handle_event(self, event):
        if event.type != self.timer_event:
            return
        if not self.shimmering:
            # start shimmering!
            pygame.time.set_timer(self.timer_event, 40)
            self.add_pixel(0, self.display.height - 1)
            return
        # Next iteration of shimmering
        # every pixel moves to the right
        # a new pixel is generated at x=0, y=y+1, if a pixel exists at x=0
        # pixels that go out of bounds are removed
        shimmering = self.shimmering
        self.shimmering = []
        for pixel in shimmering:
            self.progress_pixel(pixel)
        if len(self.shimmering) == 0:
            pygame.time.set_timer(self.timer_event, random.randrange(2000, 20000))
