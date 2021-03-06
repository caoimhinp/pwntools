 # -*- coding: utf-8 -*-
r"""
Module for packing and unpacking integers.

Simplifies access to the standard ``struct.pack`` and ``struct.unpack``
functions, and also adds support for packing/unpacking arbitrary-width
integers.

The packers are all context-aware for ``endian`` and ``signed`` arguments,
though they can be overridden in the parameters.

Examples:

    >>> p8(0)
    '\x00'
    >>> p32(0xdeadbeef)
    '\xef\xbe\xad\xde'
    >>> p32(0xdeadbeef, endian='big')
    '\xde\xad\xbe\xef'
    >>> with context.local(endian='big'): p32(0xdeadbeef)
    '\xde\xad\xbe\xef'

    Make a frozen packer, which does not change with context.

    >>> p=make_packer('all')
    >>> p(0xff)
    '\xff'
    >>> p(0x1ff)
    '\xff\x01'
    >>> with context.local(endian='big'): print repr(p(0x1ff))
    '\xff\x01'
"""
from ..context import context
import struct, sys
from itertools import product

mod = sys.modules[__name__]

def pack(number, word_size = None, endianness = None, sign = None, **kwargs):
    """pack(number, word_size = None, endianness = None, sign = None, **kwargs) -> str

    Packs arbitrary-sized integer.

    Word-size, endianness and signedness is done according to context.

    `word_size` can be any positive number or the string "all". Choosing the
    string "all" will output a string long enough to contain all the significant
    bits and thus be decodable by :func:`unpack`.

    `word_size` can be any positive number. The output will contain word_size/8
    rounded up number of bytes. If word_size is not a multiple of 8, it will be
    padded with zeroes up to a byte boundary.

    Arguments:
        number (int): Number to convert
        word_size (int): Word size of the converted integer or the string 'all'.
        endianness (str): Endianness of the converted integer ("little"/"big")
        sign (str): Signedness of the converted integer (False/True)
        kwargs: Anything that can be passed to context.local

    Returns:
        The packed number as a string.

    Examples:
        >>> pack(0x414243, 24, 'big', True)
        'ABC'
        >>> pack(0x414243, 24, 'little', True)
        'CBA'
        >>> pack(0x814243, 24, 'big', False)
        '\\x81BC'
        >>> pack(0x814243, 24, 'big', True)
        Traceback (most recent call last):
           ...
        ValueError: pack(): number does not fit within word_size
        >>> pack(0x814243, 25, 'big', True)
        '\\x00\\x81BC'
        >>> pack(-1, 'all', 'little', True)
        '\\xff'
        >>> pack(-256, 'all', 'big', True)
        '\\xff\\x00'
        >>> pack(0x0102030405, 'all', 'little', True)
        '\\x05\\x04\\x03\\x02\\x01'
"""
    with context.local(**kwargs):
        # Lookup in context if not found
        word_size  = word_size  or context.word_size
        endianness = endianness or context.endianness
        sign       = sign       or context.sign

        if not isinstance(number, (int,long)):
            raise ValueError("pack(): number must be of type (int,long) (got %r)" % type(number))

        if sign not in [True, False]:
            raise ValueError("pack(): sign must be either True or False (got %r)" % sign)

        if endianness not in ['little', 'big']:
            raise ValueError("pack(): endianness must be either 'little' or 'big' (got %r)" % endianness)

        # Verify that word_size make sense
        if word_size == 'all':
            if number == 0:
                word_size = 8
            elif number > 0:
                word_size = ((number.bit_length() - 1) | 7) + 1
            else:
                if sign == False:
                    raise ValueError("pack(): number does not fit within word_size")
                word_size = ((number + 1).bit_length() | 7) + 1
        elif not isinstance(word_size, (int, long)) or word_size <= 0:
            raise ValueError("pack(): word_size must be a positive integer or the string 'all'")

        if sign == True:
            limit = 1 << (word_size-1)
            if not -limit <= number < limit:
                raise ValueError("pack(): number does not fit within word_size")
        else:
            limit = 1 << word_size
            if not 0 <= number < limit:
                raise ValueError("pack(): number does not fit within word_size [%i, %r, %r]" % (0, number, limit))

        # Normalize number and size now that we have verified them
        # From now on we can treat positive and negative numbers the same
        number = number & ((1 << word_size) - 1)
        byte_size = (word_size + 7) / 8

        out = []

        for _ in range(byte_size):
            out.append(chr(number & 0xff))
            number = number >> 8

        if endianness == 'little':
            return ''.join(out)
        else:
            return ''.join(reversed(out))

