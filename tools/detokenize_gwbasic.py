#!/usr/bin/env python3
"""Destokeniza programas GW-BASIC / IBM BASICA (archivos .BAS binarios, primer byte 0xFF)."""

import math
import re
import sys

TOKENS = {
    0x81: "END",
    0x82: "FOR",
    0x83: "NEXT",
    0x84: "DATA",
    0x85: "INPUT",
    0x86: "DIM",
    0x87: "READ",
    0x88: "LET",
    0x89: "GOTO",
    0x8A: "RUN",
    0x8B: "IF",
    0x8C: "RESTORE",
    0x8D: "GOSUB",
    0x8E: "RETURN",
    0x8F: "REM",
    0x90: "STOP",
    0x91: "PRINT",
    0x92: "CLEAR",
    0x93: "LIST",
    0x94: "NEW",
    0x95: "ON",
    0x96: "WAIT",
    0x97: "DEF",
    0x98: "POKE",
    0x99: "CONT",
    0x9A: "(Undefined)",
    0x9B: "(Undefined)",
    0x9C: "OUT",
    0x9D: "LPRINT",
    0x9E: "LLIST",
    0x9F: "(Undefined)",
    0xA0: "WIDTH",
    0xA1: "ELSE",
    0xA2: "TRON",
    0xA3: "TROFF",
    0xA4: "SWAP",
    0xA5: "ERASE",
    0xA6: "EDIT",
    0xA7: "ERROR",
    0xA8: "RESUME",
    0xA9: "DELETE",
    0xAA: "AUTO",
    0xAB: "RENUM",
    0xAC: "DEFSTR",
    0xAD: "DEFINT",
    0xAE: "DEFSNG",
    0xAF: "DEFDBL",
    0xB0: "LINE",
    0xB1: "WHILE",
    0xB2: "WEND",
    0xB3: "CALL",
    0xB4: "(Undefined)",
    0xB5: "(Undefined)",
    0xB6: "(Undefined)",
    0xB7: "WRITE",
    0xB8: "OPTION",
    0xB9: "RANDOMIZE",
    0xBA: "OPEN",
    0xBB: "CLOSE",
    0xBC: "LOAD",
    0xBD: "MERGE",
    0xBE: "SAVE",
    0xBF: "COLOR",
    0xC0: "CLS",
    0xC1: "MOTOR",
    0xC2: "BSAVE",
    0xC3: "BLOAD",
    0xC4: "SOUND",
    0xC5: "BEEP",
    0xC6: "PSET",
    0xC7: "PRESET",
    0xC8: "SCREEN",
    0xC9: "KEY",
    0xCA: "LOCATE",
    0xCB: "(Undefined)",
    0xCC: "TO",
    0xCD: "THEN",
    0xCE: "TAB(",
    0xCF: "STEP",
    0xD0: "USR",
    0xD1: "FN",
    0xD2: "SPC(",
    0xD3: "NOT",
    0xD4: "ERL",
    0xD5: "ERR",
    0xD6: "STRING$",
    0xD7: "USING",
    0xD8: "INSTR",
    0xD9: "'",
    0xDA: "VARPTR",
    0xDB: "CSRLIN",
    0xDC: "POINT",
    0xDD: "OFF",
    0xDE: "INKEY$",
    0xE6: ">",
    0xE7: "=",
    0xE8: "<",
    0xE9: "+",
    0xEA: "-",
    0xEB: "*",
    0xEC: "/",
    0xED: "^",
    0xEE: "AND",
    0xEF: "OR",
    0xF0: "XOR",
    0xF1: "EQV",
    0xF2: "IMP",
    0xF3: "MOD",
    0xF4: "\\",
    0xFD81: "CVI",
    0xFD82: "CVS",
    0xFD83: "CVD",
    0xFD84: "MKI$",
    0xFD85: "MKS$",
    0xFD86: "MKD$",
    0xFD8B: "EXTERR",
    0xFE81: "FILES",
    0xFE82: "FIELD",
    0xFE83: "SYSTEM",
    0xFE84: "NAME",
    0xFE85: "LSET",
    0xFE86: "RSET",
    0xFE87: "KILL",
    0xFE88: "PUT",
    0xFE89: "GET",
    0xFE8A: "RESET",
    0xFE8B: "COMMON",
    0xFE8C: "CHAIN",
    0xFE8D: "DATE$",
    0xFE8E: "TIME$",
    0xFE8F: "PAINT",
    0xFE90: "COM",
    0xFE91: "CIRCLE",
    0xFE92: "DRAW",
    0xFE93: "PLAY",
    0xFE94: "TIMER",
    0xFE95: "ERDEV",
    0xFE96: "IOCTL",
    0xFE97: "CHDIR",
    0xFE98: "MKDIR",
    0xFE99: "RMDIR",
    0xFE9A: "SHELL",
    0xFE9B: "ENVIRON",
    0xFE9C: "VIEW",
    0xFE9D: "WINDOW",
    0xFE9E: "PMAP",
    0xFE9F: "PALETTE",
    0xFEA0: "LCOPY",
    0xFEA1: "CALLS",
    0xFEA4: "NOISE",
    0xFEA5: "PCOPY",
    0xFEA6: "TERM",
    0xFEA7: "LOCK",
    0xFEA8: "UNLOCK",
    0xFF81: "LEFT$",
    0xFF82: "RIGHT$",
    0xFF83: "MID$",
    0xFF84: "SGN",
    0xFF85: "INT",
    0xFF86: "ABS",
    0xFF87: "SQR",
    0xFF88: "RND",
    0xFF89: "SIN",
    0xFF8A: "LOG",
    0xFF8B: "EXP",
    0xFF8C: "COS",
    0xFF8D: "TAN",
    0xFF8E: "ATN",
    0xFF8F: "FRE",
    0xFF90: "INP",
    0xFF91: "POS",
    0xFF92: "LEN",
    0xFF93: "STR$",
    0xFF94: "VAL",
    0xFF95: "ASC",
    0xFF96: "CHR$",
    0xFF97: "PEEK",
    0xFF98: "SPACE$",
    0xFF99: "OCT$",
    0xFF9A: "HEX$",
    0xFF9B: "LPOS",
    0xFF9C: "CINT",
    0xFF9D: "CSNG",
    0xFF9E: "CDBL",
    0xFF9F: "FIX",
    0xFFA0: "PEN",
    0xFFA1: "STICK",
    0xFFA2: "STRIG",
    0xFFA3: "EOF",
    0xFFA4: "LOC",
    0xFFA5: "LOF",
}


