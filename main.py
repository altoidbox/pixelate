import pygame
import time
import os
import ctypes
import threading


CLEAR = (-1, -1, -1)
WHITE = (255, 255, 255)


class CharMap:
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
    def get(cls, char):
        shape = cls.shape_map.get(char, [])
        if shape:
            return shape
        val = f'{cls.FONT[ord(char)]:015b}'
        for i in range(0, cls.CHR_WIDTH * cls.CHR_HEIGHT, cls.CHR_WIDTH):
            shape.append([int(j) for j in val[i:i + cls.CHR_WIDTH]])
        cls.shape_map[char] = shape
        return shape


def disable_dpi_scaling():
    if os.name == 'nt':
        try:
            # Force the OS to map the window 1:1 pixel perfect to the monitor
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


class Pixel:
    pass


class Pixelate:
    def __init__(self):
        disable_dpi_scaling()
        pygame.init()
        self.lock = threading.Lock()
        self.clock = pygame.time.Clock()

        self.width = 64
        self.height = 32
        self.background = []
        self.foreground = []
        for y in range(self.height):
            self.background.append([(y*2, y*5, y*8)] * self.width)
            self.foreground.append([CLEAR] * self.width)

        pygame.display.init()
        monitor_info = pygame.display.Info()
        screen_width, screen_height = pygame.display.get_desktop_sizes()[0]
        print(screen_width, screen_height)
        screen_width = monitor_info.current_w
        screen_height = monitor_info.current_h
        print(screen_width, screen_height)

        self.pixel_width = screen_width // self.width
        pixel_height = screen_height // self.height
        if pixel_height < self.pixel_width:
            self.pixel_width = pixel_height

        print(f"Pixel size: {self.pixel_width}x{self.pixel_width}")

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
        self.foreground[y][x] = color

    def draw_shape(self, x, y, shape, color, invert=False):
        with self.lock:
            #print(x, y, shape)
            for yoff in range(len(shape)):
                for xoff in range(len(shape[0])):
                    if bool(shape[yoff][xoff]) != invert:
                        self.set_color(x+xoff, y+yoff, color)
                    #else:
                    #    self.set_color(x+xoff, y+yoff, CLEAR)

    def clear_box(self, x, y, width, height):
        row = [ 1 ] * width
        shape = [ row ] * height
        self.draw_shape(x, y, shape, CLEAR)

    def draw_chr(self, x, y, char, color, shadow=None):
        shadow_height = 0
        if shadow is not None:
            shadow_height += 1
        shape = CharMap.get(char)
        #print(char)
        self.clear_box(x, y, len(shape[0]), len(shape) + shadow_height)
        if shadow:
            self.draw_shape(x, y+1, shape, shadow)
        self.draw_shape(x, y, shape, color)

    def draw_str(self, x, y, msg, color, shadow=None):
        for c in msg:
            self.draw_chr(x, y, c, color, shadow)
            x += 4

    def paint(self):
        with self.lock:
            for y in range(self.height):
                for x in range(self.width):
                    coord = (x*self.pixel_width, y*self.pixel_width, self.pixel_width, self.pixel_width)
                    color = self.foreground[y][x]
                    if color == CLEAR:
                        color = self.background[y][x]
                    pygame.draw.rect(self.screen, color, coord)
                    pygame.draw.rect(self.screen, (40, 40, 40), coord, width=2)
                    pygame.draw.rect(self.screen, (0, 0, 0), coord, width=1)
                #pygame.draw.
            pygame.display.flip()


def app(p):
    i = 0
    while p.running:
        msg = str(i)
        msg = time.strftime("%e %b")
        y = 32//2 - 6
        p.draw_str(64 // 2 - (len(msg) * 4) // 2, y, msg, WHITE, shadow=(80, 80, 80))
        y += 7
        msg = time.strftime("%I:%M %p").lower().lstrip('0')
        p.draw_str(64 // 2 - (len(msg) * 4) // 2, y, msg, WHITE, shadow=(80, 80, 80))
        time.sleep(1)
        i += 1


def main():
    p = Pixelate()
    t = threading.Thread(target=app, args=[p])
    t.start()
    p.run()
    t.join()
    exit()



if __name__ == "__main__":
    main()
