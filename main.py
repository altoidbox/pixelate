#!/usr/bin/env python3
import pygame
import time
import os
import ctypes
import threading
from pathlib import Path
from pygame import Surface


CLEAR = pygame.Color(0, 0, 0, 0)
WHITE = pygame.Color(255, 255, 255, 255)


def draw_shape(pxarray: pygame.PixelArray, shape, coord, color):
    x, y = coord
    #print(x, y, shape)
    for yoff in range(len(shape)):
        for xoff in range(len(shape[0])):
            if bool(shape[yoff][xoff]):
                pxarray[x + xoff, y + yoff] = color


class Font3x5(pygame.font.Font):
    CHR_WIDTH = 3
    CHR_HEIGHT = 5
    FONT = [
        0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000,
        0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000,
        0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000,
        0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000,
        0x0000, 0x2482, 0x5a00, 0x5f7d, 0x3cfa, 0x52a5, 0x3ceb, 0x2400,
        0x1491, 0x4494, 0x5540, 0x05d0, 0x0014, 0x01c0, 0x0002, 0x12a4,
        0x7b6f, 0x2c97, 0x62a7, 0x628e, 0x1779, 0x798e, 0x79ef, 0x72a4,
        0x7bef, 0x7bcf, 0x0410, 0x0414, 0x1511, 0x0e38, 0x4454, 0x72c2,
        0x2b63, 0x2bed, 0x6bae, 0x3923, 0x6b6e, 0x79a7, 0x79a4, 0x396b,
        0x5bed, 0x7497, 0x126a, 0x5bad, 0x4927, 0x5fed, 0x5ffd, 0x2b6a,
        0x6ba4, 0x3b73, 0x6bad, 0x388e, 0x7492, 0x5b6f, 0x5b6a, 0x5bfd,
        0x5aad, 0x5a92, 0x72a7, 0x3493, 0x4889, 0x6496, 0x2a00, 0x0007,
        0x4400, 0x076b, 0x4d6e, 0x0723, 0x176b, 0x0573, 0x15d2, 0x07ce,
        0x49ad, 0x2092, 0x2094, 0x4bad, 0x2491, 0x0bed, 0x0d6d, 0x056a,
        0x0d74, 0x0759, 0x0564, 0x070e, 0x2691, 0x0b6b, 0x0b6a, 0x0b7d,
        0x0a95, 0x0aca, 0x0e67, 0x3513, 0x2492, 0x6456, 0x00f0, 0x0000
    ]
    shape_map = {}

    @classmethod
    def get_shape(cls, char):
        shape = cls.shape_map.get(char, None)
        if shape is not None:
            return shape
        val = ord(char)
        if val < 0x20 or val >= 0x7f:
            return None
        shape = []
        val = f'{cls.FONT[val]:015b}'
        for i in range(0, cls.CHR_WIDTH * cls.CHR_HEIGHT, cls.CHR_WIDTH):
            shape.append([int(j) for j in val[i:i + cls.CHR_WIDTH]])
        cls.shape_map[char] = shape
        return shape

    def size(self, text):
        fixed_width = -1
        for c in text:
            if self.get_shape(c) is None:
                continue
            fixed_width += self.CHR_WIDTH + 1
        if fixed_width < 0:
            return 0, 0
        return fixed_width, self.get_height()

    def get_height(self):
        return self.CHR_HEIGHT + (2 if self.underline else 0)

    def get_ascent(self):
        return self.CHR_HEIGHT

    def get_descent(self):
        return 2 if self.underline else 0

    def get_linesize(self):
        return self.get_height() + 2

    def render(self, text: str, antialias, color, background=None) -> Surface:
        fixed_width, fixed_height = self.size(text)
        canvas = Surface((fixed_width, fixed_height), flags=pygame.SRCALPHA)
        if fixed_width == 0:
            return canvas
        if not background:
            background = pygame.Color(0, 0, 0, 0)
        canvas.fill(background)
        x = -1
        y = 0
        with pygame.PixelArray(canvas) as pxarray:
            for c in text:
                shape = self.get_shape(c)
                if shape is None:
                    continue
                x += 1
                draw_shape(pxarray, shape, (x, y), color)
                x += self.CHR_WIDTH
        if self.underline:
            pygame.draw.line(canvas, color, (0, y + self.CHR_HEIGHT + 1), (fixed_width - 1, y + self.CHR_HEIGHT + 1), width=1)
        return canvas


