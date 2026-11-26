# https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41&daily=weather_code,temperature_2m_max,temperature_2m_min&hourly=temperature_2m,weather_code&current=temperature_2m,weather_code&timezone=auto&forecast_days=3&wind_speed_unit=mph&temperature_unit=fahrenheit&precipitation_unit=inch

from pixelate.pixelate import *
import pixelate.text as text
import yaml
from pathlib import Path
from dataclasses import dataclass
from pixelate.config import *
import requests
import urllib.parse
import datetime
import logging


CUR_DIR = Path(__file__).parent
LOGGER = logging.getLogger('pixelate.weather')
WEATHER_CODES = {
    0: "clear",
    1: "mostly-clear",
    2: "partly-cloudy",
    3: "overcast",
    45: "fog",
    48: "depositing-rime-fog",
    51: "light-drizzle",
    53: "drizzle",
    55: "heavy-drizzle",
    56: "light-freezing-drizzle",
    57: "heavy-freezing-drizzle",
    61: "light-rain",
    63: "rain",
    65: "heavy-rain",
    66: "light-freezing-rain",
    67: "heavy-freezing-rain",
    71: "light-snow",
    73: "snow",
    75: "heavy-snow",
    77: "snow-grains",
    80: "light-rain-showers",
    81: "rain-showers",
    82: "violent-rain-showers",
    85: "light-snow-showers",
    86: "heavy-snow-showers",
    95: "thunderstorm",
    96: "thunderstorm-with-light-hail",
    97: "heavy-thunderstorm",
    99: "thunderstorm-with-heavy-hail"
}


def weather_icon(icons: YamlFileConfig.ConfigType, code, is_day=True) -> Path:
    timeofday = 'day' if is_day else 'night'
    name = WEATHER_CODES[code]
    mapping = icons.value
    dir_ = icons.path.parent / mapping.get('directory', '.')
    if timeofday and name in mapping.get(timeofday, {}):
        return dir_ / mapping[timeofday][name]
    if name not in mapping.get('general', {}):
        return None
    return dir_ / mapping['general'][name]


def encode_params(params):
    elements = []
    for key, value in params.items():
        if isinstance(value, list):
            value = ','.join(value)
        elements.append(f'{key}={value}')
    return '&'.join(elements)


def create_weather_request(location, temp_units='fahrenheit'):
    params = {
        "latitude": location[0],
        "longitude": location[1],
        "forecast_days": 4,
        "daily": ["weather_code", "temperature_2m_max", "temperature_2m_min", "sunrise", "sunset"],
        "forecast_hours": 12,
        "past_hours": 0,
        "hourly": ["temperature_2m", "weather_code", "is_day"],
        "current": ["temperature_2m", "weather_code", "is_day"],
        "timezone": "auto",
        "temperature_unit": temp_units,
    }
    return f'https://api.open-meteo.com/v1/forecast?{encode_params(params)}'


def create_location_request(location):
    params = {
        'name': urllib.parse.quote(location),
        'count': 2,
        'language': 'en',
        'format': 'json'
    }
    url = f"https://geocoding-api.open-meteo.com/v1/search?{encode_params(params)}"
    return url


def get_weather(config: 'AppConfig'):
    url = create_weather_request(config.location_coord, config.temp_units)
    resp = requests.get(url)
    if resp.status_code != 200:
        LOGGER.error(f'Weather request returned HTTP status {resp.status_code}')
        return None
    try:
        data = resp.json()
        return data
    except:
        LOGGER.exception('Weather request returned unexpected data')
        return None


def get_location(location):
    url = create_location_request(location)
    resp = requests.get(url)
    if resp.status_code != 200:
        LOGGER.error(f'Location request returned HTTP status {resp.status_code}')
        return None
    try:
        results = resp.json()['results']
    except:
        # unexpected data
        LOGGER.exception('Location request returned unexpected data')
        return None
    lat_long = results[0]['latitude'], results[0]['longitude']
    LOGGER.info(f'Translated {location} to {lat_long}')
    return lat_long