def unpack(data, word_size = None, endianness = None, sign = None, **kwargs):
    """unpack(data, word_size = None, endianness = None, sign = None, **kwargs) -> int

    Packs arbitrary-sized integer.

    Word-size, endianness and signedness is done according to context.

    `word_size` can be any positive number or the string "all". Choosing the
    string "all" is equivalent to ``len(data)*8``.

    If `word_size` is not a multiple of 8, then the bits used for padding
    are discarded.

    Arguments:
        number (int): String to convert
        word_size (int): Word size of the converted integer or the string "all".
        endianness (str): Endianness of the converted integer ("little"/"big")
        sign (str): Signedness of the converted integer (False/True)
        kwargs: Anything that can be passed to context.local

    Returns:
        The unpacked number.

    Examples:
        >>> hex(unpack('\\xaa\\x55', 16, 'little', False))
        '0x55aa'
        >>> hex(unpack('\\xaa\\x55', 16, 'big', False))
        '0xaa55'
        >>> hex(unpack('\\xaa\\x55', 16, 'big', True))
        '-0x55ab'
        >>> hex(unpack('\\xaa\\x55', 15, 'big', True))
        '0x2a55'
        >>> hex(unpack('\\xff\\x02\\x03', 'all', 'little', True))
        '0x302ff'
        >>> hex(unpack('\\xff\\x02\\x03', 'all', 'big', True))
        '-0xfdfd'
    """

    with context.local(**kwargs):
        # Lookup in context if not found
        word_size  = word_size  or context.word_size
        endianness = endianness or context.endianness
        sign       = sign       or context.sign

        # Verify that word_size make sense
        if word_size == 'all':
            word_size = len(data) * 8
        elif not isinstance(word_size, (int, long)) or word_size <= 0:
            raise ValueError("unpack(): word_size must be a positive integer or the string 'all'")

        byte_size = (word_size + 7) / 8

        if byte_size != len(data):
            raise ValueError("unpack(): data must have length %d, since word_size was %d" % (byte_size, word_size))

        number = 0

        if endianness == "little":
            for c in reversed(data):
                number = (number << 8) + ord(c)
        elif endianness == "big":
            for c in data:
                number = (number << 8) + ord(c)
        else:
            raise ValueError("endianness must be either 'little' or 'big'")

        number = number & ((1 << word_size) - 1)

        if sign == False:
            return number
        elif sign == True:
            signbit = number & (1 << (word_size-1))
            return number - 2*signbit
        else:
            raise ValueError("unpack(): sign must be either True or False")


def unpack_many(data, word_size = None, endianness = None, sign = None, **kwargs):
    """unpack(data, word_size = None, endianness = None, sign = None) -> int list

    Splits `data` into groups of ``word_size//8`` bytes and calls :func:`unpack` on each group.  Returns a list of the results.

    `word_size` must be a multiple of `8` or the string "all".  In the latter case a singleton list will always be returned.

    Args
        number (int): String to convert
        word_size (int): Word size of the converted integers or the string "all".
        endianness (str): Endianness of the converted integer ("little"/"big")
        sign (str): Signedness of the converted integer (False/True)
        kwargs: Anything that can be passed to context.local

    Returns:
        The unpacked numbers.

    Examples:
        >>> map(hex, unpack_many('\\xaa\\x55\\xcc\\x33', 16, 'little', False))
        ['0x55aa', '0x33cc']
        >>> map(hex, unpack_many('\\xaa\\x55\\xcc\\x33', 16, 'big', False))
        ['0xaa55', '0xcc33']
        >>> map(hex, unpack_many('\\xaa\\x55\\xcc\\x33', 16, 'big', True))
        ['-0x55ab', '-0x33cd']
        >>> map(hex, unpack_many('\\xff\\x02\\x03', 'all', 'little', True))
        ['0x302ff']
        >>> map(hex, unpack_many('\\xff\\x02\\x03', 'all', 'big', True))
        ['-0xfdfd']
    """
    with context.local(**kwargs):
        # Lookup in context if None
        word_size  = word_size  or context.word_size

        if word_size == 'all':
            return [unpack(data, word_size, endianness, sign)]

        # Currently we only group on byte boundaries
        if word_size % 8 != 0:
            raise ValueError("unpack_many(): word_size must be a multiple of 8")

        out = []
        n = word_size // 8
        for i in range(0, len(data), n):
            out.append(unpack(data[i:i+n], word_size, endianness, sign))

        return out


#
# Make individual packers, e.g. _p8lu
#
ops   = {'p': struct.pack, 'u': lambda *a: struct.unpack(*a)[0]}
sizes = {8:'b', 16:'h', 32:'i', 64:'q'}
ends  = ['b','l']
signs = ['s','u']

