from pixelate import *
import text
import time


BASE_CONFIG = {
    'font': ('PressStart2P-Regular.ttf', 8),
    'background': ("mountain-cabin.png", 0, 10),
    'text_color': WHITE,
    'shadow_color': pygame.Color(80, 80, 80, 180),
    'xalign': 100,
    'yalign': 100,
    'show_dayofweek': False,
    'show_date': True,
    'clock_12hour': True,
}

PRESETS = [BASE_CONFIG]
PRESETS.append(BASE_CONFIG.copy())
PRESETS[-1].update(
    font=('Jersey10-Regular.ttf', 18),
    background=("mountain-cabin.png", 0, 100),
    show_date=False, clock_12hour=False,
    xalign=50, yalign=25
)


class ClockApp(PixelateApp):
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
            pygame.KEYDOWN: self.key_press,
            pygame.MOUSEBUTTONDOWN: self.mouse_down,
        }
        self.config_index = 1
        # Configuration:
        self._font = None
        self._background = None
        self.text_color = None
        self.shadow_color = None
        self.xalign = 0
        self.yalign = 0
        self.show_dayofweek = False
        self.show_date = False
        self.clock_12hour = False
        self.load_config(**PRESETS[self.config_index])

    @property
    def font(self):
        return self._font

    @font.setter
    def font(self, value):
        if isinstance(value, (list, tuple)):
            self._font = text.get_font(*value)
        elif isinstance(value, str):
            self._font = text.get_font(value)
        else:
            self._font = value

    @property
    def background(self):
        return self._background

    @background.setter
    def background(self, value):
        xalign, yalign = (0, 0)
        if isinstance(value, (list, tuple)):
            value, xalign, yalign = value
        if isinstance(value, pygame.Surface):
            surf = value
        elif isinstance(value, str):
            surf = pygame.image.load(value)

        self._background = surf, xalign, yalign
        dest = align_surface(surf, self.display.rect, xalign=xalign, yalign=yalign)
        self.display.draw_surface(dest.topleft, surf, layer=0)

    def load_config(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.update_time(force=True)

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
        surf = text.text_shadow(self.font, msg, self.text_color, self.shadow_color)
        r = surf.get_rect()
        r.inflate_ip((-1, 0))
        return surf.subsurface(r)

    def draw_time(self, curtime):
        if self.show_date:
            datetext = time.strftime("%e %b", curtime).strip()
            if self.show_dayofweek:
                datetext = time.strftime("%a, ", curtime) + datetext
            dateline = self.render_text(datetext)
            dateline = dateline.subsurface(dateline.get_bounding_rect())
        elif self.show_dayofweek:
            dateline = self.render_text(time.strftime("%A", curtime))
            dateline = dateline.subsurface(dateline.get_bounding_rect())
        else:
            dateline = None
        if self.clock_12hour:
            hour = self.render_text(time.strftime("%I", curtime).lstrip('0'))
        else:
            hour = self.render_text(time.strftime("%H", curtime))
        colon = self.render_text(':')
        blank = pygame.Surface((colon.get_width(), hour.get_height()), pygame.SRCALPHA)
        blank.fill(CLEAR)
        minutes = self.render_text(time.strftime("%M", curtime))
        if self.clock_12hour:
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
                surfaces.append(join_vertical([dateline, timeline], xalign=self.xalign, ypadding=1))
            else:
                surfaces.append(timeline)
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
        rect = align_surface(surface, rel_to=self.display.rect, padding=1, xalign=self.xalign, yalign=self.yalign)
        self.display.draw_surface(rect.topleft, surface, ignore_clear=False)

    def key_press(self, event):
        match event.key:
            case pygame.K_j:
                self.font_index = (self.font_index + 1) % len(self.fonts)
                self.font = text.get_font(*self.fonts[self.font_index])
            case pygame.K_k:
                self.font_index = (self.font_index - 1) % len(self.fonts)
                self.font = text.get_font(*self.fonts[self.font_index])
            case pygame.K_u:
                self.font = self.font.with_size(self.font.point_size + 1)
            case pygame.K_i:
                self.font = self.font.with_size(self.font.point_size - 1)
            case pygame.K_UP:
                self.yalign = max(self.yalign - 25, 0)
            case pygame.K_DOWN:
                self.yalign = min(self.yalign + 25, 100)
            case pygame.K_LEFT:
                self.xalign = max(self.xalign - 25, 0)
            case pygame.K_RIGHT:
                self.xalign = min(self.xalign + 25, 100)
            case pygame.K_c:
                self.clock_12hour = not self.clock_12hour
            case pygame.K_d:
                self.show_date = not self.show_date
            case pygame.K_w:
                self.show_dayofweek = not self.show_dayofweek
            case pygame.K_p:
                self.config_index = (self.config_index + 1) % len(PRESETS)
                self.load_config(**PRESETS[self.config_index])
            case _:
                return
        #print(self.font.name, 's:', self.font.point_size, 'h:', self.font.get_height(), 'l:', self.font.get_linesize(), 'a:', self.font.get_ascent(), 'd:', self.font.get_descent())
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
