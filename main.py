import pygame
import time
import os
import ctypes
import threading
from pygame import Surface


CLEAR = pygame.Color(0, 0, 0, 0)
WHITE = pygame.Color(255, 255, 255, 255)


class Canvas(Surface):
    def render(self, canvas, coordinate):
        pass


class Font:
    def render(self, canvas, coordinate):
        pass


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

    def __init__(self):
        super().__init__(size=6)

    @classmethod
    def get(cls, char):
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

    def render(self, text: str, antialias, color, background=None) -> Surface:
        fixed_width = (self.CHR_WIDTH + 1) * len(text) - 1
        fixed_height = self.CHR_HEIGHT
        canvas = Surface((fixed_width, fixed_height), flags=pygame.SRCALPHA)
        if not background:
            background = pygame.Color(0, 0, 0, 0)
        canvas.fill(background)
        x = -1
        y = 0
        with pygame.PixelArray(canvas) as pxarray:
            for c in text:
                shape = self.get(c)
                if shape is None:
                    continue
                x += 1
                draw_shape(pxarray, shape, (x, y), color)
                x += self.CHR_WIDTH
        if x < 0:
            return Surface((0, 0))
        return canvas  #.subsurface(0, 0, x, y + fixed_height)


class Font6x10(pygame.font.Font):
    CHR_WIDTH = 6
    CHR_HEIGHT = 10
    
    def __init__(self):
        super().__init__(size=22)

    def render(self, text: str, antialias, color, background=None) -> Surface:
        surface = Font3x5().render(text, antialias, color, background)
        return pygame.transform.scale_by(surface, 2)


def disable_dpi_scaling():
    if os.name == 'nt':
        try:
            # Force the OS to map the window 1:1 pixel perfect to the monitor
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


class Pixel:
    pass


def with_lock(func):
    def _func_with_lock(*args, **kwargs):
        nonlocal func
        with args[0].lock:
            func(*args, **kwargs)
    _func_with_lock.__name__ = func.__name__
    return _func_with_lock


