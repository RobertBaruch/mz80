from nmigen import *
from nmigen.asserts import *
from nmigen.hdl.ast import *
from nmigen.back import pysim

from .sequencer import Sequencer
from .arch import Registers
from .alu import ALU
from .incdec import IncDec
from .mcycler import MCycler
from .muxing import *
from .addralu import AddrALU
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

        self.mcycler = MCycler()

    def ports(self):
        return [
            self.A, self.Din, self.Dout, self.hiz, self.nM1, self.nMREQ,
            self.nIORQ, self.nRD, self.nWR, self.nBUSRQ, self.nBUSAK
        ]

    def elaborate(self, platform):
        addrBus = Signal(16)
        dataBus = Signal(8)
        # controls = SequencerControls()

        m = Module()
        m.submodules.sequencer = sequencer = Sequencer(
            include_z80fi=self.include_z80fi)
        m.submodules.registers = registers = Registers(
            include_z80fi=self.include_z80fi)
        m.submodules.mcycler = self.mcycler
        m.submodules.incdec = incdec = IncDec(16)
        m.submodules.alu = alu = ALU(include_z80fi=self.include_z80fi)
        m.submodules.addrALU = addrALU = AddrALU()

        mcycler = self.mcycler
        controls = sequencer.controls

        m.d.comb += [
            sequencer.act.eq(mcycler.act),
            sequencer.dataBusIn.eq(dataBus),
        ]

        m.d.comb += [
            registers.input16.eq(incdec.busOut),
            registers.dataBusIn.eq(dataBus),
            registers.controls.eq(controls),
        ]

        m.d.comb += [
            mcycler.addrBusIn.eq(addrBus),
            mcycler.cycle.eq(sequencer.cycle),
            mcycler.extend.eq(sequencer.extend),
            mcycler.busreq.eq(~self.nBUSRQ),
            mcycler.Din.eq(self.Din),
            mcycler.dataBusIn.eq(dataBus),
            mcycler.controls.eq(controls),
        ]

        m.d.comb += [
            incdec.busIn.eq(addrBus),
            incdec.controls.eq(controls),
        ]

        m.d.comb += [
            alu.dataBusIn.eq(dataBus),
            alu.controls.eq(controls),
        ]

        m.d.comb += [
            addrALU.input.eq(registers.addrALUInput),
            addrALU.dataBusIn.eq(dataBus),
            addrALU.controls.eq(controls),
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

        m.d.comb += addrBus.eq(registers.addrBusOut)
        m.d.comb += dataBus.eq(registers.dataBusOut | alu.dataBusOut
                               | addrALU.dataBusOut | mcycler.dataBusOut)

        if self.include_z80fi:
            z80registers = Record(
                RegRecordLayout(DIR_FANIN), name="z80_registers")

            # z80registers <- registers.z80fi, alu.z80fi
            m.d.comb += z80registers.connect(registers.z80fi, alu.z80fi)
            # z80registers -> sequencer.z80fi.registers
            m.d.comb += sequencer.z80fi.registers.eq(z80registers)
            # z80registers -> self.z80fi.registers
            m.d.comb += self.z80fi.registers.eq(z80registers)
            # sequencer.z80fi.control -> self.z80fi.control
            m.d.comb += sequencer.z80fi.control.connect(self.z80fi.control),
            # self.z80fi.bus -> sequencer.z80fi.bus
            m.d.comb += self.z80fi.bus.connect(sequencer.z80fi.bus),
            m.d.comb += self.z80fi.bus.data.eq(dataBus),
            m.d.comb += self.z80fi.bus.addr.eq(addrBus),

        return m


if __name__ == "__main__":
    m = Module()

    clk = Signal()
    rst = Signal()

    pos = ClockDomain()
    pos.clk = clk
    pos.rst = rst

    neg = ClockDomain(clk_edge="neg")
    neg.clk = clk
    neg.rst = rst

    m.domains.pos = pos
    m.domains.neg = neg

    m.submodules.z80 = z80 = Z80(include_z80fi=True)
    m.submodules.state = state = Z80fiInstrState()
    z80state = Z80fiState()

    m.d.comb += z80.z80fi.connect(state.iface)
    m.d.comb += z80state.connect(state.data)

    with m.If(~z80.nRD & ~z80.nMREQ):
        with m.Switch(z80.A):
            with m.Case(0):
                m.d.comb += z80.Din.eq(0xDD)
            with m.Case(1):
                m.d.comb += z80.Din.eq(0x36)
            with m.Case(2):
                m.d.comb += z80.Din.eq(0x01)
            with m.Case(3):
                m.d.comb += z80.Din.eq(0x02)
            with m.Default():
                m.d.comb += z80.Din.eq(0x00)

    m.d.comb += z80.nBUSRQ.eq(1)

    with pysim.Simulator(
            m,
            vcd_file=open("z80.vcd", "w"),
            gtkw_file=open("z80.gtkw", "w"),
            traces=[
                z80state.valid, z80state.instr, z80state.operands.num,
                z80state.operands.data0, z80state.operands.data1,
                z80state.useIX, z80state.useIY, z80.mcycler.mcycle,
                z80.mcycler.tcycle, z80.mcycler.extend
            ]) as sim:
        sim.add_clock(1e-9, domain="pos")
        sim.add_clock(1e-9, domain="neg")

        #sim.add_clock(1e-9)


        def process():
            for i in range(0, 30):
                yield Tick(domain="pos")
                yield Tick(domain="neg")

        #sim.add_sync_process(process(), domain="pos")
        sim.add_process(process())
        sim.run()
