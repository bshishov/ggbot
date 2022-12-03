# TODO float based levenshtein


def eq_dist(a, b) -> float:
    return 1 - float(a == b)


def match(s1, x, dist_fn=eq_dist) -> float:
    pass
