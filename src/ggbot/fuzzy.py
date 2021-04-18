from typing import Optional, Union, Tuple
import math

__all__ = [
    'FuzzySet',
    'DiscreteFuzzySet',
    'FuzzySetCompound',
    'FuzzyUnion',
    'FuzzyIntersection',
    'FuzzyMultiply',
    'FuzzySum',
    'FuzzyNegate',
    'MembershipFunction',
    'ConstMf',
    'TrapezoidalMf',
    'TriangularMf',
    'GaussianMf',
    'Variable',
    'ConditionStatement',
    'Is',
    'EqualsValue',
    'ValueIsOneOf',
    'And',
    'Or',
    'Not',
    'Rules',
    'R',
    'plot_variable',
    'iter_linear_space'
]


def iter_linear_space(x_min: float, x_max: float, steps: int):
    dx = (x_max - x_min) / (steps - 1.0)
    x = x_min
    for i in range(steps):
        yield x
        x += dx


class FuzzySet:
    def sample(self, x):
        raise NotImplementedError

    def calculate_centroid(self, x_min=0.0, x_max=1.0, steps=100):
        s1 = 0.0
        area = 0.0

        for x in iter_linear_space(x_min, x_max, steps):
            sample = self.sample(x)
            s1 += x * sample
            area += sample

        if area < 1e-8:
            return 0
        return s1 / area

    def center(self):
        return None

    def to_discrete(self, x_min=0.0, x_max=1.0, steps=100):
        values = list(map(self.sample, iter_linear_space(x_min, x_max, steps)))
        return DiscreteFuzzySet(values, (x_min, x_max))

    def __call__(self, x):
        return self.sample(x)

    def __repr__(self):
        return f'<{self.__class__.__name__}>'


class DiscreteFuzzySet(FuzzySet):
    def __init__(self, values, bounds):
        self._values = values
        self._x_min, self._x_max = bounds
        self._x_range = self._x_max - self._x_min

    def sample(self, x):
        n = len(self._values)
        k = (x - self._x_min) / self._x_range
        i = k * (n - 1)  # float index

        # Bounds
        if i <= 0:
            return self._values[0]

        if i >= n - 1:
            return self._values[-1]

        # Linear interpolation between two nearest indices
        i1 = math.floor(i)
        i2 = math.ceil(i)
        p = i - i1  # 0..1 point on a line between i1 and i2
        y1 = self._values[i1]
        y2 = self._values[i2]
        return y1 + p * (y2 - y1)


class FuzzySetCompound(FuzzySet):
    def __init__(self, *args: FuzzySet):
        self.args = args

    def sample(self, x):
        raise NotImplementedError


class FuzzyUnion(FuzzySetCompound):
    def sample(self, x):
        return max(a.sample(x) for a in self.args)


class FuzzyIntersection(FuzzySetCompound):
    def sample(self, x):
        return min(a.sample(x) for a in self.args)


class FuzzyMultiply(FuzzySetCompound):
    def sample(self, x):
        return self.args[0].sample(x) * self.args[1].sample(x)


class FuzzyNegate(FuzzySetCompound):
    def sample(self, x):
        return 1 - self.args[0].sample(x)


class FuzzySum(FuzzySetCompound):
    def sample(self, x):
        a = self.args[0].sample(x)
        b = self.args[1].sample(x)
        return a + b - a * b


class MembershipFunction(FuzzySet):
    def sample(self, x):
        raise NotImplementedError()


class ConstMf(MembershipFunction):
    def __init__(self, value: float):
        self.value = value

    def sample(self, x):
        return self.value

    def center(self):
        return self.value

    def __repr__(self):
        return f'{self.__class__.__name__}({self.value!r})'


class TriangularMf(MembershipFunction):
    def __init__(self, left: float, support: float, right: float):
        self.left = left
        self.support = support
        self.right = right

    def sample(self, x):
        left = (x - self.left) / (self.support - self.left)
        right = (self.right - x) / (self.right - self.support)
        return max(0, min(left, right))

    def center(self):
        return self.support


class TrapezoidalMf(MembershipFunction):
    def __init__(self, left: float, left_support: float, right_support: float, right: float):
        self.left = left
        self.left_support = left_support
        self.right_support = right_support
        self.right = right

    def sample(self, x):
        left = (x - self.left) / (self.left_support - self.left)
        right = (self.right - x) / (self.right - self.right_support)
        v = min(left, right)
        return max(0, min(v, 1))  # clip v to 0..1

    def center(self):
        # NOT ACCURATE :D
        return 0.5 * self.right_support - 0.5 * self.left_support

    def __repr__(self):
        return f'{self.__class__.__name__}(' \
               f'{self.left!r}, ' \
               f'{self.left_support!r}, ' \
               f'{self.right_support!r}, ' \
               f'{self.right!r})'


class GaussianMf(MembershipFunction):
    def __init__(self, mean: float, std: float):
        self.mean = mean
        self.std = std

    def sample(self, x):
        return math.exp(-(x - self.mean) ** 2 / (2 * self.std ** 2))

    def center(self):
        return self.mean

    def __repr__(self):
        return f'{self.__class__.__name__}({self.mean!r}, {self.std!r})'