@dataclass
class AppConfig(LoadableConfig):
    location: str | list
    font: FontFileConfig.ConfigType = FontFileConfig()
    icons: YamlFileConfig.ConfigType = YamlFileConfig()
    icon_color: pygame.Color | None = ColorConfig()
    background: ImageFileConfig.ConfigType | None = field(default=ImageFileConfig())
    text_color_hi: pygame.Color = field(default=ColorConfig('indianred3'))
    text_color_lo: pygame.Color = field(default=ColorConfig('royalblue'))
    text_color_when: pygame.Color = field(default=ColorConfig('lightgray'))
    shadow_color: pygame.Color | None = field(default=ColorConfig())
    temp_units: str = "F"
    _api_location: tuple | None = field(init=False, repr=False, compare=False, default=None)

    @property
    def location_coord(self):
        if self._api_location is None:
            if isinstance(self.location, str):
                self._api_location = get_location(self.location)
            elif isinstance(self.location, (list, tuple)):
                self._api_location = tuple(self.location[:2])
            else:
                raise ValueError(f'Unknown location type: {self.location} ({type(self.location)})')
        return self._api_location

    @classmethod
    def load(cls, config):
        config = super().load(config)
        if config.temp_units.lower().startswith('c'):
            config.temp_units = 'celsius'
        else:
            config.temp_units = 'fahrenheit'
        return config


def load_configs(path):
    if path.exists():
        with open(path, 'r') as f:
            return [AppConfig.load(config) for config in yaml.safe_load(f)]


PRESETS = load_configs(CUR_DIR / 'config.yml')


class AppConfigEditorMixin:
    CONFIG_MODE_NONE = 0
    CONFIG_MODE_FONT = 1
    CONFIG_MODE_BACKGROUND = 2

    WEATHER_TYPE_DAILY = 0
    WEATHER_TYPE_HOURLY = 1
    WEATHER_TYPE_COUNT = 2

    def __init__(self, *args, **kwargs):
        self.__config_mode = self.CONFIG_MODE_NONE
        self.fonts = text.get_fonts()
        self.font_index = 0
        self.bg_paths = list(Path('resources/backgrounds').iterdir())
        self.bg_index = 0
        self.config_index = 1
        self.weather_type = self.WEATHER_TYPE_DAILY

    def key_down_font(self, event):
        match event.key:
            case pygame.K_j:
                self.font_index = (self.font_index + 1) % len(self.fonts)
                path, size = self.fonts[self.font_index]
                self.config.font = (path, size)
            case pygame.K_k:
                self.font_index = (self.font_index - 1) % len(self.fonts)
                self.config.font = self.fonts[self.font_index]
            case pygame.K_u:
                self.config.font = dict(path=self.config.font.name, size=self.config.font.size + 1)
            case pygame.K_i:
                self.config.font = dict(path=self.config.font.name, size=max(self.config.font.size - 1, 0))
            case _:
                return False
        return True

    def key_down_background(self, event):
        match event.key:
            case pygame.K_j:
                self.bg_index = (self.bg_index + 1) % len(self.bg_paths)
                self.config.background = self.bg_paths[self.bg_index]
            case pygame.K_k:
                self.bg_index = (self.bg_index - 1) % len(self.bg_paths)
                self.config.background = self.bg_paths[self.bg_index]
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
            self.update(force=True)

    def mouse_down(self, event):
        self.weather_type += 1
        if self.weather_type >= self.WEATHER_TYPE_COUNT:
            self.weather_type = 0
        self.update()
        return True