class Pixelate:
    def __init__(self):
        disable_dpi_scaling()
        pygame.init()
        self.lock = threading.RLock()
        self.clock = pygame.time.Clock()

        pygame.display.init()
        monitor_info = pygame.display.Info()
        screen_width, screen_height = pygame.display.get_desktop_sizes()[0]
        print(screen_width, screen_height)
        screen_width = monitor_info.current_w
        screen_height = monitor_info.current_h
        print(screen_width, screen_height)

        self.width = 64
        self.pixel_width = screen_width // self.width
        self.height = screen_height // self.pixel_width

        print(f"Pixel disp: {self.width}x{self.height}")
        print(f"Pixel size: {self.pixel_width}x{self.pixel_width}")
        self.background = []
        self.foreground = []
        for y in range(self.height):
            self.background.append([pygame.Color(min(y*2, 255), min(y*5, 255), min(y*8, 255), 255)] * self.width)
            self.foreground.append([CLEAR] * self.width)

        self.screen = pygame.display.set_mode(size=(screen_width, screen_height), flags=pygame.FULLSCREEN)  #  | pygame.SCALED | pygame.NOFRAME
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
            self.paint()
        pygame.quit()

    def set_color(self, x, y, color):
        if x >= self.width or y >= self.height:
            return
        self.foreground[y][x] = color

    @with_lock
    def draw_shape(self, x, y, shape, color, invert=False):
        #print(x, y, shape)
        for yoff in range(len(shape)):
            for xoff in range(len(shape[0])):
                if bool(shape[yoff][xoff]) != invert:
                    self.set_color(x+xoff, y+yoff, color)
                #else:
                #    self.set_color(x+xoff, y+yoff, CLEAR)

    @with_lock
    def draw_surface(self, coord, surface: Surface):
        x, y = coord
        w, h = surface.get_width(), surface.get_height()
        #with pygame.PixelArray(surface) as pxarray:
        surface.lock()
        for yoff in range(h):
            cury = y + yoff
            for xoff in range(w):
                curx = x + xoff
                #color = pxarray[xoff, yoff]
                #print(xoff, yoff, (color >> 24) & 0xFF, (color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF)
                #alpha = (color >> 24) & 0xFF
                #color = surface.get_at_mapped((xoff, yoff))
                #color = surface.unmap_rgb(color)
                color = surface.get_at((xoff, yoff))
                if color == surface.get_colorkey() or color.a == 0:
                    continue
                self.set_color(curx, cury, color)
        surface.unlock()

    def clear_box(self, x, y, width, height):
        row = [ 1 ] * width
        shape = [ row ] * height
        self.draw_shape(x, y, shape, CLEAR)

    def draw_chr(self, x, y, char, color, shadow=None):
        shadow_height = 0
        if shadow is not None:
            shadow_height += 1
        shape = Font3x5.get(char)
        #print(char)
        self.clear_box(x, y, len(shape[0]), len(shape) + shadow_height)
        if shadow:
            self.draw_shape(x, y+1, shape, shadow)
        self.draw_shape(x, y, shape, color)

    def draw_str(self, x, y, msg, color, shadow=None):
        for c in msg:
            self.draw_chr(x, y, c, color, shadow)
            x += 4

    @with_lock
    def paint(self):
        pixel = pygame.Surface((self.pixel_width, self.pixel_width), pygame.SRCALPHA)
        for y in range(self.height):
            for x in range(self.width):
                coord = (x*self.pixel_width, y*self.pixel_width, self.pixel_width, self.pixel_width)
                #color = self.foreground[y][x]
                #if color == CLEAR:
                #    color = self.background[y][x]
                #pixel.fill(self.background[y][x])
                pygame.draw.rect(self.screen, self.background[y][x], coord)
                pixel.fill(self.foreground[y][x])
                pygame.draw.rect(pixel, pygame.Color(40, 40, 40), (0, 0, self.pixel_width, self.pixel_width), width=2)
                pygame.draw.rect(pixel, pygame.Color(0, 0, 0), (0, 0, self.pixel_width, self.pixel_width), width=1)
                #pygame.draw.rect(self.screen, self.foreground[y][x], coord)
                #pygame.draw.rect(self.screen, pygame.Color(40, 40, 40), coord, width=2)
                #pygame.draw.rect(self.screen, pygame.Color(0, 0, 0), coord, width=1)
                self.screen.blit(pixel, coord)
            #pygame.draw.
        pygame.display.flip()


def app(pxl8: Pixelate):
    try:
        #font = Font6x10()
        fonts = []
        #fonts += [Font6x10()]
        fonts += [pygame.font.Font(name, size=16) for name in os.listdir('.') if name.endswith('.ttf')]
        #font = pygame.font.Font('Doto-Thin.ttf', size=12)
        #font.set_bold(False)
        i = 0
        interval = 10
        while pxl8.running:
            #msg = str(i)
            if i % interval == 0:
                font = fonts[(i // interval) % len(fonts)]
            msg = time.strftime("%e %b")
            with pxl8.lock:
                pxl8.clear_box(0, 0, pxl8.width, pxl8.height)
                shadow = font.render(msg, 0, (80, 80, 80))
                line = font.render(msg, 0, WHITE)
                #print(line.get_width(), 'x', line.get_height())
                x = pxl8.width // 2 - (line.get_width()) // 2
                y = pxl8.height // 2 - font.get_height() #line.get_height()
                pxl8.draw_surface((x+1, y), shadow)
                pxl8.draw_surface((x, y), line)
                #p.draw_str(pxl8.width // 2 - (len(msg) * 4) // 2, y, msg, WHITE, shadow=(80, 80, 80))
                y += font.get_ascent()  #font.get_height() - 2
                msg = time.strftime("%I:%M %p").lower().lstrip('0')
                shadow = font.render(msg, 0, (80, 80, 80))
                line = font.render(msg, 0, WHITE)
                x = pxl8.width // 2 - (line.get_width()) // 2
                pxl8.draw_surface((x+1, y), shadow)
                pxl8.draw_surface((x, y), line)
                #pxl8.draw_str(pxl8.width // 2 - (len(msg) * 4) // 2, y, msg, WHITE, shadow=pygame.Color(80, 80, 80))
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
