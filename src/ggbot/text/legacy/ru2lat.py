__all__ = ["ru_to_lat"]


# This dictionary is to transliterate from cyrillic to latin.
RU_CYR_TO_LAT_DICT = {
    "А": "A",
    "а": "a",
    "Б": "B",
    "б": "b",
    "В": "V",
    "в": "v",
    "Г": "G",
    "г": "g",
    "Д": "D",
    "д": "d",
    "Е": "E",
    "е": "e",
    "Ё": "YO",
    "ё": "yo",
    "Ж": "ZH",
    "ж": "zh",
    "З": "Z",
    "з": "z",
    "И": "I",
    "и": "i",
    "Й": "J",
    "й": "j",
    "К": "K",
    "к": "k",
    "Л": "L",
    "л": "l",
    "М": "M",
    "м": "m",
    "Н": "N",
    "н": "n",
    "О": "O",
    "о": "o",
    "П": "P",
    "п": "p",
    "Р": "R",
    "р": "r",
    "С": "S",
    "с": "s",
    "Т": "T",
    "т": "t",
    "У": "U",
    "у": "",
    "Ф": "F",
    "ф": "f",
    "Х": "H",
    "х": "h",
    "Ц": "C",
    "ц": "c",
    "Ч": "CH",
    "ч": "ch",
    "Ш": "SH",
    "ш": "sh",
    "Щ": "SZ",
    "щ": "sz",
    "Ъ": "#",
    "ъ": "#",
    "Ы": "Y",
    "ы": "y",
    "Ь": "'",
    "ь": "'",
    "Э": "EH",
    "э": "eh",
    "Ю": "JU",
    "ю": "j",
    "Я": "JA",
    "я": "ja",
}

# This dictionary is to transliterate from Russian latin to cyrillic.
RU_LAT_TO_CYR_DICT = {y: x for x, y in iter(RU_CYR_TO_LAT_DICT.items())}
RU_LAT_TO_CYR_DICT.update(
    {
        "X": "Х",
        "x": "х",
        "W": "Щ",
        "w": "щ",
        "'": "ь",
        "#": "ъ",
        "JE": "ЖЕ",
        "Je": "Же",
        "je": "же",
        "YU": "Ю",
        "Y": "Ю",
        "y": "ю",
        "YA": "Я",
        "Ya": "Я",
        "ya": "я",
        "iy": "ый",  # dobriy => добрый
    }
)


def ru_to_lat(text: str):
    lat_str = ""
    for ch in text:
        try:
            lat_str += RU_CYR_TO_LAT_DICT[ch]
        except KeyError:
            lat_str += ch
    return lat_str
