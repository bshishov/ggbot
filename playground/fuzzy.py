import numpy as np

from ggbot.fuzzy import *


def main():
    bad = GaussianMf(0, 1)
    average = GaussianMf(1, 1)
    good = GaussianMf(2, 1)

    no_tip = GaussianMf(0, 1)
    poor = GaussianMf(1, 1)
    decent = GaussianMf(2, 1)

    # variables
    food = Variable('food', (0, 3), bad=bad, average=average, good=good)
    service = Variable('service', (0, 3), bad=bad, average=average, good=good)
    tip = Variable('tip', (0, 3), no_tip=bad, poor=poor, decent=decent)

    res = R(tip, no_tip, Is(food, bad) & Is(service, bad)).evaluate(food=2, service=2)
    print(res)

    rules = Rules(tip)
    rules.add_rule(no_tip, Is(food, bad) & Is(service, bad))
    rules.add_rule(poor, And(Or(Is(food, average), Is(food, good)), Is(service, average)))
    rules.add_rule(decent, And(Is(food, good), Is(service, good)))

    evaluated = rules.evaluate(food=2, service=2)
    print(f'tip={evaluated} {tip.fuzzify_all(evaluated)}')

    import matplotlib.pyplot as plt
    m = np.zeros((20, 20), np.float32)
    for i in range(m.shape[0]):
        food_val = 3 * i / (m.shape[0] - 1.0)
        for j in range(m.shape[1]):
            service_val = 3 * j / (m.shape[1] - 1.0)
            t = rules.evaluate(food=food_val, service=service_val)
            m[i, j] = t
    plt.imshow(m)
    plt.show()


if __name__ == '__main__':
    main()
