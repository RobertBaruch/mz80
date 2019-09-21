from nmigen import *
from nmigen.hdl.rec import *

from enum import Enum, unique


class SequencerControls(Record):
    def __init__(self):
        super().__init__(
            Layout([
                ("dataBusSource", Signal.enum(DataBusSource).shape(),
                 DIR_FANOUT),
                ("dataBusDest", Signal.enum(DataBusDestination).shape(),
                 DIR_FANOUT),
                ("register8Source", Signal.enum(Register8).shape(),
                 DIR_FANOUT),
                ("register16Source", Signal.enum(Register16).shape(),
                 DIR_FANOUT),
                ("register8Dest", Signal.enum(Register8).shape(), DIR_FANOUT),
                ("register16Dest", Signal.enum(Register16).shape(),
                 DIR_FANOUT),
                ("addrIncDecSetting", Signal.enum(IncDecSetting).shape(),
                 DIR_FANOUT),
            ]))


@unique
class Register8(Enum):
    I = 0
    R = 1
    W = 2
    Z = 3
    B = 4
    C = 5
    D = 6
    E = 7
    H = 8
    L = 9
    A = 10
    F = 11
    INVALID = 12

    @classmethod
    def r(cls, value):
        return Array([
            Register8.B, Register8.C, Register8.D, Register8.E, Register8.H,
            Register8.L, Register8.INVALID, Register8.A
        ])[value]


@unique
class Register16(Enum):
    WZ = 0
    BC = 1
    DE = 2
    HL = 3
    SP = 4
    PC = 5
    ADDR_ALU = 6
    INVALID = 7


@unique
class DataBusDestination(Enum):
    I = 0
    R = 1
    W = 2
    Z = 3
    B = 4
    C = 5
    D = 6
    E = 7
    H = 8
    L = 9
    A = 10
    F = 11
    OFFSET = 12
    TMP = 13
    INSTR = 14
    DATABUFF = 15
    INVALID = 16

    @classmethod
    def r(cls, value):
        return Array([
            DataBusDestination.B, DataBusDestination.C, DataBusDestination.D,
            DataBusDestination.E, DataBusDestination.H, DataBusDestination.L,
            DataBusDestination.INVALID, DataBusDestination.A
        ])[value]


@unique
class DataBusSource(Enum):
    I = 0
    R = 1
    W = 2
    Z = 3
    B = 4
    C = 5
    D = 6
    E = 7
    H = 8
    L = 9
    A = 10
    F = 11
    ALU = 12
    DATABUFF = 13
    TMP = 14
    INVALID = 15

    @classmethod
    def r(cls, value):
        return Array([
            DataBusSource.B, DataBusSource.C, DataBusSource.D, DataBusSource.E,
            DataBusSource.H, DataBusSource.L, DataBusSource.INVALID,
            DataBusSource.A
        ])[value]


@unique
class AddrBusSource(Enum):
    WZ = 0
    BC = 1
    DE = 2
    HL = 3
    SP = 4
    PC = 5
    ADDR_ALU = 6
    INVALID = 7


@unique
class AddrIncDecDestination(Enum):
    WZ = 0
    BC = 1
    DE = 2
    HL = 3
    SP = 4
    PC = 5
    INVALID = 6


@unique
class AddrALUSource(Enum):
    WZ = 0
    BC = 1
    DE = 2
    HL = 3
    SP = 4
    PC = 5
    INVALID = 6


@unique
class IncDecSetting(Enum):
    ZERO = 0
    INC = 1
    DEC = 2
