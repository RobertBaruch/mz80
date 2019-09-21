from nmigen import *
from nmigen.asserts import *
from nmigen.hdl.ast import *
from nmigen.back import pysim

from sequencer import Sequencer
from arch import Registers
from incdec import IncDec
from mcycler import MCycler
from muxing import *

if __name__ == "__main__":
    m = Module()
    m.submodules.sequencer = sequencer = Sequencer()
    m.submodules.registers = registers = Registers()
    m.submodules.mcycler = mcycler = MCycler()
    m.submodules.incdec = incdec = IncDec(16)

    addrBus = Signal(16)
    dataBus = Signal(8)

    m.d.comb += [
        mcycler.addr.eq(addrBus),
        mcycler.refresh_addr.eq(addrBus),
        mcycler.cycle.eq(sequencer.cycle),
        mcycler.extend.eq(sequencer.extend),
        mcycler.busreq.eq(0),
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

    with m.If(
            registers.readRegister16.matches(Register16.WZ, Register16.BC,
                                             Register16.DE, Register16.HL,
                                             Register16.SP, Register16.PC)):
        m.d.comb += addrBus.eq(registers.output16)
    with m.Else():
        m.d.comb += addrBus.eq(0xFFFF)

    with m.If(
            registers.readRegister8.matches(
                Register8.B, Register8.C, Register8.D, Register8.E,
                Register8.H, Register8.L, Register8.W, Register8.Z)):
        m.d.comb += dataBus.eq(registers.output8)
    with m.Else():
        with m.If(mcycler.rd):
            with m.Switch(addrBus):
                with m.Case(0):
                    m.d.comb += dataBus.eq(0x0E)
                with m.Case(1):
                    m.d.comb += dataBus.eq(0xAB)
                with m.Default():
                    m.d.comb += dataBus.eq(0x00)
        with m.Else():
            m.d.comb += dataBus.eq(0xFF)

    ports = sequencer.ports()

    with pysim.Simulator(
            m, vcd_file=open("sequencer.vcd", "w"), traces=ports) as sim:
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
