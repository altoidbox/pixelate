from pixelate import *
import text
import time
import yaml
from pathlib import Path
from dataclasses import dataclass
from config import *


@dataclass
class ClockConfig(LoadableConfig):
    font: FontFileConfig
    background: ImageFileConfig | None = None
    text_color: pygame.Color = field(default_factory=lambda: WHITE)
    shadow_color: pygame.Color | None = None
    xalign: int = 0
    yalign: int = 0
    show_dayofweek: bool = False
    show_date: bool = False
    twelve_hour: bool = False

    @classmethod
    def load(cls, config):
        if 'font' in config:
            config['font'] = FontFileConfig.load(config['font'])
        if 'background' in config:
            config['background'] = ImageFileConfig.load(config['background'])
        if 'text_color' in config:
            config['text_color'] = pygame.Color(config['text_color'])
        if 'shadow_color' in config:
            config['shadow_color'] = pygame.Color(config['shadow_color'])
        return cls(**config)


def load_configs(path):
    with open(path, 'r') as f:
        return [ClockConfig.load(config) for config in yaml.safe_load(f)]


PRESETS = load_configs('clock.yml')


class ClockConfigEditorMixin:
    CONFIG_MODE_NONE = 0
    CONFIG_MODE_FONT = 1
    CONFIG_MODE_BACKGROUND = 2

    def __init__(self, *args, **kwargs):
        self.__config_mode = self.CONFIG_MODE_NONE

    def key_down_font(self, event):
        match event.key:
            case pygame.K_j:
                self.font_index = (self.font_index + 1) % len(self.fonts)
                path, size = self.fonts[self.font_index]
                self.config.font = FontFileConfig(path=path, size=size)
            case pygame.K_k:
                self.font_index = (self.font_index - 1) % len(self.fonts)
                path, size = self.fonts[self.font_index]
                self.config.font = FontFileConfig(path=path, size=size)
            case pygame.K_u:
                self.config.font = FontFileConfig(path=self.config.font.name, size=self.config.font.size + 1)
            case pygame.K_i:
                self.config.font = FontFileConfig(path=self.config.font.name, size=max(self.config.font.size - 1, 0))
            case pygame.K_UP:
                self.config.yalign = max(self.config.yalign - 25, 0)
            case pygame.K_DOWN:
                self.config.yalign = min(self.config.yalign + 25, 100)
            case pygame.K_LEFT:
                self.config.xalign = max(self.config.xalign - 25, 0)
            case pygame.K_RIGHT:
                self.config.xalign = min(self.config.xalign + 25, 100)
            case _:
                return False
        #print(self.config.font.name, 's:', self.config.font.size, 'h:', self.font.get_height(), 'l:', self.font.get_linesize(), 'a:', self.font.get_ascent(), 'd:', self.font.get_descent())
        return True

    def key_down_background(self, event):
        match event.key:
            case pygame.K_j:
                self.bg_index = (self.bg_index + 1) % len(self.bg_paths)
                self.config.background = ImageFileConfig(self.bg_paths[self.bg_index])
            case pygame.K_k:
                self.bg_index = (self.bg_index - 1) % len(self.bg_paths)
                self.config.background = ImageFileConfig(self.bg_paths[self.bg_index])
            case pygame.K_UP:
                if self.config.background is None:
                    return False
                self.config.background.yalign = max(self.config.background.yalign - 10, 0)
            case pygame.K_DOWN:
                if self.config.background is None:
                    return False
                self.config.background.yalign = min(self.config.background.yalign + 10, 100)
            case pygame.K_LEFT:
                if self.config.background is None:
                    return False
                self.config.background.xalign = max(self.config.background.xalign - 10, 0)
            case pygame.K_RIGHT:
                if self.config.background is None:
                    return False
                self.config.background.xalign = min(self.config.background.xalign + 10, 100)
            case _:
                return False
        return True

    def key_down(self, event):
        update = True
        match event.key, self.__config_mode:
            case pygame.K_f, _:
                self.__config_mode = self.CONFIG_MODE_FONT
                return
            case pygame.K_b, _:
                self.__config_mode = self.CONFIG_MODE_BACKGROUND
                return
            case pygame.K_c, _:
                self.config.twelve_hour = not self.config.twelve_hour
            case pygame.K_d, _:
                self.config.show_date = not self.config.show_date
            case pygame.K_w, _:
                self.config.show_dayofweek = not self.config.show_dayofweek
            case pygame.K_p, _:
                self.config_index = (self.config_index + 1) % len(PRESETS)
                self.config = PRESETS[self.config_index]
            case _, self.CONFIG_MODE_NONE:
                return
            case _, self.CONFIG_MODE_FONT:
                update = self.key_down_font(event)
            case _, self.CONFIG_MODE_BACKGROUND:
                update = self.key_down_background(event)
        if update:
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


