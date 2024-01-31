from typing import Optional, Iterable
import itertools
from collections import namedtuple
from collections.abc import MutableSequence


CONSONANTS = set("bcdfghjklmnpqrstvwxz")  # as # symbol
WOVELS = set("aeiouy")  # as & symbol

REPLACEMENTS = {
    #'ation': 'эйшн',
    #'ight': 'айт',
    #'uild': 'илд',
    #'tion': 'шн',
    #'ace': 'эйс',
    #'egi': 'эджи',
    #'cur': 'кёр',
    #'the': 'зе',
    #'ing$': ['ин$', 'инг$'],
    #'se$': 'з$',
    # сочетания гласных
    "l(ue)": "ю",
    "q(ue)": "ю",
    "r(ue)": "у",
    "(ue)": "у",
    "(ei)": "ей",
    "(ee)": "и",
    #'(ie)': 'е',
    "(ie)r$": "ай",  # multiplier
    "(ie)$": "ай",  # pie, lie, die
    "(ie)": "и",  # medieval
    "(oi)": "ой",
    "(oy)": "ой",
    "(ay)": "ей",
    "(ea)": "и",
    "(ou)": "ау",
    "(ui)": "и",
    # U
    "b(u)l": "у",
    "f(u)l": "у",
    "p(u)l": "у",
    "b(u)sh": "у",
    "f(u)sh": "у",
    "p(u)sh": "у",
    #'(u)': 'а',
    # consonant-le syllable
    "#(le)": "л",
    # открытый (немая е на конце)
    "(a)#e$": "эй",
    "(o)#e$": "оу",
    "(e)#e$": "и",
    "(i)#e$": "ай",
    "(y)#e$": "ай",
    "(u)#e$": "ю",
    "&#(e)$": "",
    # Закрытый. 2.
    # Только 2 буквы в слове
    "^(a)#$": "э",
    "^(о)#$": "о",
    "^(e)#$": ["е", "э"],
    "^(i)#$": "и",
    "^(u)#$": "а",
    "^(y)#$": "и",
    # Закрытый 3. Слог вида «гласная + r»
    "#(a)r": "а",
    "#(o)r": "о",
    "#(e)r": "ё",
    "#(i)r": "ё",
    "#(y)r": "ё",
    "#(u)r": "ё",
    # Закрытый 4. Слог вида «гласная + «r» + гласная»
    "(a)r&": "э",
    "(o)r&": "о",
    "(e)r&": "и",
    "(i)r&": "ай",
    "(y)r&": "ай",
    "(u)r&": "ю",
    # Открытый слог. 1 тип
    #'(a)#&': 'эй',
    #'(o)#&': 'оу',
    #'(e)#&': 'и',
    #'(i)#&': 'ай',
    #'(y)#&': 'ай',
    #'(u)#&': 'ю',
    # Согласные
    "(ck)": "к",
    # б не читается
    "m(b)$": "",
    "(b)t$": "",
    # C перед e, i, y
    "(c)e": ["с", "ц"],
    "(c)i": "с",
    "(c)y": "с",
    # C в сочетаниях  -cion, -cial, -cian, -cean, -cient
    "(c)ion": "ш",
    "(c)ial": "ш",
    "(c)ian": "ш",
    "(c)ean": "ш",
    "(c)ient": "ш",
    "r(ch)$": "к",
    "(ch)": "ч",
    # D не произносится в nd / dn
    #'n(d)': '',
    #'(d)n': '',
    # G иключения перед i/e/y
    "^(g)ive": "г",
    "^(g)et": "г",
    "o(gg)y": "гг",
    # G перед i/e/y
    "(g)i": "дж",
    "(g)e": "дж",
    "(g)y": "дж",
    # Gh на конце
    "(gh)$": "ф",
    # G в сочетаниях gh gn
    "(g)n": "",
    "(g)h": "",
    # K 	не произносится в сочетании kn
    "(k)n": "н",
    # Q
    "(que)$": "к",  # technique
    "(qu)": "кв",  # quality
    # S
    "&(s)&": "з",  # user
    "(sh)": "ш",
    "&(s)ure": "ж",  # leisure
    "&(s)ion": "ж",
    "(s)ure": "ш",  # sure, assure
    "(s)ion": "ш",
    # Th
    "(th)$": "с",  # filth, twentieth
    "#(th)": "с",
    "(th)": "з",
    "(th)&": "з",
    "&(th)&": "з",
    "s(t)ion": "шч",
    "(t)ion": "ш",
    "(t)ure": "ч",
    "(t)ural": "ч",
    "(t)ury": "ч",
    # Y
    "^(y)": "й",
    "(y)o": "ё",  # beyond
    # Z
    "(z)ure": "ж",  # seizure
    # Unsorted
    #'(ain)': 'эйн',
    #'(ack)': 'эк',
    #'(our)': 'ор',
    #'(ur)': 'ёр',
    #'(ch)': 'ч',
    #'(un)': 'ан',
    #'(se)': 'с',
    #'(re)': 'р',
    # Defaults
    "(a)": "а",
    "(b)": "б",
    "(c)": "к",
    "(d)": "д",
    "(e)": "е",
    "(f)": "ф",
    "(g)": "г",
    "(h)": "х",
    "(i)": "и",
    "(j)": "дж",
    "(k)": "к",
    "(l)": "л",
    "(m)": "м",
    "(n)": "н",
    "(o)": "о",
    "(p)": "п",
    "(q)": "к",
    "(r)": "р",
    "(s)": "с",
    "(t)": "т",
    "(u)": "а",
    "(v)": "в",
    "(w)": "в",
    "(x)": "кс",
    "(y)": "и",
    "(z)": "з",
}

