from dataclasses import dataclass, field, fields
import pixelate.text as text
import pygame
from typing import get_args, get_origin, Union
from types import UnionType


#def is_union(type_: object) -> bool:
#    origin = get_origin(type_)
#    return origin is Union or origin is UnionType 


class LoadableConfig:
    @classmethod
    def load(cls, config):
        #for field in fields(cls):
        #    if field.name not in config:
        #        continue
        #    if is_union(field.type):
        #        for type_ in get_args(field.type):
        #            if issubclass(type_, LoadableConfig):
        #                config[field.name] = type_.load(config[field.name])
        #    elif issubclass(field.type, LoadableConfig):
        #        config[field.name] = field.type.load(config[field.name])
        return cls(**config)


@dataclass
class FontFileConfig(LoadableConfig):
    family: str | None = None
    style: str | None = None
    path: str | None = None
    size: int | None = None
    _font: text.Font | None = field(init=False, repr=False, compare=False, default=None)

    @property
    def name(self) -> str:
        if self.path is not None:
            return self.path
        style = self.style or 'Regular'
        return f'{self.family}-{style}.ttf'

    @property
    def value(self) -> text.Font:
        if self._font is None:
            self._font = text.get_font(self.name, self.size)
        return self._font


@dataclass
class ImageFileConfig(LoadableConfig):
    path: str
    xalign: int = 0
    yalign: int = 0
    _surface: pygame.Surface | None = field(init=False, repr=False, compare=False, default=None)

    @property
    def value(self) -> tuple[pygame.Surface, int, int]:
        if self._surface is None:
            self._surface = pygame.image.load(self.path)
        return self._surface, self.xalign, self.yalign