class WeatherApp(AppConfigEditorMixin, PixelateApp):
    def __init__(self, pxl8: Pixelate):
        super().__init__(pxl8)
        self.pxl8 = pxl8
        self.display = pxl8.create_display(self)
        self.timer_event = pygame.event.custom_type()
        self.event_map = {
            self.timer_event: self.update,
            pygame.KEYDOWN: self.key_down,
            pygame.MOUSEBUTTONDOWN: self.mouse_down,
        }
        self.weather = None
        # Configuration:
        self.config = PRESETS[0]

    def start(self):
        pass

    def activate(self):
        self.pxl8.active_display = self.display
        #pygame.event.set_allowed([self.timer_event, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN])
        self.update(force=True)
        # Update every 15 minutes
        pygame.time.set_timer(self.timer_event, 15 * 60 * 1000)

    def deactivate(self):
        pygame.time.set_timer(self.timer_event, 0)

    def render_text(self, msg, color) -> pygame.Surface:
        return text.render(self.config.font.value, msg, color, self.config.shadow_color)

    def draw_one_day(self, weather_code, temp, when=None, is_day=True):
        path = weather_icon(self.config.icons, weather_code, is_day)
        size = self.display.width // 3 - 1
        if path.suffix == '.svg':
            #icon = pygame.image.load_sized_svg(path, (128, 128))
            icon = pygame.image.load_sized_svg(path, (size, size))
        else:
            icon = pygame.image.load(path)
            scale = (size / icon.size[0])
            icon = pygame.transform.scale_by(icon, scale)
        if self.config.icon_color is not None:
            icon = pygame.transform.solid_overlay(icon, self.config.icon_color, keep_alpha=True)

        print(f'icon size: {icon.get_rect().bottomright}')

        if isinstance(temp, (list, tuple)):
            hi_temp, lo_temp = temp
            hi = self.render_text(f'{hi_temp}', self.config.text_color_hi)
            lo = self.render_text(f'{lo_temp}', self.config.text_color_lo)
            temp_surf = join_horizontal((hi, lo), yalign=100, xpadding=2)
        else:
            # TODO: Temp color gradiant from red=112 to yellow=72 to blue=32 to white=-8
            temp_surf = self.render_text(f'{temp}', self.config.text_color_when)
        #print(f'temp size: {temp.get_rect().bottomright}, hi:{hi.get_rect()} lo:{lo.get_rect()}')
        stack = [icon, temp_surf]
        if when:
            stack.append(self.render_text(when, self.config.text_color_when))

        return join_vertical(stack, xalign=50, ypadding=1)

    def draw_daily_weather(self, weather):
        daily = weather['daily']
        days = []
        for i in range(3):
            code = daily['weather_code'][i]
            hi = int(daily['temperature_2m_max'][i])
            lo = int(daily['temperature_2m_min'][i])
            date = datetime.date(*(int(x) for x in daily['time'][i].split('-')))
            dayofweek = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][date.weekday()]
            days.append(self.draw_one_day(code, (hi, lo), dayofweek))
        return days

    def draw_hourly_weather(self, weather):
        hours = []
        current = weather['current']
        hourly = weather['hourly']
        # replace index 0 with current weather to make getting them all easier later
        for key in hourly.keys():
            hourly[key][0] = current[key]
        #index = 0
        #if int(current['time'][2:]) >= 30:
        #    # if current time is at the half or greater, then increment index once
        #    index += 1
        for i in range(3):
            i = i * 3
            code = hourly['weather_code'][i]
            temp = int(hourly['temperature_2m'][i])
            hour = int(hourly['time'][i].split('T')[1].split(':')[0])
            if hour >= 12:
                time = f'{hour-12}p'
            else:
                if hour == 0:
                    hour = 12
                time = f'{hour}a'

            hours.append(self.draw_one_day(code, temp, time, hourly['is_day'][i]))
        return hours

    def update(self, event=None, force=False):
        if force:
            if self.config.background is not None:
                surf, xalign, yalign = self.config.background.value
                dest = align_surface(surf, self.display.rect, xalign=xalign, yalign=yalign)
                self.display.draw_surface(dest.topleft, surf, layer=0)
            else:
                self.display.fill(self.display.rect, SquarePixel(size=self.display.pixel_width, inner_border_color='black'), layer=2)
                self.display.fill(self.display.rect, (0, 0, 0, 0), layer=0)
        if event or self.weather is None:
            self.weather = get_weather(self.config)
        self.display.fill(self.display.rect, CLEAR)
        if self.weather_type == self.WEATHER_TYPE_DAILY:
            units = self.draw_daily_weather(self.weather)
        elif self.weather_type == self.WEATHER_TYPE_HOURLY:
            units = self.draw_hourly_weather(self.weather)
        for i, surf in enumerate(units):
            xalign = (i) * 50
            rect = align_surface(surf, rel_to=self.display.rect, xalign=xalign, yalign=0, padding=1)
            self.display.draw_surface(rect.topleft, surf)
            #print(f'draw {surf.get_rect().bottomright} at {rect.topleft}')

    def handle_event(self, event: pygame.event.Event):
        handler = self.event_map.get(event.type, None)
        if handler is not None:
            handler(event)