RULES: dict[int, dict] = {
    6: {},
    5: {},
    4: {},
    3: {},
    2: {},
    1: {},
}


Match = namedtuple("Match", ("group_start", "group_end"), defaults=(-1, -1))


def match_rule(text: str, rule: str, start: int = 0) -> Optional[Match]:
    rule_it = iter(rule)
    group_start = -1
    group_end = -1
    r = next(rule_it)

    if r == "^":
        if start != 0:
            return None
        r = next(rule_it)

    if r == "(":
        group_start = start
        r = next(rule_it)

    for i in range(start, len(text)):
        ch = text[i]
        if r == "#":
            if ch not in CONSONANTS:
                return None
        elif r == "&":
            if ch not in WOVELS:
                return None
        elif r == ".":
            pass
        elif r == "^":
            if i != 0:
                return None
        elif r == "$":
            if i != len(text) - 1:
                return None
        elif r != ch:
            return None
        try:
            r = next(rule_it)
            if r == "(":
                group_start = i + 1
                r = next(rule_it)
            if r == ")":
                group_end = i + 1
                r = next(rule_it)
            if r == "$":
                if i != len(text) - 1:
                    return None
        except StopIteration:
            return Match(group_start=group_start, group_end=group_end)

    if r == "$":
        return Match(group_start=group_start, group_end=group_end)
    return None


def expand(ch: str) -> Iterable[str]:
    if ch == "#":
        yield from CONSONANTS
    elif ch == "&":
        yield from WOVELS
    else:
        yield ch


def expand_rule(rule: str) -> Iterable[str]:
    for combination in itertools.product(*(expand(ch) for ch in rule)):
        yield "".join(combination)


"""
for _k, _v in REPLACEMENTS.items():
    for _r in expand_rule(_k):
        ruleset = RULES[len(_r)]
        if _r in ruleset:
            print(f'CONFLICT: {_k}')
        RULES[len(_r)][_r] = _v
"""


def _resolve_replacement(replacement: str, sub: str) -> str:
    def _it():
        for i, ch in enumerate(replacement):
            if ch.isdigit():
                yield sub[int(ch)]
            else:
                yield ch

    return "".join(_it())


def replace_with_rules(text: str):
    n = len(text)
    # original = text[:]
    for window_size, replacements in RULES.items():
        if window_size <= n:
            i = 0
            while i <= n - window_size + 1:
                sub = text[i : i + window_size]
                replacement = replacements.get(sub)

                if replacement:
                    if isinstance(replacement, list):
                        replacement = replacement[0]
                    replacement = _resolve_replacement(replacement, sub)
                    text = "".join((text[:i], replacement, text[i + window_size :]))
                else:
                    i += 1
    return text


import re

_TOKEN_RE = re.compile(r"[\w\d]+")


def tokenize(text: str) -> Iterable[str]:
    matches = _TOKEN_RE.findall(text)
    for m in matches:
        yield m


def replace_with_rules_2(text: str) -> str:
    matches: MutableSequence[Optional[str]] = [None] * len(text) * 2
    for i in range(len(text)):
        for rule, replacement in REPLACEMENTS.items():
            match = match_rule(text, rule, start=i)
            if match is not None:
                if matches[match.group_start] is None:
                    if isinstance(replacement, list):
                        replacement = replacement[0]
                    matches[match.group_start] = replacement
                    for j in range(match.group_start + 1, match.group_end):
                        matches[j] = ""
    return "".join(m for m in matches if m is not None)


def en2ru(text: str) -> str:
    results_tokens = []
    for token in tokenize(text):
        results_tokens.append(replace_with_rules_2(token.lower()))
    return " ".join(results_tokens)


def _test():
    phrases = """
    PyStemmer provides access to efficient algorithms for calculating a “stemmed” form of a word. 
    This is a form with most of the common morphological endings removed; 
    hopefully representing a common linguistic base form. 
    This is most useful in building search engines and information retrieval software; 
    for example, a search with stemming enabled should be able to 
    find a document containing “cycling” given the query “cycles”.
    GTFO
    中世纪君主 Medieval Monarch
    Tempus Bound
    Halo: The Master Chief Collection
    A Place for the Unwilling
    Subterrain
    Graviteam Tactics: Mius-Front
    Armoured Commander II
    Alba: A Wildlife Adventure
    Potion Party
    SimCasino
    Himeko Sutori
    Unturned
    Strategic Mind: Spectre of Communism
    Ninja Simulator
    Deadstick - Bush Flight Simulator
    Nosferatu's Butler
    Niko and the Cubic Curse - Steam Playtest Edition
    Cry of War
    Unturned Dedicated Server
    Juicy Army: Prologue
    The Hayseed Knight
    APICO Demo
    Four Course Combat
    Black Ink
    Ayo the Clown
    LURE
    Pantropy
    JETBOY
    Adapt
    CODE2040
    Potentia
    Das Balkonzimmer
    Horizon Chase Turbo
    Pro Strategy Football 2021
    Archons of Doom
    Pantropy dedicated server
    Guildmaster: Gratuitous Subtitle
    Soarocity Demo
    Nightfall Hacker
    GoldFish Brain
    Waronoi
    """
    for p in phrases.split("\n"):
        p = p.strip()
        if p:
            ru = en2ru(p)
            print(f"{p} -> {ru}")


if __name__ == "__main__":
    _test()