def make_single(op,size,end,sign):
    name = '_%s%s%s%s' % (op, size, end, sign)
    fmt  = sizes[size]
    end = '>' if end == 'b' else '<'

    if sign == 'u':
        fmt = fmt.upper()
    fmt = end+fmt

    def routine(data):
        return ops[op](fmt,data)
    routine.__name__ = name

    return name, routine

for op,size,end,sign in product(ops, sizes, ends, signs):
    name, routine = make_single(op,size,end,sign)
    setattr(mod, name, routine)

return_types     = {'p': 'str', 'u': 'int'}
op_verbs         = {'p': 'pack', 'u': 'unpack'}
arg_doc          = {'p': 'number (int): Number to convert',
                    'u': 'data (str): String to convert'}
rv_doc           = {'p': 'The packed number as a string',
                    'u': 'The unpacked number'}

#
# Make normal user-oriented packers, e.g. p8
#
def make_multi(op, size):

    name = "%s%s" % (op,size)

    ls = getattr(mod, "_%sls" % (name))
    lu = getattr(mod, "_%slu" % (name))
    bs = getattr(mod, "_%sbs" % (name))
    bu = getattr(mod, "_%sbu" % (name))

    def routine(number, endianness=None, sign=None, **kwargs):
        with context.local(endianness=endianness, sign=sign, **kwargs):
            endian = context.endian
            signed = context.signed
            return {("little", True  ): ls,
                    ("little", False):  lu,
                    ("big",    True  ): bs,
                    ("big",    False):  bu}[endian, signed](number)

    routine.__name__ = name
    routine.__doc__  = """
    %s%s(number, **kwargs) -> %s

    %ss an %s-bit integer

    Arguments:
        %s
        endianness (str): Endianness of the converted integer ("little"/"big")
        sign (str): Signedness of the converted integer ("unsigned"/"signed")
        kwargs (dict): Arguments passed to context.local(), such as
            ``endian`` or ``signed``.

    Returns:
        %s
    """ % (op, size, return_types[op], op_verbs[op].title(), size, arg_doc[op], rv_doc[op])

    return name, routine


for op,size in product(ops, sizes):
    name, routine = make_multi(op,size)
    setattr(mod, name, routine)

def make_packer(word_size = None, endianness = None, sign = None, **kwargs):
    """make_packer(word_size = None, endianness = None, sign = None) -> number → str

    Creates a packer by "freezing" the given arguments.

    Semantically calling ``make_packer(w, e, s)(data)`` is equivalent to calling
    ``pack(data, w, e, s)``. If word_size is one of 8, 16, 32 or 64, it is however
    faster to call this function, since it will then use a specialized version.

    Arguments:
        word_size (int): The word size to be baked into the returned packer or the string all.
        endianness (str): The endianness to be baked into the returned packer. ("little"/"big")
        sign (str): The signness to be baked into the returned packer. ("unsigned"/"signed")
        kwargs: Additional context flags, for setting by alias (e.g. ``endian=`` rather than index)

    Returns:
        A function, which takes a single argument in the form of a number and returns a string
        of that number in a packed form.

    Examples:
        >>> p = make_packer(32, 'little', 'unsigned')
        >>> p
        <function _p32lu at 0x...>
        >>> p(42)
        '*\\x00\\x00\\x00'
        >>> p(-1)
        Traceback (most recent call last):
            ...
        error: integer out of range for 'I' format code
        >>> make_packer(33, 'little', 'unsigned')
        <function <lambda> at 0x...>
"""
    with context.local(endianness=endianness, sign=sign, **kwargs):
        word_size  = word_size or context.word_size
        endianness = context.endianness
        sign       = context.sign

        if word_size in [8, 16, 32, 64]:
            endianness = 1 if endianness == 'big'    else 0

            return {
                (8, 0, 0):  _p8lu,
                (8, 0, 1):  _p8ls,
                (8, 1, 0):  _p8bu,
                (8, 1, 1):  _p8bs,
                (16, 0, 0): _p16lu,
                (16, 0, 1): _p16ls,
                (16, 1, 0): _p16bu,
                (16, 1, 1): _p16bs,
                (32, 0, 0): _p32lu,
                (32, 0, 1): _p32ls,
                (32, 1, 0): _p32bu,
                (32, 1, 1): _p32bs,
                (64, 0, 0): _p64lu,
                (64, 0, 1): _p64ls,
                (64, 1, 0): _p64bu,
                (64, 1, 1): _p64bs,
            }[word_size, endianness, sign]
        else:
            return lambda number: pack(number, word_size, endianness, sign)

