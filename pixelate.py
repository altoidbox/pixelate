#!/usr/bin/env python3
import pygame
import time
import os
import threading
from pygame import Surface
import text


CLEAR = pygame.Color(0, 0, 0, 0)
WHITE = pygame.Color(255, 255, 255, 255)


class Alignment:
    # X align
    LEFT = -2
    MIDLEFT = -1
    MIDRIGHT = 1
    RIGHT = 2
    # Y align
    TOP = -2
    MIDTOP = -1
    MIDBOTTOM = 1
    BOTTOM = 2
    # X or Y align
    CENTER = 0


class SquarePixel:
    def __init__(self, size):
        self.size = size
        self.inner_border_color = pygame.Color(40, 40, 40)
        self.outer_border_color = pygame.Color(0, 0, 0)

    def render(self, color, background):
        surface = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        surface.fill(background)
        pygame.draw.rect(surface, color, (2, 2, self.size - 3, self.size - 3))
        pygame.draw.rect(surface, self.inner_border_color, (1, 1, self.size - 2, self.size - 2), width=1)
        pygame.draw.rect(surface, self.outer_border_color, (0, 0, self.size, self.size), width=1)
        return surface


class RoundPixel:
    def __init__(self, size):
        self.size = size
        self.inner_border_color = pygame.Color(40, 40, 40)
        self.outer_border_color = pygame.Color(0, 0, 0)

    def render(self, color, background):
        surface = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        surface.fill(background)
        pygame.draw.circle(surface, color, (self.size // 2, self.size // 2), self.size // 2 - 2)
        pygame.draw.circle(surface, self.inner_border_color, (self.size // 2, self.size // 2), self.size // 2 - 1, width=1)
        pygame.draw.circle(surface, self.outer_border_color, (self.size // 2, self.size // 2), self.size // 2, width=1)
        return surface


def iter_rect(rect: pygame.Rect):
    return ((x, y) for x in range(rect.left, rect.right) for y in range(rect.top, rect.bottom))


def join_horizontal(surfaces, yalignment=Alignment.TOP, xpadding=0):
    if len(surfaces) == 1:
        return surfaces[0]
    width = sum(surf.get_width() for surf in surfaces) + (xpadding * (len(surfaces) - 1))
    height = max(surf.get_height() for surf in surfaces)
    full_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    full_surface.fill(CLEAR)
    full_rect = full_surface.get_rect()
    x = 0
    for surf in surfaces:
        loc = align_surface(surf, rel_to=full_rect, yalign=yalignment, offset=(x, 0))
        full_surface.blit(surf, loc.topleft)
        x += surf.get_width() + xpadding
    return full_surface


def join_vertical(surfaces, xalignment=Alignment.LEFT, ypadding=0):
    if len(surfaces) == 1:
        return surfaces[0]
    width = max(surf.get_width() for surf in surfaces)
    height = sum(surf.get_height() for surf in surfaces) + (ypadding * (len(surfaces) - 1))
    full_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    full_surface.fill(CLEAR)
    full_rect = full_surface.get_rect()
    y = 0
    for surf in surfaces:
        loc = align_surface(surf, rel_to=full_rect, xalign=xalignment, offset=(0, y))
        full_surface.blit(surf, loc.topleft)
        y += surf.get_height() + ypadding
    return full_surface


def prepare_surface(lines, xalignment=Alignment.LEFT):
    surf_lines = [join_horizontal(line) for line in lines]
    return join_vertical(surf_lines, xalignment)


def align_surface(rect: pygame.Rect|pygame.Surface, rel_to: pygame.Rect|pygame.Surface, xalign=None, yalign=None, padding=0, offset=None):
    if isinstance(rel_to, pygame.Surface):
        rel_to = rel_to.get_rect()
    if isinstance(rect, pygame.Surface):
        rect = rect.get_rect()
    else:
        rect = rect.copy()
    if padding:
        rel_to = rel_to.inflate(-2*padding, -2*padding)
    match xalign:
        case Alignment.LEFT:
            rect.left = rel_to.left
        case Alignment.MIDLEFT:
            within = rel_to.width - rect.width
            rect.left = rel_to.left + within // 4
        case Alignment.CENTER:
            rect.centerx = rel_to.centerx
        case Alignment.MIDRIGHT:
            within = rel_to.width - rect.width
            rect.right = rel_to.right - within // 4
        case Alignment.RIGHT:
            rect.right = rel_to.right
    match yalign:
        case Alignment.TOP:
            rect.top = rel_to.top
        case Alignment.MIDTOP:
            within = rel_to.height - rect.height
            rect.top = rel_to.top + within // 4
        case Alignment.CENTER:
            rect.centery = rel_to.centery
        case Alignment.MIDBOTTOM:
            within = rel_to.height - rect.height
            rect.bottom = rel_to.bottom - within // 4
        case Alignment.BOTTOM:
            rect.bottom = rel_to.bottom
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
        self.apps = set()
        self.displays = {}
        self.next_display_id = 0
        self.active_display = self.create_display(self)
        self.active_app: PixelateApp = None
        print(f"Displ size: {self.screen_width}x{self.screen_height}")
        print(f"Pixel disp: {self.active_display.width}x{self.active_display.height}")
        print(f"Pixel size: {self.active_display.pixel_width}x{self.active_display.pixel_width}")
        self.running = False
        self.screen = pygame.display.set_mode(size=(self.screen_width, self.screen_height), flags=pygame.FULLSCREEN | pygame.SCALED)  # | pygame.NOFRAME
        self.switch_app(PixelateApp(self))

    def create_display(self, owner, preferred_width=None, preferred_height=None):
        if preferred_width is None and preferred_height is None:
            preferred_width = self.preferred_width
            preferred_height = self.preferred_height
        ident = self.next_display_id
        self.next_display_id += 1
        new_display = PixelateDisplay(owner, ident, self.screen_width, self.screen_height, preferred_width, preferred_height)
        self.displays[ident] = new_display
        return new_display

    @staticmethod
    def is_quit_event(event: pygame.event.Event):
        if event.type == pygame.QUIT:
            return True
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_q, pygame.K_ESCAPE):
                return True
        return False

    def start_app(self, app: 'PixelateApp', activate=False):
        self.apps.add(app)
        app.start()
        if activate:
            self.switch_app(app)

    def switch_app(self, app: 'PixelateApp'):
        if app is self.active_app:
            return
        pygame.event.set_blocked(None)
        pygame.event.set_allowed(self.REQUIRED_EVENTS)
        if self.active_app is not None:
            self.active_app.deactivate()
        self.active_app = app
        self.active_app.activate()

    def eventloop(self):
        self.running = True
        while self.running:
            self.clock.tick(30)
            event = pygame.event.wait()
            while event.type != pygame.NOEVENT:
                if self.is_quit_event(event):
                    self.running = False
                else:
                    self.active_app.handle_event(event)
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
        if self.layers[layer][y][x] == color:
            return
        self.layers[layer][y][x] = color
        self.dirty.add(coord)

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