class Variable:
    def __init__(
            self,
            name: Optional[str] = None,
            bounds: Tuple[float, float] = (0, 1),
            **terms: MembershipFunction
    ):
        self.membership_functions = terms
        self.name = name
        self.bounds = bounds

    def fuzzify_all(self, x):
        result = {}
        for mf_name, mf in self.membership_functions.items():
            result[mf_name] = mf.sample(x)
        return result

    def fuzzify_max(self, x) -> Optional[str]:
        best_mf_name = None
        best_sample = 0
        for name, mf in self.membership_functions.items():
            sample = mf.sample(x)
            if sample > best_sample:
                best_sample = sample
                best_mf_name = name
        return best_mf_name

    def fuzzify(self, mf, x):
        if isinstance(mf, str):
            # Try to get mf by key
            return self.membership_functions.get(mf).sample(x)
        return mf.sample(x)

    def defuzzify(self, mf):
        bounds_min, bounds_max = self.bounds
        if not isinstance(mf, MembershipFunction):
            # Try to get mf by key
            mf = self.membership_functions[mf]
        return mf.calculate_centroid(bounds_min, bounds_max)

    def get_mf(self, mf) -> MembershipFunction:
        if not isinstance(mf, MembershipFunction):
            # Try to get mf by key
            mf = self.membership_functions[mf]
        return mf

    def get_membership_functions(self):
        return self.membership_functions.values()

    def name_of_mf(self, mf: MembershipFunction) -> Optional[str]:
        for name, m in self.membership_functions.items():
            if m is mf:
                return name
        return None

    def is_(self, mf):
        return Is(self, mf)


class ConditionStatement:
    def evaluate(self, **kwargs):
        raise NotImplementedError

    def __call__(self, **kwargs):
        return self.evaluate(**kwargs)

    def and_(self, cond):
        return And(self, cond)

    def or_(self, cond):
        return Or(self, cond)

    def __or__(self, other):
        return Or(self, other)

    def __and__(self, other):
        return And(self, other)

    def __repr__(self):
        return f'<{self.__class__.__name__}>'


class Is(ConditionStatement):
    def __init__(self, variable: Variable, mf: Union[str, MembershipFunction]):
        self._var = variable
        self._mf = self._var.get_mf(mf)

    def evaluate(self, **kwargs):
        x = kwargs[self._var.name]
        x_min, x_max = self._var.bounds
        x = max(min(x, x_max), x_min)
        return self._var.fuzzify(self._mf, x)

    def __str__(self):
        mf_name = self._var.name_of_mf(self._mf)
        return f'{self._var.name} IS {mf_name}'

    def __repr__(self):
        mf_name = self._var.name_of_mf(self._mf)
        return f'<{self._var.name} IS {mf_name}>'


class EqualsValue(ConditionStatement):
    def __init__(self, name: str, expected):
        self.name = name
        self.expected = expected

    def evaluate(self, **kwargs):
        value = kwargs.get(self.name)
        return float(value == self.expected)

    def __str__(self):
        return f'{self.name} == {self.expected}'


class ValueIsOneOf(ConditionStatement):
    def __init__(self, name: str, expected):
        self.name = name
        self.expected = expected

    def evaluate(self, **kwargs):
        value = kwargs.get(self.name)
        return float(value in self.expected)

    def __str__(self):
        return f'{self.name} in {self.expected}'


class And(ConditionStatement):
    def __init__(self, *operands: ConditionStatement):
        self._operands = operands

    def evaluate(self, **kwargs):
        results = (op.evaluate(**kwargs) for op in self._operands)
        return min(results)

    def __str__(self):
        operand_fmt = " AND ".join(map(str, self._operands))
        return f'({operand_fmt})'

    def __repr__(self):
        items_reps = ", ".join(map(repr, self._operands))
        return f'{self.__class__.__name__}({items_reps})'


class Or(ConditionStatement):
    def __init__(self, *operands: ConditionStatement):
        self._operands = operands

    def __str__(self):
        operand_fmt = " OR ".join(map(str, self._operands))
        return f'({operand_fmt})'

    def evaluate(self, **kwargs):
        results = (op.evaluate(**kwargs) for op in self._operands)
        return max(results)


class Not(ConditionStatement):
    def __init__(self, operand: ConditionStatement):
        self._operand = operand

    def evaluate(self, **kwargs):
        return 1.0 - self._operand.evaluate(**kwargs)


class R:
    def __init__(
            self,
            var: Variable,
            mf: Union[str, MembershipFunction],
            when: ConditionStatement
    ):
        self.var = var
        self.mf = self.var.get_mf(mf)
        self.condition = when

    def evaluate(self, **kwargs) -> float:
        # Mamdani inference
        alpha = self.condition.evaluate(**kwargs)
        intersection = FuzzyIntersection(self.mf, ConstMf(alpha))
        return intersection.calculate_centroid(x_min=self.var.bounds[0], x_max=self.var.bounds[1])

    def __call__(self, **kwargs):
        return self.evaluate(**kwargs)


class Rules:
    def __init__(self, var: Variable):
        self.var = var
        self.rules = []

    def add_rule(self, term, condition):
        self.rules.append((term, condition))

    def evaluate(self, **kwargs):
        # Mamdani inference
        rule_fs = []
        for term, condition in self.rules:
            alpha = condition.evaluate(**kwargs)
            mf = FuzzyIntersection(self.var.get_mf(term), ConstMf(alpha))
            rule_fs.append(mf)
        result_fs = FuzzyUnion(*rule_fs)
        return result_fs.calculate_centroid(*self.var.bounds)

    def __call__(self, **kwargs):
        return self.evaluate(**kwargs)


def plot_variable(v: Variable):
    import matplotlib.pyplot as plt

    x_min, x_max = v.bounds
    x = list(iter_linear_space(x_min, x_max, 100))

    for mf_name, mf in v.membership_functions.items():
        plt.plot(x, mf.sample(x), label=mf_name)

    plt.title(v.name)
    plt.legend()
    plt.show()