class Font6x10(pygame.font.Font):
    CHR_WIDTH = 6
    CHR_HEIGHT = 10
    
    def __init__(self):
        super().__init__()
        self.source = Font3x5()

    def size(self, text):
        self.source.underline = self.underline
        w, h = self.source.size(text)
        return w * 2, h * 2

    def get_height(self):
        return self.CHR_HEIGHT

    def get_ascent(self):
        return self.CHR_HEIGHT

    def get_descent(self):
        return 4 if self.underline else 0

    def get_linesize(self):
        return self.get_height() + 2

    def render(self, text: str, antialias, color, background=None) -> Surface:
        self.source.underline = self.underline
        surface = self.source.render(text, antialias, color, background)
        return pygame.transform.scale_by(surface, 2)


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

        print(f"Displ size: {screen_width}x{screen_height}")
        print(f"Pixel disp: {self.width}x{self.height}")
        print(f"Pixel size: {self.pixel_width}x{self.pixel_width}")
        self.background = []
        self.foreground = []
        self.layers = [self.background, self.foreground]
        for y in range(self.height):
            y += 1
            self.background.append([pygame.Color(min(y*2, 255), min(y*5, 255), min(y*8, 255), 255)] * self.width)
            self.foreground.append([CLEAR] * self.width)

        self.screen = pygame.display.set_mode(size=(screen_width, screen_height), flags=pygame.FULLSCREEN | pygame.SCALED)  # | pygame.NOFRAME
        pygame.event.set_grab(True)
        self.running = True

    def run(self):
        self.running = True
        while self.running:
            self.clock.tick(30)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_q, pygame.K_ESCAPE):
                        self.running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.running = False
            self.paint()
        pygame.quit()

    def set_color(self, x, y, color, layer=1):
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return
        if layer < 0 or layer >= len(self.layers):
            return
        self.layers[layer][y][x] = color

    @with_lock
    def draw_surface(self, coord, surface: Surface, layer=1):
        x, y = coord
        w, h = surface.get_width(), surface.get_height()
        surface.lock()
        for yoff in range(h):
            cury = y + yoff
            for xoff in range(w):
                curx = x + xoff
                color = surface.get_at((xoff, yoff))
                if color == surface.get_colorkey() or color.a == 0:
                    continue
                self.set_color(curx, cury, color, layer)
        surface.unlock()

    def fill(self, rect: pygame.Rect, color, layer=1):
        for y in range(rect.y, rect.y + rect.height):
            for x in range(rect.x, rect.x + rect.width):
                self.set_color(x, y, color, layer)

    @with_lock
    def paint(self):
        px = SquarePixel(self.pixel_width)
        #px = RoundPixel(self.pixel_width)
        px.inner_border_color = px.outer_border_color
        for y in range(self.height):
            for x in range(self.width):
                coord = (x*self.pixel_width, y*self.pixel_width, self.pixel_width, self.pixel_width)
                pixel = px.render(self.foreground[y][x], (0, 0, 0))
                pygame.draw.rect(self.screen, self.background[y][x], coord)
                self.screen.blit(pixel, coord)
        pygame.display.flip()


def get_fonts():
    fonts = []
    #fonts += [Font3x5()]
    #fonts += [Font6x10()]
    size_maps = {
        'PressStart2P-Regular.ttf': 8,
        'PixelifySans-Regular.ttf': 10,
        'Tiny5-Regular.ttf': 12,
    }
    for font_path in Path('./fonts').glob('*.ttf'):
        size = size_maps.get(font_path.name, 12)
        fonts.append(pygame.font.Font(str(font_path), size))
    return fonts


def app(pxl8: Pixelate):
    try:
        if os.path.exists("mountain-cabin.png"):
            pxl8.draw_surface((0, 0), pygame.image.load("mountain-cabin.png"), layer=0)
        fonts = get_fonts()
        i = 0
        interval = 10
        while pxl8.running:
            if i % interval == 0:
                font = fonts[(i // interval) % len(fonts)]
            msg = time.strftime("%e %b").strip()
            with pxl8.lock:
                pxl8.fill(pygame.Rect(0, 0, pxl8.width, pxl8.height), CLEAR)
                shadow = font.render(msg, 0, (80, 80, 80))
                line = font.render(msg, 0, WHITE)
                #x = pxl8.width // 2 - (line.get_width()) // 2
                #y = pxl8.height // 2 - font.get_linesize()
                x = 1
                y = pxl8.height - font.get_linesize() * 2
                pxl8.draw_surface((x+1, y+1), shadow)
                #for sy in range(y-1, y+2):
                #    for sx in range(x-1, x+2):
                #        pxl8.draw_surface((sx, sy), shadow)
                pxl8.draw_surface((x, y), line)
                y += font.get_linesize()
                if i % 2 == 0:
                    msg = time.strftime("%I:%M %p").lower().lstrip('0')
                else:
                    msg = time.strftime("%I %M %p").lower().lstrip('0')
                shadow = font.render(msg, 0, (80, 80, 80))
                line = font.render(msg, 0, WHITE)
                x = pxl8.width // 2 - (line.get_width()) // 2
                pxl8.draw_surface((x+1, y+1), shadow)
                pxl8.draw_surface((x, y), line)
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
