from nmigen import *
from nmigen.cli import main
from nmigen.asserts import *
from enum import Enum, unique, IntEnum

# Two different types of "enums".


class Thing(object):
    """A fake enumerated value.

    This isn't actually an Enum, but is just a bag of constants,
    and not at all Pythonic.
    """
    DOG = 0
    CAT = 1
    SQUIRREL = 2

    @classmethod
    def signal(cls):
        """Returns a Signal with the right number of bits for the Enum.

        src_loc_at tells nMigen which stack frame to get the variable
        name from, so the one above this one.
        """
        return Signal.range(0, 3, src_loc_at=1)


@unique
class ConstingEnumThing(Enum):
    """A real Enum.

    In general, we shouldn't care what the actual value of an enum
    is. If you do, you probably don't want an enum but a Const.

    We'll see later that the enum values don't matter. You can auto() them,
    or even use strings.
    """
    DOG = 0
    CAT = 1
    SQUIRREL = 2

    @classmethod
    def signal(cls):
        """Returns a Signal with the right number of bits for the Enum.

        src_loc_at tells nMigen which stack frame to get the variable
        name from, so the one above this one.
        """
        return Signal.range(0, 3, src_loc_at=1)

    @property
    def const(self):
        """Returns a Const with the right number of bits for the Enum.

        Although we use self.value, we'll see later on that we can
        dispense with that.
        """
        return Const(self.value, ConstingEnumThing.signal().shape())


class CatDetector(Elaboratable):
    """Uses Thing, which isn't an Enum.

    This issues a warning because width(Thing.CAT) = 1, and
    width(Thing.DOG) = 2.
    """

    def __init__(self):
        self.input = Thing.signal()
        self.output = Signal()

    def elaborate(self, platform):
        m = Module()
        self.detectCat(m, Thing.CAT)
        return m

    def detectCat(self, m, comparand):
        with m.Switch(comparand):
            with m.Case(Thing.DOG, Thing.SQUIRREL):
                m.d.comb += self.output.eq(0)
            with m.Default():
                m.d.comb += self.output.eq(1)


# This is the way we want things to work:
#
# But, we get an error:
# TypeError: Object '<ConstingEnumThing.CAT: 1>' is not an nMigen value
#
# class EnumCatDetector(Elaboratable):
#     def __init__(self):
#         self.input = ConstingEnumThing.signal()
#         self.output = Signal()

#     def elaborate(self, platform):
#         m = Module()
#         self.detectCat(m, ConstingEnumThing.CAT)
#         return m

#     def detectCat(self, m, comparand):
#         with m.Switch(comparand):
#             with m.Case(ConstingEnumThing.DOG,
#                         ConstingEnumThing.SQUIRREL):
#                 m.d.comb += self.output.eq(0)
#             with m.Default():
#                 m.d.comb += self.output.eq(1)


class EnumValueCatDetector(Elaboratable):
    """
    We can try to fix the error by using .value on all the enum values. But
    we run into the same width warning.
    """

    def __init__(self):
        self.input = ConstingEnumThing.signal()
        self.output = Signal()

    def elaborate(self, platform):
        m = Module()
        self.detectCat(m, ConstingEnumThing.CAT.value)
        return m

    def detectCat(self, m, comparand):
        with m.Switch(comparand):
            with m.Case(ConstingEnumThing.DOG.value,
                        ConstingEnumThing.SQUIRREL.value):
                m.d.comb += self.output.eq(0)
            with m.Default():
                m.d.comb += self.output.eq(1)


# We can't use the Const version on all the enum values, because:
#
# File "/home/robertbaruch/.local/lib/python3.6/site-packages/nmigen/hdl/dsl.py", line 286, in Case
#    switch_data["cases"][new_values] = self._statements
# TypeError: unhashable type: 'Const'
#
# class EnumConstCatDetector(Elaboratable):
#     def __init__(self):
#         self.input = ConstingEnumThing.signal()
#         self.output = Signal()

#     def elaborate(self, platform):
#         m = Module()
#         self.detectCat(m, ConstingEnumThing.CAT.const)
#         return m

#     def detectCat(self, m, comparand):
#         with m.Switch(comparand):
#             with m.Case(ConstingEnumThing.DOG.const, ConstingEnumThing.const):
#                 m.d.comb += self.output.eq(0)
#             with m.Default():
#                 m.d.comb += self.output.eq(1)


class EnumConstCatDetector(Elaboratable):
    """
    This is how you can use the Enum, but it's not great because
    now you have to remember when to use .value and when to use .const.

    And you still have to care about the actual numeric values of the Enum
    values, which isn't great.
    """

    def __init__(self):
        self.input = ConstingEnumThing.signal()
        self.output = Signal()

    def elaborate(self, platform):
        m = Module()
        self.detectCat(m, ConstingEnumThing.CAT.const)
        return m

    def detectCat(self, m, comparand):
        with m.Switch(comparand):
            with m.Case(ConstingEnumThing.DOG.value,
                        ConstingEnumThing.SQUIRREL.value):
                m.d.comb += self.output.eq(0)
            with m.Default():
                m.d.comb += self.output.eq(1)