def make_unpacker(word_size = None, endianness = None, sign = None, **kwargs):
    """make_unpacker(word_size = None, endianness = None, sign = None,  **kwargs) -> str → number

    Creates a unpacker by "freezing" the given arguments.

    Semantically calling ``make_unpacker(w, e, s)(data)`` is equivalent to calling
    ``unpack(data, w, e, s)``. If word_size is one of 8, 16, 32 or 64, it is however
    faster to call this function, since it will then use a specialized version.

    Arguments:
        word_size (int): The word size to be baked into the returned packer.
        endianness (str): The endianness to be baked into the returned packer. ("little"/"big")
        sign (str): The signness to be baked into the returned packer. ("unsigned"/"signed")
        kwargs: Additional context flags, for setting by alias (e.g. ``endian=`` rather than index)

    Returns:
        A function, which takes a single argument in the form of a string and returns a number
        of that string in an unpacked form.

    Examples:
        >>> u = make_unpacker(32, 'little', 'unsigned')
        >>> u
        <function _u32lu at 0x...>
        >>> hex(u('/bin'))
        '0x6e69622f'
        >>> u('abcde')
        Traceback (most recent call last):
            ...
        error: unpack requires a string argument of length 4
        >>> make_unpacker(33, 'little', 'unsigned')
        <function <lambda> at 0x...>
"""
    # Validate
    with context.local(endianness=endianness, sign=sign, **kwargs):
        word_size  = word_size or context.word_size
        endianness = context.endianness
        sign       = context.sign

        if word_size in [8, 16, 32, 64]:
            endianness = 1 if endianness == 'big'    else 0

            return {
                (8, 0, 0):  _u8lu,
                (8, 0, 1):  _u8ls,
                (8, 1, 0):  _u8bu,
                (8, 1, 1):  _u8bs,
                (16, 0, 0): _u16lu,
                (16, 0, 1): _u16ls,
                (16, 1, 0): _u16bu,
                (16, 1, 1): _u16bs,
                (32, 0, 0): _u32lu,
                (32, 0, 1): _u32ls,
                (32, 1, 0): _u32bu,
                (32, 1, 1): _u32bs,
                (64, 0, 0): _u64lu,
                (64, 0, 1): _u64ls,
                (64, 1, 0): _u64bu,
                (64, 1, 1): _u64bs,
            }[word_size, endianness, sign]
        else:
            return lambda number: unpack(number, word_size, endianness, sign)



def _flat(args, preprocessor, packer):
    out = []
    for arg in args:

        if not isinstance(arg, (list, tuple)):
            arg_ = preprocessor(arg)
            if arg_ != None:
                arg = arg_

        if isinstance(arg, (list, tuple)):
            out.append(_flat(arg, preprocessor, packer))
        elif isinstance(arg, str):
            out.append(arg)
        elif isinstance(arg, unicode):
            out.append(arg.encode('utf8'))
        elif isinstance(arg, (int, long)):
            out.append(packer(arg))
        else:
            raise ValueError("flat(): Flat does not support values of type %s" % type(arg))
    return ''.join(out)


def flat(*args, **kwargs):
    """flat(*args, preprocessor = None, word_size = None, endianness = None, sign = None)

    Flattens the arguments into a string.

    This function takes an arbitrary number of arbitrarily nested lists and
    tuples. It will then find every string and number inside those and flatten
    them out. Strings are inserted directly while numbers are packed using the
    :func:`pack` function.

    The three kwargs `word_size`, `endianness` and `sign` will default to using
    values in :mod:`pwnlib.context` if not specified as an argument.

    Arguments:
      args: Values to flatten
      preprocessor (function): Gets called on every element to optionally
         transform the element before flattening. If :const:`None` is
         returned, then the original value is uded.
      word_size (int): Word size of the converted integer.
      endianness (str): Endianness of the converted integer ("little"/"big").
      sign (str): Signedness of the converted integer (False/True)

    Examples:
      >>> flat(1, "test", [[["AB"]*2]*3], endianness = 'little', word_size = 16, sign = False)
      '\\x01\\x00testABABABABABAB'
      >>> flat([1, [2, 3]], preprocessor = lambda x: str(x+1))
      '234'
"""

    preprocessor = kwargs.pop('preprocessor', lambda x: None)
    word_size    = kwargs.pop('word_size', None)
    endianness   = kwargs.pop('endianness', None)
    sign         = kwargs.pop('sign', None)

    if kwargs != {}:
        raise TypeError("flat() does not support argument %r" % kwargs.popitem()[0])

    return _flat(args, preprocessor, make_packer(word_size, endianness, sign))
