"""Text Encoding Transformations

Handles Khmer text transformations, particularly Limon to Unicode conversion.
"""

from typing import Any

from .base import BaseTransformer, TransformationContext


class KhmerTextTransformer(BaseTransformer):
    """
    Handles all Khmer text transformations, particularly Limon to Unicode conversion.
    This centralizes all your Khmer text handling logic in one place.
    """

    def _initialize(self):
        """Load the Limon to Unicode mapping table once when the transformer is created."""
        self._limon_unicode_map = self._load_limon_unicode_mapping()
        self._more_dic = self._load_additional_mappings()
        self._left_vowels = ["e", "E", "é"]
        self._coeng_ro = ["®", "R"]
        self._shifters = [":", "'"]
        self._subscripts = [  # noqa: RUF001, RUF100
            "á",
            "ç",
            "Á",
            "Ç",
            "¶",
            "©",
            "ä",
            "¢",
            "Ä",
            "Ø",
            "þ",
            "æ",
            "Ð",
            "Æ",
            "Ñ",
            "þ",
            "ß",
            "Þ",
            "§",
            "ñ",
            ",",
            "ö",
            "<",
            "Ö",
            "µ",
            "ü",
            "ø",
            "V",
            "S",
            "ð",
            "¥",
        ]
        self._cons = [
            "k",
            "x",
            "K",
            "X",
            "g",
            "c",
            "q",
            "C",
            "Q",
            "j",
            "d",
            "z",
            "D",
            "Z",
            "N",
            "t",
            "f",
            "T",
            "F",
            "n",
            "b",
            "p",
            "B",
            "P",
            "m",
            "y",
            "r",
            "l",
            "v",
            "s",
            "h",
            "L",
            "G",
            ")",
        ]

    def _load_limon_unicode_mapping(self) -> dict[str, str]:
        """Load the main Limon to Unicode character mapping."""
        return {  # noqa: RUF001, RUF100
            "k": "ក",
            "x": "ខ",
            "K": "គ",
            "X": "ឃ",
            "g": "ង",
            "c": "ច",
            "q": "ឆ",
            "C": "ជ",
            "Q": "ឈ",
            "j": "ញ",
            "d": "ដ",
            "z": "ឋ",
            "D": "ឌ",
            "Z": "ឍ",
            "N": "ណ",
            "t": "ត",
            "f": "ថ",
            "T": "ទ",
            "F": "ធ",
            "n": "ន",
            "b": "ប",
            "p": "ផ",
            "B": "ព",
            "P": "ភ",
            "m": "ម",
            "y": "យ",
            "r": "រ",
            "l": "ល",
            "v": "វ",
            "s": "ស",
            "h": "ហ",
            "L": "ឡ",
            "G": "អ",
            "a": "ា",
            "i": "ិ",
            "I": "ី",
            "u": "ុ",
            "U": "ូ",
            "w": "ួ",
            "W": "ៀ",
            "e": "េ",
            "E": "ែ",
            "o": "ោ",
            "O": "ៅ",
            "ú": "ុ",
            "Ú": "ូ",
            "ª": "ំ",
            ";": "ះ",
            "'": "៍",
            ":": "៉",
            "°": "%",
            "´": "ខ្ញុំ",  # noqa: RUF001
            "¬": "(",
            "¦": ")",
            ">": ".",
            "0": "០",
            "1": "១",
            "2": "២",
            "3": "៣",
            "4": "៤",
            "5": "៥",
            "6": "៦",
            "7": "៧",
            "8": "៨",
            "9": "៩",
            "á": "្ក",
            "ç": "្ខ",
            "Á": "្គ",
            "Ç": "្ឃ",
            "¶": "្ង",
            "©": "្ច",
            "ä": "្ឆ",
            "¢": "្ជ",
            "Ä": "្ឈ",
            "Ø": "្ញ",
            "þ": "្ដ",
            "æ": "្ឋ",
            "Ð": "្ឌ",
            "Æ": "្ឍ",
            "Ñ": "្ណ",
            "ß": "្ថ",
            "Þ": "្ទ",
            "§": "្ធ",
            "ñ": "្ន",
            ",": "្ប",
            "ö": "្ផ",
            "<": "្ព",
            "Ö": "្ភ",
            "µ": "្ម",
            "ü": "្យ",
            "®": "្រ",
            "ø": "្ល",
            "V": "្វ",
            "S": "្ស",
            "ð": "្ហ",
            "¥": "្អ",
        }

    def _load_additional_mappings(self) -> dict[str, str]:
        """Load additional character mappings."""
        return {  # noqa: RUF001, RUF100
            "R": "្រ",
            ")": "ប",
            "ú": "ុ",
            ",": "្ប",
            "Ú": "ូ",
            ">": ".",
            "°": "%",
            "´": "ខ្ញុំ",  # noqa: RUF001
            "¬": "(",
            "¦": ")",
        }

    def can_transform(self, value: Any) -> bool:
        """
        Check if the value appears to be Limon-encoded text.
        This prevents us from trying to transform already-Unicode text.
        """
        if not isinstance(value, str) or not value:
            return False

        # Check for Limon encoding characteristics
        try:
            # If it's already valid Unicode Khmer, don't transform
            if any("\u1780" <= char <= "\u17ff" for char in value):
                return False

            # Check for common Limon characters
            limon_indicators = set(self._limon_unicode_map.keys()) | set(self._more_dic.keys())
            return any(char in limon_indicators for char in value)
        except Exception:
            return False

    def transform(self, value: str, context: TransformationContext) -> str:
        """
        Convert Limon-encoded text to Unicode using the complete algorithm.
        This implements the full Limon to Unicode conversion process.
        """
        if not value:
            return value

        return self._limon_to_unicode_conversion(value)

    def _limon_to_unicode_conversion(self, limon_text: str) -> str:
        """Main conversion function that handles the full Limon to Unicode process."""
        # Clean the text first
        cleaned_limon_text = "".join(char for char in limon_text if char.isprintable()).strip()
        return self._limon_to_unicode(cleaned_limon_text)

    def _limon_to_unicode(self, string: str) -> str:
        """Core conversion logic with character reordering."""
        new_string = ""

        for paragraph in string.split("\n"):
            # Apply the transformation sequence
            first_trans_string = self._ro_sub_swap(paragraph)
            second_trans_string = self._vowel_swap(first_trans_string)
            third_trans_string = self._second_swap(second_trans_string)
            fourth_trans_string = self._ro_sub_vowel_swap(third_trans_string)

            # Apply character mappings
            uni_trans_string = self._replace_all(fourth_trans_string, self._limon_unicode_map)
            final_trans_string = self._replace_all(uni_trans_string, self._more_dic)

            new_string += final_trans_string + "\n"

        return new_string.rstrip("\n")  # Remove trailing newline

    def _replace_all(self, text: str, dic: dict[str, str]) -> str:
        """Replace all characters according to the dictionary."""
        for old_char, new_char in dic.items():
            text = text.replace(old_char, new_char)
        return text

    def _swap(self, text: str, ch1: str, ch2: str) -> str:
        """Swap two character sequences in text."""
        return text.replace(ch1 + ch2, ch2 + ch1)

    def _vowel_swap(self, trans_string: str) -> str:
        """Swap left vowels with following consonants."""
        for i, c in enumerate(trans_string[:-1]):
            if c in self._left_vowels and trans_string[i + 1] in self._cons:
                trans_string = self._swap(trans_string, trans_string[i], trans_string[i + 1])
        return trans_string

    def _ro_sub_swap(self, trans_string: str) -> str:
        """Swap Coeng Ro with following consonants."""
        for i, c in enumerate(trans_string[:-1]):
            if c in self._coeng_ro and i + 1 < len(trans_string) and trans_string[i + 1] in self._cons:
                trans_string = self._swap(trans_string, trans_string[i], trans_string[i + 1])
        return trans_string

    def _second_swap(self, trans_string: str) -> str:
        """Handle complex swapping rules for vowels and subscripts."""
        for i, c in enumerate(trans_string[:-1]):
            if (
                (c in self._left_vowels and trans_string[i + 1] in self._subscripts)
                or (c in self._left_vowels and trans_string[i + 1] in self._shifters)
                or (c in self._coeng_ro and trans_string[i + 1] in self._subscripts)
                or (c in self._coeng_ro and trans_string[i + 1] in self._shifters)
            ):
                trans_string = self._swap(trans_string, trans_string[i], trans_string[i + 1])
        return trans_string

    def _ro_sub_vowel_swap(self, trans_string: str) -> str:
        """Swap left vowels with Coeng Ro."""
        for i, c in enumerate(trans_string[:-1]):
            if c in self._left_vowels and trans_string[i + 1] in self._coeng_ro:
                trans_string = self._swap(trans_string, trans_string[i], trans_string[i + 1])
        return trans_string

    def detect_encoding(self, value: str) -> str:
        """
        Utility method to detect the text encoding type.
        Useful for diagnostics and logging.
        """
        if not value:
            return "empty"
        if any("\u1780" <= char <= "\u17ff" for char in value):
            return "unicode_khmer"
        if self.can_transform(value):
            return "limon"
        return "unknown"
