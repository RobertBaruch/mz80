from enum import Enum, unique
from nmigen import *
from nmigen.cli import main
from nmigen.asserts import *

from .muxing import *


class IncDec(Elaboratable):
    """An incrementer/decrementer.

    Can increment, decrement, or just pass through a value.
    """

    def __init__(self, width):
        self.input = Signal(width)
        self.output = Signal(width)
        self.setting = Signal.enum(IncDecSetting)

    def ports(self):
        return [self.input, self.output, self.setting]

    def elaborate(self, platform):
        m = Module()

        with m.Switch(self.setting):
            with m.Case(IncDecSetting.INC):
                m.d.comb += self.output.eq(self.input + 1)
            with m.Case(IncDecSetting.DEC):
                m.d.comb += self.output.eq(self.input - 1)
            with m.Default():
                m.d.comb += self.output.eq(self.input)

        return m