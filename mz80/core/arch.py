from nmigen import *
from nmigen.cli import main
from nmigen.asserts import *

from .muxing import *
from ..z80fi.z80fi import *


class Registers(Elaboratable):
    """Main registers.

    Consists of the standard B, C, D, E, H, L registers and their
    secondary counterparts, and the IX, IY, SP, and PC registers.
    """

    def __init__(self, include_z80fi=False):
        # registerSet chooses whether we use the W set or the W2 set.
        self.registerSet = Signal()
        self.useIX = Signal()
        self.useIY = Signal()

        self.output8 = Signal(8)
        self.output16 = Signal(16)
        self.input8 = Signal(8)
        self.input16 = Signal(16)

        self.readRegister8 = Signal.enum(Register8)
        self.writeRegister8 = Signal.enum(Register8)
        self.readRegister16 = Signal.enum(Register16)
        self.writeRegister16 = Signal.enum(Register16)

        self.W1 = Signal(8)
        self.W2 = Signal(8)
        self.W = Array([self.W1, self.W2])
        self.Z1 = Signal(8)
        self.Z2 = Signal(8)
        self.Z = Array([self.Z1, self.Z2])
        self.B1 = Signal(8)
        self.B2 = Signal(8)
        self.B = Array([self.B1, self.B2])
        self.C1 = Signal(8)
        self.C2 = Signal(8)
        self.C = Array([self.C1, self.C2])
        self.D1 = Signal(8)
        self.D2 = Signal(8)
        self.D = Array([self.D1, self.D2])
        self.E1 = Signal(8)
        self.E2 = Signal(8)
        self.E = Array([self.E1, self.E2])
        self.H1 = Signal(8)
        self.H2 = Signal(8)
        self.H = Array([self.H1, self.H2])
        self.L1 = Signal(8)
        self.L2 = Signal(8)
        self.L = Array([self.L1, self.L2])
        self.IXh = Signal(8)
        self.IXl = Signal(8)
        self.IYh = Signal(8)
        self.IYl = Signal(8)
        self.SPh = Signal(8)
        self.SPl = Signal(8)
        self.PCh = Signal(8)
        self.PCl = Signal(8)

        self.include_z80fi = include_z80fi
        if self.include_z80fi:
            self.z80fi = Record(RegRecordLayout(DIR_FANOUT))

    def ports(self):
        return [
            self.registerSet, self.useIX, self.useIY, self.output8,
            self.output16, self.input8, self.input16, self.readRegister8,
            self.writeRegister8, self.readRegister16
        ]

    def elaborate(self, platform):
        m = Module()

        conflict = Signal()
        m.d.comb += conflict.eq(((self.writeRegister16 == Register16.WZ) &
                self.writeRegister8.matches(Register8.W, Register8.Z)) |
            ((self.writeRegister16 == Register16.BC) &
                self.writeRegister8.matches(Register8.B, Register8.C)) |
            ((self.writeRegister16 == Register16.DE) &
                self.writeRegister8.matches(Register8.D, Register8.E)) |
            ((self.writeRegister16 == Register16.HL) &
                self.writeRegister8.matches(Register8.H, Register8.L)))

        with m.Switch(self.readRegister8):
            with m.Case(Register8.W):
                m.d.comb += self.output8.eq(self.W[self.registerSet])
            with m.Case(Register8.Z):
                m.d.comb += self.output8.eq(self.Z[self.registerSet])
            with m.Case(Register8.B):
                m.d.comb += self.output8.eq(self.B[self.registerSet])
            with m.Case(Register8.C):
                m.d.comb += self.output8.eq(self.C[self.registerSet])
            with m.Case(Register8.D):
                m.d.comb += self.output8.eq(self.D[self.registerSet])
            with m.Case(Register8.E):
                m.d.comb += self.output8.eq(self.E[self.registerSet])
            with m.Case(Register8.H):
                with m.If(self.useIX):
                    m.d.comb += self.output8.eq(self.IXh)
                with m.Elif(self.useIY):
                    m.d.comb += self.output8.eq(self.IYh)
                with m.Else():
                    m.d.comb += self.output8.eq(self.H[self.registerSet])
            with m.Case(Register8.L):
                with m.If(self.useIX):
                    m.d.comb += self.output8.eq(self.IXl)
                with m.Elif(self.useIY):
                    m.d.comb += self.output8.eq(self.IYl)
                with m.Else():
                    m.d.comb += self.output8.eq(self.L[self.registerSet])
            with m.Default():
                m.d.comb += self.output8.eq(0)

        with m.If(~conflict):
            with m.Switch(self.writeRegister8):
                with m.Case(Register8.W):
                    m.d.pos += self.W[self.registerSet].eq(self.input8)
                with m.Case(Register8.Z):
                    m.d.pos += self.Z[self.registerSet].eq(self.input8)
                with m.Case(Register8.B):
                    m.d.pos += self.B[self.registerSet].eq(self.input8)
                with m.Case(Register8.C):
                    m.d.pos += self.C[self.registerSet].eq(self.input8)
                with m.Case(Register8.D):
                    m.d.pos += self.E[self.registerSet].eq(self.input8)
                with m.Case(Register8.E):
                    m.d.pos += self.E[self.registerSet].eq(self.input8)
                with m.Case(Register8.H):
                    with m.If(self.useIX):
                        m.d.comb += self.output8.eq(self.IXh)
                    with m.Elif(self.useIY):
                        m.d.comb += self.output8.eq(self.IYh)
                    with m.Else():
                        m.d.pos += self.H[self.registerSet].eq(self.input8)
                with m.Case(Register8.L):
                    with m.If(self.useIX):
                        m.d.comb += self.output8.eq(self.IXl)
                    with m.Elif(self.useIY):
                        m.d.comb += self.output8.eq(self.IYl)
                    with m.Else():
                        m.d.pos += self.L[self.registerSet].eq(self.input8)

        with m.Switch(self.readRegister16):
            with m.Case(Register16.WZ):
                m.d.comb += self.output16.eq(self.WZ)
            with m.Case(Register16.BC):
                m.d.comb += self.output16.eq(self.BC)
            with m.Case(Register16.DE):
                m.d.comb += self.output16.eq(self.DE)
            with m.Case(Register16.HL):
                with m.If(self.useIX):
                    m.d.comb += self.output16.eq(self.IX)
                with m.Elif(self.useIY):
                    m.d.comb += self.output16.eq(self.IY)
                with m.Else():
                    m.d.comb += self.output16.eq(self.HL)
            with m.Case(Register16.SP):
                m.d.comb += self.output16.eq(self.SP)
            with m.Case(Register16.PC):
                m.d.comb += self.output16.eq(self.PC)
            with m.Default():
                m.d.comb += self.output16.eq(0)

        with m.If(~conflict):
            with m.Switch(self.writeRegister16):
                with m.Case(Register16.WZ):
                    m.d.pos += self.WZ.eq(self.input16)
                with m.Case(Register16.BC):
                    m.d.pos += self.BC.eq(self.input16)
                with m.Case(Register16.DE):
                    m.d.pos += self.DE.eq(self.input16)
                with m.Case(Register16.HL):
                    with m.If(self.useIX):
                        m.d.pos += self.IX.eq(self.input16)
                    with m.Elif(self.useIY):
                        m.d.pos += self.IY.eq(self.input16)
                    with m.Else():
                        m.d.pos += self.HL.eq(self.input16)
                with m.Case(Register16.SP):
                    m.d.pos += self.SP.eq(self.input16)
                with m.Case(Register16.PC):
                    m.d.pos += self.PC.eq(self.input16)

        if self.include_z80fi:
            m.d.comb += self.copy_regs()

        return m

    def copy_regs(self):
        regs = self.z80fi
        return [
            regs.eq(0),
            regs.W1.eq(self.W[self.registerSet]),
            regs.W2.eq(self.W[~self.registerSet]),
            regs.Z1.eq(self.Z[self.registerSet]),
            regs.Z2.eq(self.Z[~self.registerSet]),
            regs.B1.eq(self.B[self.registerSet]),
            regs.B2.eq(self.B[~self.registerSet]),
            regs.C1.eq(self.C[self.registerSet]),
            regs.C2.eq(self.C[~self.registerSet]),
            regs.D1.eq(self.D[self.registerSet]),
            regs.D2.eq(self.D[~self.registerSet]),
            regs.E1.eq(self.E[self.registerSet]),
            regs.E2.eq(self.E[~self.registerSet]),
            regs.H1.eq(self.H[self.registerSet]),
            regs.H2.eq(self.H[~self.registerSet]),
            regs.L1.eq(self.L[self.registerSet]),
            regs.L2.eq(self.L[~self.registerSet]),
            regs.IX.eq(self.IX),
            regs.IY.eq(self.IY),
            regs.SP.eq(self.SP),
            regs.PC.eq(self.PC),
        ]

    @property
    def WZ(self):
        return Cat([self.Z[self.registerSet], self.W[self.registerSet]])

    @property
    def BC(self):
        return Cat([self.C[self.registerSet], self.B[self.registerSet]])

    @property
    def DE(self):
        return Cat([self.E[self.registerSet], self.D[self.registerSet]])

    @property
    def HL(self):
        return Cat([self.L[self.registerSet], self.H[self.registerSet]])

    @property
    def IX(self):
        return Cat([self.IXl, self.IXh])

    @property
    def IY(self):
        return Cat([self.IYl, self.IYh])

    @property
    def SP(self):
        return Cat([self.SPl, self.SPh])

    @property
    def PC(self):
        return Cat([self.PCl, self.PCh])


class Arch(Elaboratable):
    def __init__(self):
        pass

    def elaborate(self, platform):
        m = Module()

        return m


if __name__ == "__main__":
    clk = Signal()
    rst = Signal()

    pos = ClockDomain()
    pos.clk = clk
    pos.rst = rst

    neg = ClockDomain(clk_edge="neg")
    neg.clk = clk
    neg.rst = rst

    regs = Registers()

    m = Module()
    m.domains.pos = pos
    m.domains.neg = neg
    m.submodules.regs = regs

    main(m, ports=[clk, rst] + regs.ports(), platform="formal")
