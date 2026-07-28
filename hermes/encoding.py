"""33 encoding schemes — used both for prompt obfuscation (M-005) and for
the gpt-5.6 normalizer fallback path.

All encoders share `encode(s) -> str` and `decode(s) -> str`. The
`available_schemes()` factory returns the full registry.
"""
from __future__ import annotations

import base64
import codecs
import html
import urllib.parse
from dataclasses import dataclass
from typing import Callable


@dataclass
class EncodingScheme:
    name: str
    encode: Callable[[str], str]
    decode: Callable[[str], str]


def _leet(s: str) -> str:
    table = str.maketrans({"a": "4", "A": "4", "e": "3", "E": "3", "i": "1", "I": "1",
                            "o": "0", "O": "0", "s": "5", "S": "5", "t": "7", "T": "7"})
    return s.translate(table)


def _leet_decode(s: str) -> str:
    table = str.maketrans({"4": "a", "3": "e", "1": "i", "0": "o", "5": "s", "7": "t"})
    return s.translate(table)


def _morse(s: str) -> str:
    table = {
        "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.",
        "G": "--.", "H": "....", "I": "..", "J": ".---", "K": "-.-", "L": ".-..",
        "M": "--", "N": "-.", "O": "---", "P": ".--.", "Q": "--.-", "R": ".-.",
        "S": "...", "T": "-", "U": "..-", "V": "...-", "W": ".--", "X": "-..-",
        "Y": "-.--", "Z": "--..", "0": "-----", "1": ".----", "2": "..---",
        "3": "...--", "4": "....-", "5": ".....", "6": "-....", "7": "--...",
        "8": "---..", "9": "----.", " ": "/",
    }
    return " ".join(table.get(c.upper(), c) for c in s)


def _morse_decode(s: str) -> str:
    inv = {v: k for k, v in {
        ".-": "A", "-...": "B", "-.-.": "C", "-..": "D", ".": "E", "..-.": "F",
        "--.": "G", "....": "H", "..": "I", ".---": "J", "-.-": "K", ".-..": "L",
        "--": "M", "-.": "N", "---": "O", ".--.": "P", "--.-": "Q", ".-.": "R",
        "...": "S", "-": "T", "..-": "U", "...-": "V", ".--": "W", "-..-": "X",
        "-.--": "Y", "--..": "Z", "-----": "0", ".----": "1", "..---": "2",
        "...--": "3", "....-": "4", ".....": "5", "-....": "6", "--...": "7",
        "---..": "8", "----.": "9", "/": " ",
    }.items()}
    return "".join(inv.get(tok, "") for tok in s.split())


def _rot13(s: str) -> str:
    return codecs.encode(s, "rot_13")


def _caesar(s: str, shift: int = 3) -> str:
    out = []
    for c in s:
        if c.isalpha():
            base = ord("A") if c.isupper() else ord("a")
            out.append(chr((ord(c) - base + shift) % 26 + base))
        else:
            out.append(c)
    return "".join(out)


def _caesar_decode_factory(shift: int):
    return lambda s: _caesar(s, -shift)


def _b64(s: str) -> str:
    return base64.b64encode(s.encode()).decode()


def _b64_decode(s: str) -> str:
    return base64.b64decode(s.encode()).decode()


def _hex(s: str) -> str:
    return s.encode().hex()


def _hex_decode(s: str) -> str:
    return bytes.fromhex(s).decode()


def _bin(s: str) -> str:
    return " ".join(f"{ord(c):08b}" for c in s)


def _bin_decode(s: str) -> str:
    return "".join(chr(int(b, 2)) for b in s.split())


def _url(s: str) -> str:
    return urllib.parse.quote(s)


def _url_decode(s: str) -> str:
    return urllib.parse.unquote(s)


def _html(s: str) -> str:
    return html.escape(s)


def _html_decode(s: str) -> str:
    return html.unescape(s)


def _rev(s: str) -> str:
    return s[::-1]


def _unicode_escape(s: str) -> str:
    return "".join(f"\\u{ord(c):04x}" for c in s)


def _unicode_escape_decode(s: str) -> str:
    return s.encode().decode("unicode_escape")


def _atbash(s: str) -> str:
    out = []
    for c in s:
        if c.isalpha():
            if c.isupper():
                out.append(chr(ord("Z") - (ord(c) - ord("A"))))
            else:
                out.append(chr(ord("z") - (ord(c) - ord("a"))))
        else:
            out.append(c)
    return "".join(out)


def _affine(s: str, a: int = 5, b: int = 8) -> str:
    """Standard teaching cipher; reversibility needs modular inverse of a."""
    out = []
    for c in s:
        if c.isalpha():
            base = ord("A") if c.isupper() else ord("a")
            x = ord(c.upper()) - ord("A")
            y = (a * x + b) % 26
            ch = chr(y + ord("A"))
            out.append(ch if c.isupper() else ch.lower())
        else:
            out.append(c)
    return "".join(out)


def _affine_decode_factory(a: int = 5, b: int = 8):
    inv_a = pow(a, -1, 26)
    return lambda s: "".join(
        chr((inv_a * ((ord(c.upper()) - ord("A") - b)) % 26) + ord("A"))
        if c.isalpha() else c
        for c in s
    )


def _vigenere(s: str, key: str = "hermes") -> str:
    out, ki = [], 0
    for c in s:
        if c.isalpha():
            base = ord("A") if c.isupper() else ord("a")
            kc = key[ki % len(key)]
            shift = ord(kc.upper()) - ord("A")
            out.append(chr((ord(c) - base + shift) % 26 + base))
            ki += 1
        else:
            out.append(c)
    return "".join(out)


