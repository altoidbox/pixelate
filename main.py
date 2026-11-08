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


def with_lock(func):
    def _func_with_lock(*args, **kwargs):
        nonlocal func
        with args[0].lock:
            func(*args, **kwargs)
    _func_with_lock.__name__ = func.__name__
    return _func_with_lock


class Pixelate:
    def __init__(self, width=64):
        pygame.init()
        self.lock = threading.RLock()
        self.clock = pygame.time.Clock()

        pygame.display.init()
        screen_width, screen_height = pygame.display.get_desktop_sizes()[0]

        self.width = width
        self.pixel_width = screen_width // self.width
        self.height = screen_height // self.pixel_width
        self.rect = pygame.Rect(0, 0, self.width, self.height)

        print(f"Displ size: {screen_width}x{screen_height}")
        print(f"Pixel disp: {self.width}x{self.height}")
        print(f"Pixel size: {self.pixel_width}x{self.pixel_width}")
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

        self.screen = pygame.display.set_mode(size=(screen_width, screen_height), flags=pygame.FULLSCREEN | pygame.SCALED)  # | pygame.NOFRAME
        self.running = True

    @staticmethod
    def is_quit_event(event: pygame.event.Event):
        if event.type == pygame.QUIT:
            return True
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_q, pygame.K_ESCAPE):
                return True
        return False

    def eventloop(self):
        self.running = True
        while self.running:
            self.clock.tick(30)
            event = pygame.event.wait()
            while event.type != pygame.NOEVENT:
                if self.is_quit_event(event):
                    self.running = False
                else:
                    yield event
                event = pygame.event.poll()
            self.paint()
        pygame.quit()

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
    def draw_surface(self, coord, surface: Surface, layer=1):
        x, y = coord
        surface.lock()
        for point in iter_rect(surface.get_rect()):
            color = surface.get_at(point)
            if color == surface.get_colorkey() or color.a == 0:
                continue
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
    def paint(self):
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
            pygame.draw.rect(self.screen, self.background[y][x], coord)
            self.screen.blit(pixel, coord)
        pygame.display.flip()


class ClockApp:
    def __init__(self, pxl8: Pixelate):
        self.pxl8 = pxl8
        self.fonts = text.get_fonts()
        self.font_index = 0
        self.font = text.get_font('PressStart2P-Regular.ttf', 8)
        self.text_color = WHITE
        self.shadow_color = pygame.Color(80, 80, 80, 180)
        self.alignment = (Alignment.RIGHT, Alignment.BOTTOM)
        if os.path.exists("mountain-cabin.png"):
            pxl8.draw_surface((0, 0), pygame.image.load("mountain-cabin.png"), layer=0)
    
    def align(self, alignment, rect: pygame.Rect, padding=0, offset=(0, 0), rel_to=None):
        if rel_to is None:
            rel_to = self.pxl8.rect
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
        return rect.move(offset)

    def render_text(self, msg) -> pygame.Surface:
        surf = text.text_shadow(self.font, msg, self.text_color, self.shadow_color)
        r = surf.get_rect()
        r.inflate_ip((-1, 0))
        return surf.subsurface(r)

    def draw_time(self):
        curtime = time.localtime()
        dateline = self.render_text(time.strftime("%e %b", curtime).strip())
        hour = self.render_text(time.strftime("%I", curtime).lstrip('0'))
        colon = self.render_text(':')
        minutes = self.render_text(time.strftime("%M", curtime))
        ampm = self.render_text(time.strftime("%p", curtime).lower())
        size = (hour.get_width() + colon.get_width()*2 + minutes.get_width() + ampm.get_width(), hour.get_height())
        timeline = pygame.Surface(size, pygame.SRCALPHA)
        timeline.fill(CLEAR)
        timeline.blit(hour, (0, 0))
        offset = hour.get_width()
        if curtime.tm_sec % 2 == 0:
            timeline.blit(colon, (offset, 0))
        offset += colon.get_width()
        timeline.blit(minutes, (offset, 0))
        offset += minutes.get_width() + colon.get_width()
        timeline.blit(ampm, (offset, 0))
        dlbounds = dateline.get_bounding_rect()
        tlbounds = timeline.get_bounding_rect()
        dateline2 = dateline.subsurface(dlbounds)
        timeline2 = timeline.subsurface(tlbounds)
        combined = pygame.Surface((max(dateline2.get_width(), timeline2.get_width()), dlbounds.height + tlbounds.height + 1), pygame.SRCALPHA)
        combined_rect = combined.get_rect()
        combined.fill(CLEAR)
        rect = self.align((self.alignment[0], Alignment.TOP), dlbounds, offset=(0, 0), rel_to=combined_rect)
        combined.blit(dateline2, rect.topleft)
        rect = self.align((self.alignment[0], Alignment.TOP), tlbounds, offset=(0, dlbounds.height + 1), rel_to=combined_rect)
        combined.blit(timeline2, rect.topleft)
        return combined

    def update_time(self, event=None):
        self.pxl8.fill(self.pxl8.rect, CLEAR)
        surface = self.draw_time2()
        rect = self.align(self.alignment, surface.get_rect(), padding=1)
        self.pxl8.draw_surface(rect.topleft, surface)

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
        self.update_time()

    def mouse_down(self, event: pygame.event.Event):
        # translate mouse position to pixel grid position
        x, y = event.pos
        x = x // self.pxl8.pixel_width
        y = y // self.pxl8.pixel_width
        if event.button == 1:
            self.pxl8.style[y][x] = RoundPixel(self.pxl8.pixel_width)
        else:
            self.pxl8.style[y][x] = SquarePixel(self.pxl8.pixel_width)
        self.pxl8.dirty.add((x, y))
        pass

    def run(self):
        pygame.event.set_allowed([pygame.USEREVENT, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN, pygame.QUIT])
        self.update_time()
        pygame.time.set_timer(pygame.USEREVENT, 1000)
        event_map = {
            pygame.USEREVENT: self.update_time,
            pygame.KEYDOWN: self.key_press,
            pygame.MOUSEBUTTONDOWN: self.mouse_down,
        }
        for event in self.pxl8.eventloop():
            handler = event_map.get(event.type, None)
            if handler is not None:
                handler(event)


def main():
    ClockApp(Pixelate()).run()
    exit()


if __name__ == "__main__":
    main()
    pygame.examples.alien()