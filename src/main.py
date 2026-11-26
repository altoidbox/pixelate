#!/usr/bin/env python3

from pixelate.pixelate import Pixelate, ShimmerEffect
from apps.clock.clock import ClockApp
from apps.weather.weather import WeatherApp


def main():
    pxl8 = Pixelate()
    pxl8.start_app(ClockApp(pxl8))
    pxl8.start_app(WeatherApp(pxl8), activate=True)
    pxl8.enable_effect(ShimmerEffect(pxl8))
    pxl8.eventloop()
    exit()


if __name__ == "__main__":
    main()
