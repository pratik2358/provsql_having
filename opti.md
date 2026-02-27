# Optimizations in HAVING Semantics Evaluation

The implementation targets **SUM**, **COUNT**, **MIN**, **MAX**, **AVG**, and **CHOOSE**
aggregates, with specialized handling of **SUM** and **COUNT**.

We introduce a number of optimizations which can be broadly classified into:

- Logical pruning (tautological and contradictory cases)
- Dynamic programming improvements
- Absorptive semiring–specific reductions
- Provenance-expression-level simplifications
- Structural rewriting optimizations

---

# Logical Pruning in `subset.cpp`

## Impossible-Case Elimination

For SUM aggregates, define:

$$
T = \sum_i w_i
$$

Before executing dynamic programming, the following contradictions are detected:

- `SUM > C` and $C \geq T$
- `SUM >= C` and $C > T$
- `SUM < C` and $C \leq 0$
- `SUM <= C` and $C < 0$
- `SUM = C` and $(C > T \ \text{or} \ C < 0)$

In these cases, the function returns the empty set of worlds immediately.

**Effect:** Avoids all enumeration work for unsatisfiable predicates.

---

## Tautology Detection

The following predicates are detected as universally true:

- `SUM > C` and $C < 0$
- `SUM >= C` and $C \leq 0$
- `SUM < C` and $C > T$
- `SUM <= C` and $C \geq T$

In these cases, the function returns `all_worlds(values)` without DP.

**Effect:** Skips all computation for predicates that hold in every world.

---

## NEQ Decomposition

The predicate `SUM != C` is implemented as:

$$
(\mathrm{SUM} < C) \cup (\mathrm{SUM} > C)
$$

This reuses existing logic and avoids duplicating DP code.

---

# Dynamic Programming Improvements for SUM

The SUM case is implemented as a subset-sum dynamic program:

$$
dp[j] = \{ S \subseteq [n] \mid \sum_{i \in S} w_i = j \}.
$$

---

## Bounded DP Range

Instead of allocating DP up to $C$, the maximum tracked sum $J$ is defined as:

- $J = T$, if $\mathrm{op} \in \{\mathrm{GT}, \mathrm{GE}\}$
- $J = \min(C - 1, T)$, if $\mathrm{op} = \mathrm{LT}$
- $J = \min(C, T)$, otherwise

Thus:

$$
J \leq T.
$$

**Effect:** Prevents unnecessarily large DP tables when $C$ is much larger than reachable sums.

---

## Prefix-Sum Pruning

Define the running prefix sum:

$$
\mathrm{pref\_sum}_i = \sum_{k \leq i} w_k.
$$

At iteration $i$, the maximum reachable sum is $\mathrm{pref\_sum}_i$.

Thus:

$$
j_{\max} = \min(J, \mathrm{pref\_sum}_i).
$$

The inner DP loop iterates only over:

$$
j = j_{\max}, j_{\max}-1, \dots, w,
$$

instead of all $j \leq J$.

**Effect:** Eliminates iterations over sums that are not yet reachable, reducing early-stage DP cost.

---

## Negative tuple value Fallback

If any tuple value $w_i < 0$, the DP throws an exception and falls back to exhaustive enumeration.

**Rationale:** Subset-sum DP assumes non-negative weights.

---

# Absorptive Semiring Optimizations

Let $S$ be a semiring satisfying the absorption law:

$$
a \oplus (a \otimes b) = a.
$$

This holds for the Boolean semiring, Why-provenance semiring, and other idempotent semirings.

---

## Upset-Based Pruning in SUM

For monotone comparisons (e.g., GT, GE): if a partial sum already satisfies the threshold, further supersets are not enumerated. Instead:

- An `upset` flag is set.
- Enumeration continues only for minimal satisfying generators.

**Rationale:** Under absorption, supersets of satisfying worlds do not contribute new information.

---

## COUNT Optimization

For `COUNT >= m` or `COUNT > m` under absorptive semirings, instead of enumerating all subsets of size at least $m$:

$$
\bigcup_{k = m}^{n} \{ S \subseteq [n] \mid |S| = k \},
$$

only subsets of size exactly $m$ are generated:

$$
\{ S \subseteq [n] \mid |S| = m \},
$$

and `upset = true` is set.

**Rationale:** All larger subsets are absorbed by minimal generators under absorptive semantics.

---

## Exhaustive Enumeration Compression

If every non-empty subset satisfies the predicate and the semiring is absorptive:

- The full world set is replaced with singleton worlds.
- `upset = true` is set.

This represents the upward closure via minimal generators.

---

# Provenance-Expression-Level Simplifications in `having_semantics.cpp`

## Identity Elimination

While constructing semiring expressions:

- Multiplication by `S.one()` is omitted.
- Addition of `S.zero()` is omitted.

**Effect:** Reduces formula size and avoids redundant nodes.

---

## Missing-World Factor Suppression

In absorptive semirings with monotone comparisons:

- For MAX with GE/GT
- For MIN with LE/LT

Missing-tuple constraints are suppressed when they do not affect minimal generators.

---

# Structural Rewriting Optimizations

## Selective Comparison Gate Rewriting

Only comparison gates of the form:

aggregate `op` constant

are rewritten into possible-world semantics. Other circuit components are untouched.

---

## Operator Normalization

Comparisons of the form:

$$
C \ \mathrm{op} \ \mathrm{aggregate}
$$

are rewritten by flipping the operator to:

$$
\mathrm{aggregate} \ \mathrm{flip}(\mathrm{op}) \ C,
$$

---

## Aggregate Kind Detection

If all semimod coefficients are equal to $1$, then SUM is treated as COUNT. This ensures that COUNT semantics use the combinatorial enumeration path rather than subset-sum DP.

---

# Conclusion

The presented optimizations preserve correctness under possible-world semantics and semiring evaluation while significantly reducing enumeration complexity and provenance expression size.
