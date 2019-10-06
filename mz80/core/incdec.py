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
        self.controls = SequencerControls()
        self.busIn = Signal(width)
        self.busOut = Signal(width)

    def elaborate(self, platform):
        m = Module()

        with m.Switch(self.controls.addrIncDecSetting):
            with m.Case(IncDecSetting.INC):
                m.d.comb += self.busOut.eq(self.busIn + 1)
            with m.Case(IncDecSetting.DEC):
                m.d.comb += self.busOut.eq(self.busIn - 1)
            with m.Default():
                m.d.comb += self.busOut.eq(self.busIn)

        return m