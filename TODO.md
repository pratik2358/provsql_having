# Changes for the final version

Corrections and improvements that came out of the ICDT reviews and are not
part of the author feedback. “Lnnn” refers to the line numbers of the reviewed
PDF.

## Semantics

- **Boolean combinations (R1, W1).** Replace the atom-by-atom rule (L312–317,
  `semantics.tex`) by the joint reading: a predicate over one group takes a
  single ⊕-sum, over the worlds where the whole predicate holds. On
  `COUNT(*) = 1 AND COUNT(*) = 2` in Viterbi, with two tuples at 0.5, this gives
  0 and not 0.125.
  - State when the two readings coincide: a ⊗ (1 ⊖ a) = 0 for all a, and ⊗
    idempotent, as in B[X] (`predProv_mul_predProv`). The ∨ case also changes
    in non-idempotent m-semirings.
  - Update “Boolean connectives being interpreted as above” in Definition 20.
  - Say that the implementation resolves conditions jointly within an
    enumeration bound, and otherwise falls back to the product with a warning.
- **Theorem 29(ii).** Restrict the compound case to a single comparison, as
  `MonoCond.site_rewrite` now is; the join rewriting gives 0.25 and the joint
  reading 0.5 on `COUNT(*) >= 1 AND COUNT(*) >= 1` with one tuple at 0.5.
  Rewrite the remark at L1335–1337, which says summing over the worlds where the
  whole combination holds “would define a different semantics”, and the matching
  passage near `results.tex:1053`.
- **Definition 10 on mixed predicates (R3, W3).** Keep α in the second case
  unless ψ entails the existence of the group: on `g = 7 OR COUNT(*) >= 2` it
  now gives 1 and should give x. Correct the sentence following the definition
  (the non-empty worlds enforce group existence only for such ψ), and the claim
  at L986–987 that Definitions 10 and 20 “agree on every site”.

## Theorem 12

- **L343.** “agrees with it exactly when” should read “when”. The hypotheses are
  not necessary: {0, 1, t} with 0 < 1 < t, ⊕ = max, and ⊗ = max on non-zero
  elements is neither absorptive nor distributive, yet both sides agree for all
  θ and C.
- **Quantification on q.** “Let q be…” opens the theorem and so scopes over all
  three items, whereas (ii) and (iii) should read “there exists q”: they are
  false for degenerate q (empty, or with groups of at most one occurrence). The
  premise also refers to ⟪q⟫^Î before Î is introduced.
- **`results.tex:1084`.** Reword “distributivity becomes necessary”: it holds
  only in the sense of item (ii).
- **Consider strengthening (iii).** In every idempotent, distributive,
  non-absorptive K, with q a base relation, Q^{≥1} disagrees on the group (x, x)
  for x = 1 ⊕ b ≠ 1. Not formalized in Lean yet.
- **Consider simplifying (ii).** Security (absorptive, non-distributive in
  Table 1) may replace the five-element chain: with an idempotent level e
  strictly between 0 and 1, the group (e, e) gives e on the HAVING side and 0 on
  the join side for Q^{=1}. Checked by hand and by enumeration, not in Lean.
- **Open question.** Does every absorptive non-distributive K disagree on = and
  ≤? All examples with at most 4 elements do, for the values of C tested.

## Introduction

- **Corrections (R1).** Remove them from the contribution list (item (i) of the
  introduction, “correcting erroneous claims”), keeping them in Section 2 and
  Appendix A.1. The contribution is the compilation with machine-checked proofs.

## Examples and presentation (R2)

- **Use one running example instead of adding more.** Start Example 11 from a
  small concrete relation and SQL query, showing q′, γ, the output tuple, t, f,
  and the values in each world, so that Definitions 9–10 are visibly
  instantiated. Reuse it in Example 18 and in the statement of Theorem 12, with
  the two queries Q₁ and Q₂ side by side.
- **Show a non-Boolean case.** One line in a semiring where the monus does not
  cancel (e.g., COUNT(*) = 1 in Viterbi), as Example 11 only shows B[X], where it
  cancels.
- Make the comparison with [6, 34] more explicit.

## Related work

- **Cite Suciu, “Different Differences in Semirings”, Tannen Festschrift,
  OASIcs 119, 2024 (R3, W1).** Its eq. (4) defines the tropical monus on
  [0, ∞], and its footnote 6 extends it to ℝ ∪ {∞} and already says that
  Example 4 of Geerts and Poggi is incorrect. Credit it in Section 2 and
  Appendix A.1, next to Amarilli and Monet.
- **Its (A5) is the distributivity of ⊗ over ⊖.** It exhibits the failure on
  ({0, ½, 1}, ∨, ∧), adapted from Amsterdamer et al., which is relevant to
  simplifying Theorem 12(ii). Its Section 4.3 also states that (A5) holds in
  ℕ[X], which Appendix A.1 refutes: mention this there as a propagation of the
  error, as done for the Codd paper. Its footnote 10 uses the claim to argue that
  ℕ[X] is not the free m-semiring. That conclusion is still true, by the
  homomorphism to 𝔹 given in its main text, so say only that the premise fails.
- Situate its quotient construction next to the dual indeterminates of Grädel
  and Tannen in Section 7.

## Lean

- Align the anonymous links with the current development. Names have changed
  (e.g., `AggQuery.havingSite` is now `AggQueryIn.havingSite`), and the toolchain
  has moved from 4.33 to 4.35.
- Cite the joint reading (`predProvAnd`, `predProv_mul_predProv`,
  `GenPredIn.predsemJ`) from the paper.
