from nmigen import *

from enum import Enum, unique
from .muxing import *
from ..z80fi.z80fi import *


class ALU(Elaboratable):
    def __init__(self, include_z80fi=False):
        self.input = Signal(8)
        self.output = Signal(8)
        self.controls = SequencerControls()

        self.include_z80fi = include_z80fi
        if self.include_z80fi:
            self.z80fi = Record(
                RegRecordLayout(DIR_FANOUT), name="alu_z80firegs")

    def elaborate(self, platform):
        m = Module()

        TMP = Signal(8)
        A1 = Signal(8)
        A2 = Signal(8)
        A = Array([A1, A2])
        F1 = Signal(8)
        F2 = Signal(8)
        F = Array([F1, F2])

        with m.Switch(self.controls.writeRegister8):
            with m.Case(Register8.A):
                m.d.pos += A[self.controls.registerSet].eq(self.input)
            with m.Case(Register8.F):
                m.d.pos += F[self.controls.registerSet].eq(self.input)
            with m.Case(Register8.TMP):
                m.d.pos += TMP.eq(self.input)

        with m.Switch(self.controls.readRegister8):
            with m.Case(Register8.A):
                m.d.pos += self.output.eq(A[self.controls.registerSet])
            with m.Case(Register8.F):
                m.d.pos += self.output.eq(F[self.controls.registerSet])
            with m.Case(Register8.TMP):
                m.d.pos += self.output.eq(TMP)

        if self.include_z80fi:
            regs = self.z80fi
            m.d.comb += [
                regs.eq(0),
                regs.A1.eq(A[self.controls.registerSet]),
                regs.A2.eq(A[~self.controls.registerSet]),
                regs.F1.eq(F[self.controls.registerSet]),
                regs.F2.eq(F[~self.controls.registerSet]),
            ]

        return m
