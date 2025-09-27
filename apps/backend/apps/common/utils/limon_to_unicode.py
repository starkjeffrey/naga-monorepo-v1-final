from .dictionaries import limon_unicode

left_vowels = ["e", "E", "é"]


CoengRo = ["®", "R"]


shipters = [":", "'"]


subscripts = [  # noqa: RUF001, RUF100
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


cons = [
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


more_dic = {  # noqa: RUF001, RUF100
    "R": "្រ",
    ")": "ប",
    "ú": "ុ",
    ",": "្ប",
    "Ú": "ូ",
    ">": ".",
    "°": "%",
    "´": "ខ្ញុំ",
    "¬": "(",
    "¦": ")",
}


def replace_all(text, dic):
    for i, j in dic.items():
        text = text.replace(i, j)

    return text


def swap(text, ch1, ch2):
    return text.replace(ch1 + ch2, ch2 + ch1)


def vowel_swap(trans_string):
    for i, c in enumerate(trans_string[:-1]):
        if c in left_vowels and trans_string[i + 1] in cons:
            trans_string = swap(trans_string, trans_string[i], trans_string[i + 1])

    return trans_string


def ro_sub_swap(trans_string):
    for i, c in enumerate(trans_string[:-1]):
        if c in CoengRo and i + 1 < len(trans_string) and trans_string[i + 1] in cons:
            trans_string = swap(trans_string, trans_string[i], trans_string[i + 1])

    return trans_string


def second_swap(trans_string):
    for i, c in enumerate(trans_string[:-1]):
        if (
            (c in left_vowels and trans_string[i + 1] in subscripts)
            or (c in left_vowels and trans_string[i + 1] in shipters)
            or (
                (c in CoengRo and trans_string[i + 1] in subscripts)
                or (c in CoengRo and trans_string[i + 1] in shipters)
            )
        ):
            trans_string = swap(trans_string, trans_string[i], trans_string[i + 1])

    return trans_string


def ro_sub_vowel_swap(trans_string):
    for i, c in enumerate(trans_string[:-1]):
        if c in left_vowels and trans_string[i + 1] in CoengRo:
            trans_string = swap(trans_string, trans_string[i], trans_string[i + 1])

    return trans_string


def limon_to_unicode(string):
    new_string = ""

    for paragraph in string.split("\n"):
        first_trans_string = ro_sub_swap(paragraph)

        second_trans_string = vowel_swap(first_trans_string)

        third_trans_string = second_swap(second_trans_string)

        fourth_trans_string = ro_sub_vowel_swap(third_trans_string)

        uni_trans_string = replace_all(fourth_trans_string, limon_unicode)

        final_trans_string = replace_all(uni_trans_string, more_dic)

        new_string += final_trans_string + "\n"

    return new_string


def limon_to_unicode_conversion(limon_text):
    cleaned_limon_text = "".join(char for char in limon_text if char.isprintable()).strip()

    return limon_to_unicode(cleaned_limon_text)
