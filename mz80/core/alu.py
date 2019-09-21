from nmigen import *

from enum import Enum, unique


@unique
class ALUFunc(Enum):
    ADD = 1


class ALU(Elaboratable):
    def __init__(self):
        self.TMP = Signal(8)
        self.A = Signal(8)
        self.A2 = Signal(8)
        self.F = Signal(8)
        self.F2 = Signal(8)
        self.out = Signal(8)
        self.func = ALUFunc()

    def elaborate(self, platform):
        m = Module()

        return m