class ClockApp(ClockConfigEditorMixin, PixelateApp):
    def __init__(self, pxl8: Pixelate):
        super().__init__(pxl8)
        self.pxl8 = pxl8
        self.display = pxl8.create_display(self)
        self.fonts = text.get_fonts()
        self.font_index = 0
        self.surfaces = [None, None]
        self.surface_time = None
        self.surface_index = 0
        self.timer_event = pygame.event.custom_type()
        self.event_map = {
            self.timer_event: self.update_time,
            pygame.KEYDOWN: self.key_down,
            pygame.MOUSEBUTTONDOWN: self.mouse_down,
        }
        self.bg_paths = list(Path('backgrounds').iterdir())
        self.bg_index = 0
        self.config_index = 1
        # Configuration:
        self.config = PRESETS[self.config_index]

    @property
    def font(self):
        return self.config.font.value

    def start(self):
        pass

    def activate(self):
        self.pxl8.active_display = self.display
        pygame.event.set_allowed([self.timer_event, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN])
        self.update_time(force=True)
        pygame.time.set_timer(self.timer_event, 1000)

    def deactivate(self):
        pygame.time.set_timer(self.timer_event, 0)

    def render_text(self, msg) -> pygame.Surface:
        if self.config.shaow_color is None:
            surf = self.font.render(msg, self.config.text_color)
        else:
            surf = text.text_shadow(self.font, msg, self.config.text_color, self.config.shadow_color)
        r = surf.get_rect()
        r.inflate_ip((-1, 0))
        return surf.subsurface(r)

    def draw_time(self, curtime):
        if self.config.show_date:
            datetext = time.strftime("%e %b", curtime).strip()
            if self.config.show_dayofweek:
                datetext = time.strftime("%a, ", curtime) + datetext
            dateline = self.render_text(datetext)
            dateline = dateline.subsurface(dateline.get_bounding_rect())
        elif self.config.show_dayofweek:
            dateline = self.render_text(time.strftime("%A", curtime))
            dateline = dateline.subsurface(dateline.get_bounding_rect())
        else:
            dateline = None
        if self.config.twelve_hour:
            hour = self.render_text(time.strftime("%I", curtime).lstrip('0'))
        else:
            hour = self.render_text(time.strftime("%H", curtime))
        colon = self.render_text(':')
        blank = pygame.Surface((colon.get_width(), hour.get_height()), pygame.SRCALPHA)
        blank.fill(CLEAR)
        minutes = self.render_text(time.strftime("%M", curtime))
        if self.config.twelve_hour:
            ampm = self.render_text(time.strftime("%p", curtime).lower())
            time_suffix = [ampm]
        else:
            time_suffix = []
        with_colon = join_horizontal([hour, colon, minutes, blank] + time_suffix)
        without_colon = join_horizontal([hour, blank, minutes, blank] + time_suffix)
        timeline_bounds = with_colon.get_bounding_rect()
        timeline_bounds2 = without_colon.get_bounding_rect()
        if timeline_bounds2.height > timeline_bounds.height:
            timeline_bounds = timeline_bounds2
        surfaces = []
        for timeline in [with_colon, without_colon]:
            timeline = timeline.subsurface(timeline_bounds)
            if dateline is not None:
                surfaces.append(join_vertical([dateline, timeline], xalign=self.config.xalign, ypadding=1))
            else:
                surfaces.append(timeline)
        return surfaces

    def update_time(self, event=None, force=False):
        curtime = time.localtime()
        if force and self.config.background is not None:
            surf, xalign, yalign = self.config.background.value
            dest = align_surface(surf, self.display.rect, xalign=xalign, yalign=yalign)
            self.display.draw_surface(dest.topleft, surf, layer=0)
        if force or self.surface_time != curtime[1:5]:
            self.display.fill(self.display.rect, CLEAR)
            self.surfaces = self.draw_time(curtime)
            self.surface_time = curtime[1:5]
        if event is not None and event.type == self.timer_event:
            self.surface_index = (self.surface_index + 1) % len(self.surfaces)
        surface = self.surfaces[self.surface_index]
        rect = align_surface(surface, rel_to=self.display.rect, padding=1, xalign=self.config.xalign, yalign=self.config.yalign)
        self.display.draw_surface(rect.topleft, surface, ignore_clear=False)

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
            pygame.KEYDOWN: self.key_down,
            pygame.MOUSEBUTTONDOWN: self.mouse_down,
        }
        for event in self.pxl8.eventloop():
            handler = event_map.get(event.type, None)
            if handler is not None:
                handler(event)