def enumToConst(v):
    """Converts an Enum value to a Const of the correct size for the Enum.
    """
    assert (isinstance(v, Enum))
    s = Signal.range(0, len(type(v)))
    return Const(enumToValue(v), s.shape())


def enumToValue(v):
    """Converts an Enum value to a Value of the correct size for the Enum.

    Note that we do not care what the actual numeric values of the Enum
    values are. All we care about is that they are unique, start from 0,
    and monotonically increase by 1.

    O(N), but there's no reason you can't memoize a hashtable.
    """
    assert (isinstance(v, Enum))
    return list(type(v)).index(v)


def enumToSignal(t):
    """Converts an Enum type to a Signal of the correct size for the Enum.

    This could be useful if the Signal constructor accepts an Enum.
    """
    assert (issubclass(t, Enum))
    return Signal.range(0, len(t), src_loc_at=1)


class IdealEnumCatDetector(Elaboratable):
    """
    This is the ideal, if we imagine that Switch accepts Enum values and calls
    enumToConst() on them, Case accepts Enum values and calls enumToValue()
    on them, and Signal() accepts Enum classes and calls enumToSignal() on them.
    """

    def __init__(self):
        self.input = enumToSignal(ConstingEnumThing)
        self.output = Signal()

    def elaborate(self, platform):
        m = Module()
        self.detectCat(m, ConstingEnumThing.CAT)
        return m

    def detectCat(self, m, comparand):
        with m.Switch(enumToConst(comparand)):
            with m.Case(
                    enumToValue(ConstingEnumThing.DOG),
                    enumToValue(ConstingEnumThing.SQUIRREL)):
                m.d.comb += self.output.eq(0)
            with m.Default():
                m.d.comb += self.output.eq(1)


class OtherUses(Elaboratable):
    def __init__(self):
        self.input = enumToSignal(ConstingEnumThing)
        self.output1 = Signal()
        self.output2 = enumToSignal(ConstingEnumThing)
        self.output3 = Signal()

    def elaborate(self, platform):
        m = Module()
        with m.If(self.input == enumToValue(ConstingEnumThing.CAT)):
            m.d.comb += self.output1.eq(1)
        with m.Else():
            m.d.comb += self.output1.eq(0)

        # These should be disallowed, as should any math on enum values
        # except equality/inequality comparison.
        m.d.comb += self.output2.eq((self.input < 1) | (1 + self.input))

        # matches should allow Enums.
        m.d.comb += self.output3.eq(
            self.input.matches(enumToValue(ConstingEnumThing.CAT)))
        return m


class IntThing(IntEnum):
    """An enumerated value based on IntEnum.
    """
    DOG = 0
    CAT = 1
    SQUIRREL = 2

    @classmethod
    def signal(cls):
        """Returns a Signal with the right number of bits for the Enum.

        src_loc_at tells nMigen which stack frame to get the variable
        name from, so the one above this one.
        """
        return Signal.range(0, 3, src_loc_at=1)

    @property
    def const(self):
        """Returns a Const with the right number of bits for the Enum.

        Although we use self.value, we'll see later on that we can
        dispense with that.
        """
        return Const(self.value, ConstingEnumThing.signal().shape())


class IntEnumCatDetector(Elaboratable):
    """CatDetector using IntEnum.

    You can dispense with .value, but you must still use .const.
    """

    def __init__(self):
        self.input = IntThing.signal()
        self.output = Signal()

    def elaborate(self, platform):
        m = Module()
        self.detectCat(m, IntThing.CAT.const)
        return m

    def detectCat(self, m, comparand):
        with m.Switch(comparand):
            with m.Case(IntThing.DOG, IntThing.SQUIRREL):
                m.d.comb += self.output.eq(0)
            with m.Default():
                m.d.comb += self.output.eq(1)


if __name__ == "__main__":
    meow = CatDetector()
    # meow2 = EnumCatDetector()
    meow3 = EnumValueCatDetector()
    meow4 = EnumConstCatDetector()
    meow5 = IdealEnumCatDetector()
    meow6 = OtherUses()
    meow7 = IntEnumCatDetector()

    m = Module()
    m.submodules.meow = meow
    # m.submodules.meow2 = meow2
    m.submodules.meow3 = meow3
    m.submodules.meow4 = meow4
    m.submodules.meow5 = meow5
    m.submodules.meow6 = meow6
    m.submodules.meow7 = meow7

    main(
        m,
        ports=[
            meow.input,
            meow.output,
            # meow2.input, meow2.output,
            meow3.input,
            meow3.output,
            meow4.input,
            meow4.output,
            meow5.input,
            meow5.output,
            meow6.input,
            meow6.output1,
            meow6.output2,
            meow6.output3,
            meow7.input,
            meow7.output
        ])