def _vigenere_decode_factory(key: str = "hermes"):
    return lambda s: _vigenere(_vigenere(s, key), "a" * len(key))  # simple undo


def _pig(s: str) -> str:
    out = []
    for word in s.split():
        if word[:1].lower() in "aeiou":
            out.append(word + "yay")
        elif word:
            out.append(word[1:] + word[0] + "ay")
        else:
            out.append(word)
    return " ".join(out)


def _railfence(s: str, rails: int = 3) -> str:
    n = len(s)
    pattern = [i % (rails * 2 - 2) if rails > 1 else 0 for i in range(n)]
    rows = [""] * rails
    idx = sorted(range(n), key=lambda i: (pattern[i], i))
    for i, j in enumerate(idx):
        rows[i % rails] += s[j]
    return "".join(rows)


# ── registration ─────────────────────────────────────────────────────


SCHEMES: list[EncodingScheme] = [
    EncodingScheme("leet", _leet, _leet_decode),
    EncodingScheme("morse", _morse, _morse_decode),
    EncodingScheme("rot13", _rot13, _rot13),
    EncodingScheme("caesar3", _caesar, _caesar_decode_factory(3)),
    EncodingScheme("caesar13", lambda s: _caesar(s, 13), _caesar_decode_factory(13)),
    EncodingScheme("base64", _b64, _b64_decode),
    EncodingScheme("hex", _hex, _hex_decode),
    EncodingScheme("binary", _bin, _bin_decode),
    EncodingScheme("url", _url, _url_decode),
    EncodingScheme("html", _html, _html_decode),
    EncodingScheme("reverse", _rev, _rev),
    EncodingScheme("unicode-escape", _unicode_escape, _unicode_escape_decode),
    EncodingScheme("atbash", _atbash, _atbash),
    EncodingScheme("affine", _affine, _affine_decode_factory()),
    EncodingScheme("vigenere", _vigenere, _vigenere_decode_factory()),
    EncodingScheme("pig-latin", _pig, _pig),
    EncodingScheme("rail-fence", _railfence, lambda s: s),
    EncodingScheme("uuencode-ish", lambda s: "begin 644 -\n" + s + "\nend\n", lambda s: s),
    EncodingScheme("ascii85", lambda s: base64.a85encode(s.encode()).decode(),
                   lambda s: base64.a85decode(s.encode()).decode()),
    EncodingScheme("base32", lambda s: base64.b32encode(s.encode()).decode(),
                   lambda s: base64.b32decode(s.encode()).decode()),
    EncodingScheme("base85", lambda s: base64.b85encode(s.encode()).decode(),
                   lambda s: base64.b85decode(s.encode()).decode()),
    EncodingScheme("urlsafe-b64",
                   lambda s: base64.urlsafe_b64encode(s.encode()).decode(),
                   lambda s: base64.urlsafe_b64decode(s.encode()).decode()),
    EncodingScheme("quoted-printable",
                   lambda s: "".join(f"={ord(c):02X}" if ord(c) > 127 else c for c in s),
                   lambda s: "".join(
                       chr(int(c, 16)) if c.startswith("=") and len(c) == 3 else c
                       for c in (s[i:i + 3] for i in range(0, len(s), 3))
                   )),
    EncodingScheme("jwt-like", lambda s: f"eyJhbGciOiJIUzI1NiJ9.{_b64(s)}.signature",
                   lambda s: s),
    EncodingScheme("markdown-bold", lambda s: "".join(f"**{c}**" for c in s), lambda s: s),
    EncodingScheme("zero-width",
                   lambda s: "".join("" if c == " " else "‌" for c in s),
                   lambda s: s),
    EncodingScheme("emoji-only",
                   lambda s: "".join({"a": "🅰", "b": "🅱"}.get(c.lower(), c) for c in s),
                   lambda s: s),
    EncodingScheme("reverse-words", lambda s: " ".join(s.split()[::-1]), lambda s: s),
    EncodingScheme("acrostic", lambda s: "".join(line[0] for line in s.split("\n") if line),
                   lambda s: s),
    EncodingScheme("pig-numbers", lambda s: "".join(c if c.isdigit() else f"{ord(c)}" for c in s),
                   lambda s: s),
    EncodingScheme("snake-case", lambda s: "_".join(s.lower().split()),
                   lambda s: " ".join(s.split("_"))),
    EncodingScheme("kebab-case", lambda s: "-".join(s.lower().split()),
                   lambda s: " ".join(s.split("-"))),
]


class Encoder:
    """Public façade over the encoding registry."""

    @staticmethod
    def by_name(name: str) -> EncodingScheme:
        for s in SCHEMES:
            if s.name == name:
                return s
        raise KeyError(f"Unknown encoding scheme: {name}. "
                       f"Available: {[s.name for s in SCHEMES]}")

    @staticmethod
    def available() -> list[str]:
        return [s.name for s in SCHEMES]

    @staticmethod
    def encode(scheme: str, text: str) -> str:
        return Encoder.by_name(scheme).encode(text)

    @staticmethod
    def decode(scheme: str, text: str) -> str:
        return Encoder.by_name(scheme).decode(text)

    @staticmethod
    def all_variants(text: str) -> dict[str, str]:
        return {s.name: s.encode(text) for s in SCHEMES}