def canonize_number(num: str) -> str:
    num = re.sub(r"^([\-])*0\.", r"\1.", num)
    num = re.sub(r"\.0$", "", num)
    return num.upper()


def parse_float32(data: bytes, index: int) -> str:
    if data[index + 3] == 0:
        return "0"
    exp = data[index + 3] - 152
    mantissa = ((data[index + 2] | 0x80) << 16) | (data[index + 1] << 8) | data[index]
    number = -math.ldexp(mantissa, exp) if data[index + 2] & 0x80 else math.ldexp(mantissa, exp)
    number_str = canonize_number("%s" % float("%.6g" % number))
    if "." not in number_str and "E" not in number_str:
        number_str += "!"
    return number_str


def parse_float64(data: bytes, index: int) -> str:
    if data[index + 7] == 0:
        return "0"
    exp = data[index + 7] - 184
    mantissa = (
        ((data[index + 6] | 0x80) << 48)
        | (data[index + 5] << 40)
        | (data[index + 4] << 32)
        | (data[index + 3] << 24)
        | (data[index + 2] << 16)
        | (data[index + 1] << 8)
        | data[index]
    )
    number = math.ldexp(mantissa, exp)
    number_str = canonize_number("%s" % float("%.16g" % number)).replace("E", "D")
    if "D" not in number_str:
        number_str += "#"
    return number_str


def detokenize(data: bytes, encoding: str = "cp437") -> str:
    if not data or data[0] != 0xFF:
        raise ValueError("No es un programa tokenizado GW-BASIC/BASICA (falta byte inicial 0xFF)")

    lines = []
    pos = 1
    while pos < len(data) - 1:
        if data[pos] == 0 and data[pos + 1] == 0:
            break
        pos += 2
        line_num = data[pos] | (data[pos + 1] << 8)
        pos += 2
        buf = []
        inside_rem = False
        inside_quotes = False
        while pos < len(data) and data[pos] != 0:
            code = data[pos]
            if code == 0x22 and not inside_rem:
                inside_quotes = not inside_quotes
                buf.append('"')
                pos += 1
            elif (
                code == 0x3A
                and not (inside_quotes or inside_rem)
                and pos + 2 < len(data)
                and data[pos + 1] == 0x8F
                and data[pos + 2] == 0xD9
            ):
                inside_rem = True
                buf.append("'")
                pos += 3
            elif inside_quotes or inside_rem or (0x20 <= code <= 0x7E):
                buf.append(bytes([code]).decode(encoding))
                pos += 1
            elif code == 0x8F:
                inside_rem = True
                buf.append("REM")
                pos += 1
            elif code == 0x0B:
                value = data[pos + 1] | (data[pos + 2] << 8)
                numerals = []
                while value > 0:
                    numerals.append(str(value & 0x07))
                    value >>= 3
                if not numerals:
                    numerals.append("0")
                numerals.reverse()
                buf.append("&O" + "".join(numerals))
                pos += 3
            elif code == 0x0C:
                val = data[pos + 1] | (data[pos + 2] << 8)
                buf.append("&H" + format(val, "X"))
                pos += 3
            elif code == 0x0E:
                buf.append(str(data[pos + 1] | (data[pos + 2] << 8)))
                pos += 3
            elif code == 0x0F:
                buf.append(str(data[pos + 1]))
                pos += 2
            elif 0x11 <= code <= 0x1B:
                buf.append(str(code - 0x11))
                pos += 1
            elif code == 0x1C:
                val = data[pos + 1] | (data[pos + 2] << 8)
                if val >= 32768:
                    val -= 65536
                buf.append(str(val))
                pos += 3
            elif code == 0x1D:
                buf.append(parse_float32(data, pos + 1))
                pos += 5
            elif code == 0x1F:
                buf.append(parse_float64(data, pos + 1))
                pos += 9
            elif code in TOKENS:
                buf.append(TOKENS[code])
                pos += 1
            elif pos + 1 < len(data) and ((code << 8) | data[pos + 1]) in TOKENS:
                buf.append(TOKENS[(code << 8) | data[pos + 1]])
                pos += 2
            else:
                raise ValueError("Token inesperado 0x%02X en linea %d offset %d" % (code, line_num, pos))
        pos += 1
        lines.append("%d %s" % (line_num, "".join(buf)))
    return "\n".join(lines) + "\n"


def main() -> None:
    if len(sys.argv) < 3:
        print("Uso: detokenize_gwbasic.py ENTRADA.BAS SALIDA.txt")
        sys.exit(1)
    src, dst = sys.argv[1], sys.argv[2]
    with open(src, "rb") as f:
        data = f.read()
    text = detokenize(data, "cp437")
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("OK %s -> %s (%d lineas)" % (src, dst, text.count("\n")))


if __name__ == "__main__":
    main()
