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
    LEFT = -1
    RIGHT = 1
    # Y align
    TOP = -1
    BOTTOM = 1
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
        loc = align_surface((Alignment.LEFT, yalignment), surf, rel_to=full_rect, offset=(x, 0))
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
        loc = align_surface((xalignment, Alignment.TOP), surf, rel_to=full_rect, offset=(0, y))
        full_surface.blit(surf, loc.topleft)
        y += surf.get_height() + ypadding
    return full_surface


def prepare_surface(lines, xalignment=Alignment.LEFT):
    surf_lines = [join_horizontal(line) for line in lines]
    return join_vertical(surf_lines, xalignment)


def align_surface(alignment, rect: pygame.Rect|pygame.Surface, rel_to: pygame.Rect|pygame.Surface, padding=0, offset=(0, 0)):
    if isinstance(rel_to, pygame.Surface):
        rel_to = rel_to.get_rect()
    if isinstance(rect, pygame.Surface):
        rect = rect.get_rect()
    else:
        rect = rect.copy()
    if padding:
        rel_to = rel_to.inflate(-2*padding, -2*padding)
    match alignment:
        case (Alignment.LEFT, Alignment.TOP):
            rect.topleft = rel_to.topleft
        case (Alignment.LEFT, Alignment.CENTER):
            rect.midleft = rel_to.midleft
        case (Alignment.LEFT, Alignment.BOTTOM):
            rect.bottomleft = rel_to.bottomleft
        case (Alignment.RIGHT, Alignment.TOP):
            rect.topright = rel_to.topright
        case (Alignment.RIGHT, Alignment.CENTER):
            rect.midright = rel_to.midright
        case (Alignment.RIGHT, Alignment.BOTTOM):
            rect.bottomright = rel_to.bottomright
        case (Alignment.CENTER, Alignment.TOP):
            rect.midtop = rel_to.midtop
        case (Alignment.CENTER, Alignment.CENTER):
            rect.center = rel_to.center
        case (Alignment.CENTER, Alignment.BOTTOM):
            rect.midbottom = rel_to.midbottom
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

    def switch_app(self, app: 'PixelateApp'):
        if app is self.active_app:
            return
        if self.active_app is not None:
            self.active_app.deactivate()
        if app not in self.apps:
            self.apps.add(app)
        self.active_app = app
        pygame.event.set_blocked(None)
        pygame.event.set_allowed(self.REQUIRED_EVENTS)
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
        """
        pass

    def close(self):
        """
        Called when the app is closed.
        """
        pass


class ClockApp(PixelateApp):
    def __init__(self, pxl8: Pixelate):
        super().__init__(pxl8)
        self.pxl8 = pxl8
        self.display = pxl8.create_display(self)
        self.fonts = text.get_fonts()
        self.font_index = 0
        self.font = text.get_font('PressStart2P-Regular.ttf', 8)
        self.text_color = WHITE
        self.shadow_color = pygame.Color(80, 80, 80, 180)
        self.alignment = (Alignment.RIGHT, Alignment.BOTTOM)
        self.surfaces = [None, None]
        self.surface_time = None
        self.surface_index = 0
        self.timer_event = pygame.event.custom_type()
        self.event_map = {
            self.timer_event: self.update_time,
            pygame.KEYDOWN: self.key_press,
            pygame.MOUSEBUTTONDOWN: self.mouse_down,
        }
        if os.path.exists("mountain-cabin.png"):
            self.display.draw_surface((0, 0), pygame.image.load("mountain-cabin.png"), layer=0)

    def activate(self):
        self.pxl8.active_display = self.display
        pygame.event.set_allowed([self.timer_event, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN])
        self.update_time(force=True)
        pygame.time.set_timer(self.timer_event, 1000)

    def deactivate(self):
        pygame.time.set_timer(self.timer_event, 0)

    def render_text(self, msg) -> pygame.Surface:
        surf = text.text_shadow(self.font, msg, self.text_color, self.shadow_color)
        r = surf.get_rect()
        r.inflate_ip((-1, 0))
        return surf.subsurface(r)

    def draw_time(self, curtime):
        dateline = self.render_text(time.strftime("%e %b", curtime).strip())
        hour = self.render_text(time.strftime("%I", curtime).lstrip('0'))
        colon = self.render_text(':')
        blank = pygame.Surface((colon.get_width(), hour.get_height()), pygame.SRCALPHA)
        blank.fill(CLEAR)
        minutes = self.render_text(time.strftime("%M", curtime))
        ampm = self.render_text(time.strftime("%p", curtime).lower())
        with_colon = join_horizontal([hour, colon, minutes, blank, ampm])
        without_colon = join_horizontal([hour, blank, minutes, blank, ampm])
        dlbounds = dateline.get_bounding_rect()
        dateline = dateline.subsurface(dlbounds)
        surfaces = []
        for timeline in [with_colon, without_colon]:
            tlbounds = timeline.get_bounding_rect()
            timeline = timeline.subsurface(tlbounds)
            surfaces.append(join_vertical([dateline, timeline], xalignment=self.alignment[0], ypadding=1))
        return surfaces

    def update_time(self, event=None, force=False):
        curtime = time.localtime()
        if force or self.surface_time != curtime[1:5]:
            self.display.fill(self.display.rect, CLEAR)
            self.surfaces = self.draw_time(curtime)
            self.surface_time = curtime[1:5]
        if event is not None and event.type == self.timer_event:
            self.surface_index = (self.surface_index + 1) % len(self.surfaces)
        surface = self.surfaces[self.surface_index]
        rect = align_surface(self.alignment, surface, rel_to=self.display.rect, padding=1)
        self.display.draw_surface(rect.topleft, surface, ignore_clear=False)

    def key_press(self, event):
        if event.key == pygame.K_j:
            self.font_index = (self.font_index + 1) % len(self.fonts)
            self.font = text.get_font(*self.fonts[self.font_index])
        elif event.key == pygame.K_k:
            self.font_index = (self.font_index - 1) % len(self.fonts)
            self.font = text.get_font(*self.fonts[self.font_index])
        elif event.key == pygame.K_u:
            self.font = self.font.with_size(self.font.point_size + 1)
        elif event.key == pygame.K_i:
            self.font = self.font.with_size(self.font.point_size - 1)
        elif event.key == pygame.K_UP:
            self.alignment = (self.alignment[0], max(self.alignment[1] - 1, Alignment.TOP))
        elif event.key == pygame.K_DOWN:
            self.alignment = (self.alignment[0], min(self.alignment[1] + 1, Alignment.BOTTOM))
        elif event.key == pygame.K_LEFT:
            self.alignment = (max(self.alignment[0] - 1, Alignment.LEFT), self.alignment[1])
        elif event.key == pygame.K_RIGHT:
            self.alignment = (min(self.alignment[0] + 1, Alignment.RIGHT), self.alignment[1])
        else:
            return
        print(self.font.name, 's:', self.font.point_size, 'h:', self.font.get_height(), 'l:', self.font.get_linesize(), 'a:', self.font.get_ascent(), 'd:', self.font.get_descent())
        self.update_time(force=True)

    def mouse_down(self, event: pygame.event.Event):
        # translate mouse position to pixel grid position
        x, y = event.pos
        x = x // self.display.pixel_width
        y = y // self.display.pixel_width
        print('Mouse:', event.button, '@', (x, y))
        style = self.display.styles[0]
        if self.display.style[y][x] == style:
            style = self.display.styles[1]
        self.display.set_color((x, y), style, layer=2)

    def handle_event(self, event: pygame.event.Event):
        handler = self.event_map.get(event.type, None)
        if handler is not None:
            handler(event)

    def run(self):
        pygame.event.set_allowed([self.timer_event, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN, pygame.QUIT])
        self.update_time(force=True)
        pygame.time.set_timer(self.timer_event, 1000)
        event_map = {
            self.timer_event: self.update_time,
            pygame.KEYDOWN: self.key_press,
            pygame.MOUSEBUTTONDOWN: self.mouse_down,
        }
        for event in self.pxl8.eventloop():
            handler = event_map.get(event.type, None)
            if handler is not None:
                handler(event)


def main():
    pxl8 = Pixelate()
    pxl8.switch_app(ClockApp(pxl8))
    pxl8.eventloop()
    exit()


if __name__ == "__main__":
    main()
    pygame.examples.alien()