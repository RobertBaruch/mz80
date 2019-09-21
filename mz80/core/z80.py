from nmigen import *
from nmigen.asserts import *
from nmigen.hdl.ast import *
from nmigen.back import pysim

from .sequencer import Sequencer
from .arch import Registers
from .incdec import IncDec
from .mcycler import MCycler
from .muxing import *
from ..z80fi.z80fi import *


class Z80(Elaboratable):
    def __init__(self, include_z80fi=False):
        self.A = Signal(16)
        self.Din = Signal(8)
        self.Dout = Signal(8)
        self.hiz = Signal()

        self.nM1 = Signal()
        self.nMREQ = Signal()
        self.nIORQ = Signal()
        self.nRD = Signal()
        self.nWR = Signal()
        self.nBUSRQ = Signal()
        self.nBUSAK = Signal()

        self.include_z80fi = include_z80fi
        if self.include_z80fi:
            self.z80fi = Z80fiInterface()

    def ports(self):
        return [
            self.A, self.Din, self.Dout, self.hiz, self.nM1, self.nMREQ,
            self.nIORQ, self.nRD, self.nWR, self.nBUSRQ, self.nBUSAK
        ]

    def elaborate(self, platform):
        addrBus = Signal(16)
        dataBus = Signal(8)

        m = Module()
        m.submodules.sequencer = sequencer = Sequencer(
            include_z80fi=self.include_z80fi)
        m.submodules.registers = registers = Registers(
            include_z80fi=self.include_z80fi)
        m.submodules.mcycler = mcycler = MCycler()
        m.submodules.incdec = incdec = IncDec(16)

        m.d.comb += [
            mcycler.addr.eq(addrBus),
            mcycler.refresh_addr.eq(addrBus),
            mcycler.cycle.eq(sequencer.cycle),
            mcycler.extend.eq(sequencer.extend),
            mcycler.busreq.eq(~self.nBUSRQ),
        ]

        m.d.comb += [
            incdec.input.eq(addrBus),
            incdec.setting.eq(sequencer.addrIncDecSetting),
        ]

        m.d.comb += [
            sequencer.act.eq(mcycler.act),
            sequencer.dataBusIn.eq(dataBus),
        ]

        m.d.comb += [
            registers.useIX.eq(sequencer.useIX),
            registers.useIY.eq(sequencer.useIY),
            registers.registerSet.eq(sequencer.registerSet),
            registers.readRegister8.eq(sequencer.register8Source),
            registers.readRegister16.eq(sequencer.register16Source),
            registers.writeRegister8.eq(sequencer.register8Dest),
            registers.writeRegister16.eq(sequencer.register16Dest),
            registers.input16.eq(incdec.output),
            registers.input8.eq(dataBus),
        ]

        m.d.comb += [
            self.A.eq(addrBus),
            self.Dout.eq(dataBus),
            self.hiz.eq(mcycler.hiz),
            self.nM1.eq(~mcycler.m1),
            self.nMREQ.eq(~mcycler.mreq),
            self.nIORQ.eq(~mcycler.iorq),
            self.nRD.eq(~mcycler.rd),
            self.nWR.eq(~mcycler.wr),
            self.nBUSAK.eq(~mcycler.busack),
        ]

        with m.If(
                sequencer.register16Source.matches(
                    Register16.WZ, Register16.BC, Register16.DE, Register16.HL,
                    Register16.SP, Register16.PC)):
            m.d.comb += addrBus.eq(registers.output16)
        with m.Else():
            m.d.comb += addrBus.eq(0xFFFF)

        with m.If(
                sequencer.register8Source.matches(
                    Register8.B, Register8.C, Register8.D, Register8.E,
                    Register8.H, Register8.L, Register8.W, Register8.Z)):
            m.d.comb += dataBus.eq(registers.output8)
        with m.Else():
            with m.If(mcycler.rd):
                m.d.comb += dataBus.eq(self.Din)
            with m.Else():
                m.d.comb += dataBus.eq(0xFF)

        if self.include_z80fi:
            m.d.comb += registers.z80fi.connect(self.z80fi.registers,
                                                sequencer.z80fi.registers),
            m.d.comb += sequencer.z80fi.control.connect(self.z80fi.control),
            m.d.comb += self.z80fi.state.connect(sequencer.z80fi.state),
            m.d.comb += self.z80fi.state.dataBus.eq(dataBus),
            m.d.comb += self.z80fi.state.addrBus.eq(addrBus),

        return m


if __name__ == "__main__":
    m = Module()

    m.submodules.z80 = z80 = Z80(include_z80fi=True)
    m.submodules.z80fi = z80f = Z80fiInstrState()
    z80state = Z80fiState()

    m.d.comb += z80.z80fi.connect(z80f.iface)
    m.d.comb += z80state.connect(z80f.data)

    with m.If(~z80.nRD & ~z80.nMREQ):
        with m.Switch(z80.A):
            with m.Case(0):
                m.d.comb += z80.Din.eq(0x0E)
            with m.Case(1):
                m.d.comb += z80.Din.eq(0xAB)
            with m.Default():
                m.d.comb += z80.Din.eq(0x00)

    m.d.comb += z80.nBUSRQ.eq(1)

    with pysim.Simulator(
            m,
            vcd_file=open("z80.vcd", "w"),
            gtkw_file=open("z80.gtkw", "w"),
            traces=[
                z80state.valid, z80state.instr, z80state.operands.num,
                z80state.operands.data0
            ]) as sim:
        sim.add_clock(1e-9, domain="pos")

        def process():
            # initial reset
            yield
            yield
            yield
            yield
            yield
            yield
            yield
            yield
            yield
            yield
            yield
            yield
            yield
            yield

        sim.add_sync_process(process(), domain="pos")
        sim.run()
