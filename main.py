#!/usr/bin/env python3
import pygame
import time
import os
import threading
from pygame import Surface
import text


CLEAR = pygame.Color(0, 0, 0, 0)
WHITE = pygame.Color(255, 255, 255, 255)


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
    def __init__(self):
        pygame.init()
        self.lock = threading.RLock()
        self.clock = pygame.time.Clock()

        pygame.display.init()
        screen_width, screen_height = pygame.display.get_desktop_sizes()[0]

        self.width = 64
        self.pixel_width = screen_width // self.width
        self.height = screen_height // self.pixel_width
        self.rect = pygame.Rect(0, 0, self.width, self.height)

        print(f"Displ size: {screen_width}x{screen_height}")
        print(f"Pixel disp: {self.width}x{self.height}")
        print(f"Pixel size: {self.pixel_width}x{self.pixel_width}")
        self.background = []
        self.foreground = []
        self.dirty = set()
        self.needs_redraw = True
        self.layers = [self.background, self.foreground]
        for y in range(self.height):
            y += 1
            self.background.append([pygame.Color(min(y*2, 255), min(y*5, 255), min(y*8, 255), 255)] * self.width)
            self.foreground.append([CLEAR] * self.width)

        self.screen = pygame.display.set_mode(size=(screen_width, screen_height), flags=pygame.FULLSCREEN | pygame.SCALED)  # | pygame.NOFRAME
        pygame.event.set_grab(True)
        self.running = True

    @staticmethod
    def is_quit_event(event: pygame.event.Event):
        if event.type == pygame.QUIT:
            return True
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_q, pygame.K_ESCAPE):
                return True
        elif event.type == pygame.MOUSEBUTTONDOWN:
            return True
        return False

    def run(self):
        self.running = True
        while self.running:
            self.clock.tick(30)
            for event in pygame.event.get():
                if self.is_quit_event(event):
                    self.running = False
            self.paint()
        pygame.quit()

    @with_lock
    def set_color(self, coord, color, layer=1):
        x, y = coord
        if layer < 0 or layer >= len(self.layers):
            return
        if not self.rect.collidepoint(coord):
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
    def fill(self, rect: pygame.Rect, color, layer=1):
        for coord in iter_rect(rect):
            self.set_color(coord, color, layer)

    @with_lock
    def paint(self):
        px = SquarePixel(self.pixel_width)
        #px = RoundPixel(self.pixel_width)
        px.inner_border_color = px.outer_border_color
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
            pixel = px.render(self.foreground[y][x], (0, 0, 0))
            pygame.draw.rect(self.screen, self.background[y][x], coord)
            self.screen.blit(pixel, coord)
        pygame.display.flip()


def app(pxl8: Pixelate):
    try:
        if os.path.exists("mountain-cabin.png"):
            pxl8.draw_surface((0, 0), pygame.image.load("mountain-cabin.png"), layer=0)
        fonts = text.get_fonts()
        i = 0
        interval = 10
        while pxl8.running:
            if i % interval == 0:
                font = fonts[(i // interval) % len(fonts)]
            msg = time.strftime("%e %b")
            with pxl8.lock:
                pxl8.fill(pygame.Rect(0, 0, pxl8.width, pxl8.height), CLEAR)
                #line = text.text_shadows(font, msg, WHITE, pygame.Color(0, 0, 0, 127), offsets=[(0, 1), (1, 0), (0, -1), (-1, 0)])
                dateline = text.text_shadow(font, msg, WHITE, pygame.Color(80, 80, 80, 180))
                if i % 2 == 0:
                    msg = time.strftime("%I:%M %p").lower()
                else:
                    msg = time.strftime("%I %M %p").lower()
                if msg.startswith('0'):
                    msg = ' ' + msg[1:]
                timeline = text.text_shadow(font, msg, WHITE, pygame.Color(80, 80, 80, 180))
                overlay = pygame.Surface((pxl8.width, dateline.get_height() + timeline.get_height() + 2), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 80))
                x = 1
                y = pxl8.height - font.get_linesize() * 2 - 2
                #pxl8.draw_surface((0, y-1), overlay)
                pxl8.draw_surface((x, y), dateline)
                y += font.get_linesize() + 1
                pxl8.draw_surface((x, y), timeline)
            time.sleep(1)
            i += 1
    finally:
        pxl8.running = False


def main():
    p = Pixelate()
    t = threading.Thread(target=app, args=[p])
    t.start()
    p.run()
    t.join()
    exit()


if __name__ == "__main__":
    main()
