#!/usr/bin/env python3
"""Experiments for EXTENSIONS.md, direction 5 (ground-truth instantiations).

Tests, on random instances over several m-semirings, the identities

  Id1 (monus-freeness):  for upward-closed V (within non-empty worlds),
      sum_{W in V} ann_U(W)  =  sum_{W in V} A_W
  Id2 (minimal-witness collapse):
      sum_{W in V} A_W  =  sum_{W minimal in V} A_W

with A_W = prod_{i in W} alpha_i and
ann_U(W) = A_W (x) (1 (-) sum_{i not in W} alpha_i)   [Definition 10 of the paper].

Conjecture from the proof sketch: Id1 holds in every commutative
*idempotent* m-semiring (no distributivity of (x) over (-) needed),
Id2 additionally needs absorptivity.

Also: the N (bag) specialization vs SQL, and exclusivity of the
world decomposition (ann_U(W) (x) ann_U(W') = 0 for W != W').
"""

import itertools
import math
import random

random.seed(42)

INF = math.inf


class Semiring:
    name = "?"
    idempotent = False
    absorptive = False

    def leq(self, a, b):  # natural order a <= b
        raise NotImplementedError


class Nat(Semiring):
    name = "N (bags)"
    zero, one = 0, 1

    def add(self, a, b): return a + b
    def mul(self, a, b): return a * b
    def sub(self, a, b): return max(a - b, 0)
    def leq(self, a, b): return a <= b
    def rand(self): return random.randint(1, 3)


class TropN(Semiring):
    name = "Tropical over N (min,+)"
    zero, one = INF, 0
    idempotent = True
    absorptive = True

    def add(self, a, b): return min(a, b)
    def mul(self, a, b): return a + b
    def sub(self, a, b): return a if b > a else INF
    def leq(self, a, b): return b <= a  # natural order: infinity is bottom
    def rand(self): return random.randint(0, 5)


class TropZ(TropN):
    name = "Tropical over Z (min,+)"
    absorptive = False

    def rand(self): return random.randint(-4, 4)


class Chain5(Semiring):
    """Total order 0<1<2<3<4, max/min; absorptive, but (x) does not
    distribute over (-): min(1, 2-1)=1 vs min(1,2)-min(1,1)=1-1=0."""
    name = "Chain5 (max,min)"
    zero, one = 0, 4
    idempotent = True
    absorptive = True

    def add(self, a, b): return max(a, b)
    def mul(self, a, b): return min(a, b)
    def sub(self, a, b): return 0 if b >= a else a
    def leq(self, a, b): return a <= b
    def rand(self): return random.randint(0, 4)


class BoolFunc(Semiring):
    """B[X] over NVARS variables; an element is the bitmask of its
    satisfying assignments. Monus a - b = a AND NOT b."""
    name = "B[X]"
    idempotent = True
    absorptive = True
    NVARS = 4
    FULL = (1 << (1 << NVARS)) - 1
    zero, one = 0, FULL

    def add(self, a, b): return a | b
    def mul(self, a, b): return a & b
    def sub(self, a, b): return a & ~b & self.FULL
    def leq(self, a, b): return a | b == b

    def var(self, i):
        m = 0
        for asg in range(1 << self.NVARS):
            if asg >> i & 1:
                m |= 1 << asg
        return m

    def rand(self):
        # a random variable, possibly repeated across occurrences
        return self.var(random.randrange(self.NVARS))


def big_add(K, xs):
    r = K.zero
    for x in xs:
        r = K.add(r, x)
    return r


def big_mul(K, xs):
    r = K.one
    for x in xs:
        r = K.mul(r, x)
    return r


def check_monus(K, samples=300):
    """Sanity-check residuation: a-b is the least c with a <= b+c."""
    ok = True
    for _ in range(samples):
        a, b = K.rand(), K.rand()
        c = K.sub(a, b)
        if not K.leq(a, K.add(b, c)):
            ok = False
        # least: no strictly smaller candidate among sampled values
        for _ in range(30):
            d = K.rand()
            if K.leq(a, K.add(b, d)) and K.leq(d, c) and d != c:
                ok = False
    return ok


def ann(K, alphas, W):
    inside = big_mul(K, [alphas[i] for i in W])
    outside = big_add(K, [alphas[i] for i in range(len(alphas)) if i not in W])
    return K.mul(inside, K.sub(K.one, outside))


def A(K, alphas, W):
    return big_mul(K, [alphas[i] for i in W])


def upward_closure(gens, n):
    """Upward closure, within non-empty subsets of {0..n-1}, of gens."""
    fam = set()
    for W in map(frozenset, gens):
        for X in itertools.chain.from_iterable(
                itertools.combinations(range(n), r) for r in range(n + 1)):
            X = frozenset(X)
            if W <= X and X:
                fam.add(X)
    return fam


def minimals(fam):
    return [W for W in fam if not any(X < W for X in fam)]


