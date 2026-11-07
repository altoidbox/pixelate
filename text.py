import pygame
from pathlib import Path


def draw_shape(pxarray: pygame.PixelArray, shape, coord, color):
    x, y = coord
    for yoff in range(len(shape)):
        for xoff in range(len(shape[0])):
            if bool(shape[yoff][xoff]):
                pxarray[x + xoff, y + yoff] = color


class Font(pygame.font.Font):
    def __init__(self, name=None, size=12):
        super().__init__(name, size)
        self.name = name
        self.point_size = size

    def with_size(self, size):
        return self.__class__(self.name, size)


class Font3x5(Font):
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
        return self.get_height() + 1

    def render(self, text: str, antialias, color, background=None) -> pygame.Surface:
        fixed_width, fixed_height = self.size(text)
        canvas = pygame.Surface((fixed_width, fixed_height), flags=pygame.SRCALPHA)
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


class Font6x10(Font):
    CHR_WIDTH = 6
    CHR_HEIGHT = 10
    
    def __init__(self, *args, **kwwargs):
        super().__init__(*args, **kwwargs)
        self.source = Font3x5(*args, **kwwargs)

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

    def render(self, text: str, antialias, color, background=None) -> pygame.Surface:
        self.source.underline = self.underline
        surface = self.source.render(text, antialias, color, background)
        return pygame.transform.scale_by(surface, 2)


LOADED_FONTS = {}


def get_fonts() -> list[tuple[str, int]]:
    #fonts += [Font3x5()]
    #fonts += [Font6x10()]
    size_maps = {
        'PressStart2P-Regular.ttf': [8],  # *8*: [7x7]
        'PixelifySans-Regular.ttf': [11],  # *11*: [5x7], 19: [9x12]
        'Tiny5-Regular.ttf': [8, 16],  # *8*: ~[3x5], *16*: [6x10]
        'Micro5-Regular.ttf': [10, 16, 21],  # *10*: ~[3x5], 14: [4x6], *16*: [4x8], *21*: [6x10]
        'Jersey10-Regular.ttf': [18],  # 9: bad kerning, *18*: ~[7x9]
        'Bytesized-Regular.ttf': [8, 12, 16],  # *8*: [3x4], *12*: [5x7], *16*: [6x8]
        'JacquardaBastarda9-Regular.ttf': [12],  # *12*: [5x10], 19: [bigish] 23: [big]
        'Silkscreen-Regular.ttf': [8, 15, 16],  # *8*: [4x5], 15: [7x10], 16: [8x10] - wide kerning
        'VT323-Regular.ttf': [20],  # 20: [6x11]
    }
    fonts = []
    for font_path in sorted(Path('./fonts').glob('*.ttf')):
        sizes = size_maps.get(font_path.name, [12])
        for size in sizes:
            fonts.append((font_path.name, size))
            #font = Font(str(font_path), size)
            #print(font.name, 's:', font.point_size, 'h:', font.get_height(), 'l:', font.get_linesize(), 'a:', font.get_ascent(), 'd:', font.get_descent())

    return fonts


def get_font(name, size):
    if (name, size) in LOADED_FONTS:
        return LOADED_FONTS[(name, size)]
    path = Path(name)
    if not path.exists():
        path = Path('./fonts') / name
    LOADED_FONTS[(name, size)] = font = Font(str(path), size)
    return font


def text_shadow(font: pygame.font.Font, text: str, color: pygame.Color, shadow_color: pygame.Color, offset=(1, 1)) -> pygame.Surface:
    foreground = font.render(text, 0, color)
    shadow = font.render(text, 0, shadow_color)
    shadow.set_alpha(shadow_color.a)

    dx, dy = offset
    width = foreground.get_width() + abs(dx)
    height = foreground.get_height() + abs(dy)
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    surface.blit(shadow, (max(0, dx), max(0, dy)))
    surface.blit(foreground, (max(0, -dx), max(0, -dy)))
    return surface


def text_shadows(font: pygame.font.Font, text: str, color: pygame.Color, shadow_color: pygame.Color, offsets=[(1, 1)]):
    foreground = font.render(text, 0, color)
    shadow = font.render(text, 0, shadow_color)
    #shadow.set_alpha(shadow_color.a)

    left = right = 0
    top = bottom = 0
    for (dx, dy) in offsets:
        if dx < left:
            left = dx
        elif dx > right:
            right = dx
        if dy < top:
            top = dy
        elif dy > bottom:
            bottom = dy
    
    width = foreground.get_width() + abs(left) + right
    height = foreground.get_height() + abs(top) + bottom
    bg = pygame.Surface((width, height), shadow.get_flags(), shadow.get_bitsize(), shadow.get_masks())
    bg.set_palette(shadow.get_palette())
    bg.set_colorkey(shadow.get_colorkey())
    bg.fill(shadow.get_colorkey())
    for (dx, dy) in offsets:
        bg.blit(shadow, (dx - left, dy - top))
    bg.set_alpha(shadow_color.a)
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    surface.blit(bg, (0, 0))
    surface.blit(foreground, (-left, -top))
    return surface
    