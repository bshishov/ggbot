from typing import Sequence, Dict, Tuple

__all__ = ["damerau_levenshtein_distance"]


def damerau_levenshtein_distance(s1: Sequence, s2: Sequence) -> int:
    d: Dict[Tuple[int, int], int] = {}
    len1 = len(s1)
    len2 = len(s2)

    for i in range(-1, len1 + 1):
        d[(i, -1)] = i + 1

    for j in range(-1, len2 + 1):
        d[(-1, j)] = j + 1

    for i in range(len1):
        for j in range(len2):
            if s1[i] == s2[j]:
                cost = 0
            else:
                cost = 1
            d[(i, j)] = min(
                d[(i - 1, j)] + 1,  # deletion
                d[(i, j - 1)] + 1,  # insertion
                d[(i - 1, j - 1)] + cost,  # substitution
            )

            if i and j and s1[i] == s2[j - 1] and s1[i - 1] == s2[j]:
                d[(i, j)] = min(d[(i, j)], d[i - 2, j - 2] + cost)  # transposition

    return d[len1 - 1, len2 - 1]