def random_upward_family(n):
    kind = random.choice(["count", "sum", "random"])
    subsets = [frozenset(c) for r in range(1, n + 1)
               for c in itertools.combinations(range(n), r)]
    if kind == "count":
        C = random.randint(1, n)
        return {W for W in subsets if len(W) >= C}, f"COUNT>= {C}"
    if kind == "sum":
        vals = [random.randint(0, 3) for _ in range(n)]
        c = random.randint(1, 6)
        fam = {W for W in subsets if sum(vals[i] for i in W) >= c}
        return upward_closure(fam, n), f"SUM{vals}>={c}"
    gens = random.sample(subsets, k=random.randint(1, min(3, len(subsets))))
    return upward_closure(gens, n), f"up({[sorted(g) for g in gens]})"


def test_identities(K, trials=400):
    fail1 = fail2 = 0
    ex1 = ex2 = None
    for _ in range(trials):
        n = random.randint(1, 4)
        alphas = [K.rand() for _ in range(n)]
        fam, desc = random_upward_family(n)
        if not fam:
            continue
        s_ann = big_add(K, [ann(K, alphas, W) for W in fam])
        s_A = big_add(K, [A(K, alphas, W) for W in fam])
        s_min = big_add(K, [A(K, alphas, W) for W in minimals(fam)])
        if s_ann != s_A:
            fail1 += 1
            ex1 = ex1 or (alphas, desc, s_ann, s_A)
        if s_A != s_min:
            fail2 += 1
            ex2 = ex2 or (alphas, desc, s_A, s_min)
    return fail1, fail2, ex1, ex2, trials


def test_exclusivity(K, trials=300):
    """ann_U(W) (x) ann_U(W') = 0 for W != W' ?"""
    fails = None
    for _ in range(trials):
        n = random.randint(2, 4)
        alphas = [K.rand() for _ in range(n)]
        subsets = [frozenset(c) for r in range(1, n + 1)
                   for c in itertools.combinations(range(n), r)]
        for W, X in itertools.combinations(subsets, 2):
            p = K.mul(ann(K, alphas, W), ann(K, alphas, X))
            if p != K.zero:
                fails = fails or (alphas, sorted(W), sorted(X), p)
    return fails


def test_nat_sql(trials=300):
    """In N: predicate provenance = [psi holds on full group] * prod(alpha).
    With all-ones annotations this is exactly SQL's HAVING (support and
    multiplicity)."""
    K = Nat()
    all_match = True
    for _ in range(trials):
        n = random.randint(1, 4)
        alphas = [K.rand() for _ in range(n)]
        C = random.randint(1, n + 1)
        # semantics: sum over non-empty worlds with |W| >= C
        fam = {frozenset(c) for r in range(1, n + 1)
               for c in itertools.combinations(range(n), r) if r >= C}
        p = big_add(K, [ann(K, alphas, W) for W in fam])
        expected = math.prod(alphas) if n >= C else 0
        if p != expected:
            all_match = False
    return all_match


def main():
    semirings = [Nat(), TropN(), TropZ(), Chain5(), BoolFunc()]
    print("== monus residuation sanity check ==")
    for K in semirings:
        print(f"  {K.name:28s} {'ok' if check_monus(K) else 'FAIL'}")

    print("\n== Id1 (sum ann = sum A) and Id2 (sum A = sum over minimals),"
          " upward-closed families ==")
    for K in semirings:
        f1, f2, ex1, ex2, tr = test_identities(K)
        print(f"  {K.name:28s} idem={K.idempotent!s:5s} abs={K.absorptive!s:5s}"
              f"  Id1 fails {f1}/{tr}, Id2 fails {f2}/{tr}")
        if ex1:
            print(f"    Id1 counterexample: alphas={ex1[0]} fam={ex1[1]}"
                  f" sum_ann={ex1[2]} sum_A={ex1[3]}")
        if ex2:
            print(f"    Id2 counterexample: alphas={ex2[0]} fam={ex2[1]}"
                  f" sum_A={ex2[2]} sum_min={ex2[3]}")

    print("\n== exclusivity ann(W) (x) ann(W') = 0 ==")
    for K in semirings:
        ex = test_exclusivity(K)
        if ex:
            print(f"  {K.name:28s} FAILS, e.g. alphas={ex[0]}"
                  f" W={ex[1]} W'={ex[2]} product={ex[3]}")
        else:
            print(f"  {K.name:28s} holds on all samples")

    print("\n== N specialization: provenance = [psi(full group)] * prod(alpha) ==")
    print(f"  {'confirmed' if test_nat_sql() else 'REFUTED'}")

    print("\n== tropical, non-monotone example: COUNT(*)=2 on 3 occurrences ==")
    K = TropN()
    alphas = [1, 2, 4]
    fam = [frozenset(c) for c in itertools.combinations(range(3), 2)]
    for W in fam:
        print(f"  W={sorted(W)}: A_W={A(K, alphas, W)} ann={ann(K, alphas, W)}")
    print(f"  provenance = {big_add(K, [ann(K, alphas, W) for W in fam])}")


if __name__ == "__main__":
    main()
