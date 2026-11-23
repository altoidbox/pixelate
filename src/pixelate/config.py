from dataclasses import dataclass, field, fields
import pixelate.text as text
import pygame


class LoadableConfig:
    @classmethod
    def load_from(cls, config, name):
        if name in config:
            config[name] = cls.load(config[name])

    @classmethod
    def load(cls, config):
        if isinstance(config, dict):
            # For dictionaries, we treat it as keyword arguments
            return cls(**config)
        elif isinstance(config, (list, tuple)):
            # For lists, we treat it as positional arguments
            return cls(*config)
        # anything else (scalar?) gets passed in as is
        return cls(config)


class ConfigDescriptor:
    ConfigType = LoadableConfig

    def __init__(self, default=None):
        self.default = default

    def __set_name__(self, owner, name):
        self.name = f'_{name}'

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return getattr(instance, self.name)

    def __set__(self, instance, value):
        if isinstance(value, type(self)):
            value = value.default
        elif not isinstance(value, self.ConfigType):
            value = self.ConfigType.load(value)
        setattr(instance, self.name, value)


class FontFileConfig(ConfigDescriptor):
    @dataclass
    class ConfigType(LoadableConfig):
        family: str | None = None
        style: str | None = None
        path: str | None = None
        size: int | None = None
        _font: text.Font | None = field(init=False, repr=False, compare=False, default=None)
        _font_key: tuple | None = field(init=False, repr=False, compare=False, default=None)

        @property
        def name(self) -> str:
            if self.path is not None:
                return self.path
            style = self.style or 'Regular'
            return f'{self.family}-{style}.ttf'

        @property
        def value(self) -> text.Font:
            key = (self.name, self.size)
            if self._font_key != key:
                self._font = text.get_font(self.name, self.size)
                self._font_key = key
            return self._font


class ImageFileConfig(ConfigDescriptor):
    @dataclass
    class ConfigType(LoadableConfig):
        path: str
        xalign: int = 0
        yalign: int = 0
        _surface: pygame.Surface | None = field(init=False, repr=False, compare=False, default=None)
        _surface_key: tuple | None = field(init=False, repr=False, compare=False, default=None)

        @property
        def value(self) -> tuple[pygame.Surface, int, int]:
            key = (self.path, self.xalign, self.yalign)
            if self._surface_key != key:
                self._surface = pygame.image.load(self.path)
                self._surface_key = key
            return self._surface, self.xalign, self.yalign


class ColorConfig(ConfigDescriptor):
    class ConfigType(LoadableConfig):
        @classmethod
        def load(cls, value):
            if value is None:
                return None
            return pygame.Color(value)
