#!/usr/bin/env python3

from pixelate import Pixelate
from clock import ClockApp


def main():
    pxl8 = Pixelate()
    pxl8.start_app(ClockApp(pxl8), activate=True)
    pxl8.eventloop()
    exit()


if __name__ == "__main__":
    main()
