# Extensions and open directions

Directions for strengthening the justification of the possible-world
semantics and for follow-up work (journal version or a next paper).
Items 2 and 5 are appendix-plus-Lean material; items 3 and 4 are a
research program.

Notation as in the paper: for a group with occurrence sequence
U = ((u_1,α_1),…,(u_N,α_N)) and a world W ⊑ U,

    A_W      = ⊗_{i∈W} α_i
    ann_U(W) = A_W ⊗ (𝟙 ⊖ ⊕_{i∉W} α_i)
    T_U(W)   = A_W ⊖ ⊕_{i∉W} A_{W∪{i}}      (form used in the appendix proofs)

and the predicate provenance of ψ is ⊕ of ann_U(W) over the non-empty
worlds where ψ holds. Call V(ψ) = {W ≠ ∅ : ψ holds in W} the family of
valid worlds; ψ is *monotone* when V(ψ) is upward-closed.

## 1. Conservativity beyond COUNT(*) — DONE (September 2026)

Realized in the paper as the appendix "Monotone Conditions:
Absorptivity Suffices" (definition of monotone conditions,
Proposition monus-cancellation, Theorem th:monotone with the
compositional positive rewriting), fully machine-checked
(Provenance/HavingMonotone.lean, MonoCond.site_rewrite;
Having.witness_identity / witness_minimal / sum_ann_meet;
Query.joinCount_monotone_correct). Theorem th:correctness(ii)/(iii)
were rescoped to the proved cases Q^{=1} / Q^{≥1} along the way.
Nothing left here.

## 2. Axiomatic characterization

Write down what any reasonable semantics for aggregate comparisons must
satisfy and ask how far the axioms pin it down. Candidate axioms:

- *Locality*: the predicate provenance of a group depends only on U and ψ.
- *Conservativity*: agreement with the standard σ on regular predicates
  (in the paper).
- *Homomorphism commutation* (in the paper).
- *Excluded middle*: ⟦ψ⟧ ⊕ ⟦¬ψ⟧ = δ(⊕_i α_i), the group-existence
  annotation.
- *Conditioning*: worlds omitting an occurrence annotated 𝟙 contribute
  nothing; ann does this, since 𝟙 ⊖ (𝟙 ⊕ x) = 𝟘. In Trop(ℕ) this
  surfaces concretely: 𝟙 ⊖ E_W is 𝟘 exactly when some discarded
  occurrence has cost 0, so, e.g., COUNT(*) = 2 reads "minimum cost
  over exactly-2 worlds discarding no zero-cost occurrence" – a
  sensible cost-of-witnessing reading outside the monotone case too.
- *Monotonicity*: ψ ⊨ ψ′ implies ⟦ψ⟧ ≤ ⟦ψ′⟧ in the natural order.
- *Exclusivity of the decomposition*: ann_U(W) ⊗ ann_U(W′) = 𝟘 for
  W ≠ W′ ("the ⊖ makes distinct parts incompatible").

Goal: any semantics satisfying these agrees with the possible-world sum
(perhaps only on absorptive m-semirings); failing uniqueness, a second
semantics satisfying all but one axiom identifies the decisive axiom.

Caveat found experimentally (see `msemiring_experiments.py`):
exclusivity as stated holds in 𝔹[X] and ℕ but *fails* in the tropical
semirings and in chains (e.g., Trop over ℕ, α = (1,5,5):
ann({1}) ⊗ ann({2}) = 6 ≠ ∞). It is a Boolean-flavored property; the
axiom must be weakened, e.g., to "no situation is counted twice under
any homomorphism to 𝔹", or restricted to the Boolean image. Related
fact, recorded during the appendix work: the gate semantics of ∧ is
not the world-wise sum even over absorptive semirings (Viterbi, two
occurrences at 0.5: ψ∧ψ gives 0.25 gate-wise vs 0.5 world-wise), as
absorptive semirings need not be multiplicatively idempotent.

## 3. Universality via the free m-semiring

Since the semantics commutes with homomorphisms, it is determined by
its value in the free commutative m-semiring over the tuple
annotations; the whole question reduces to characterizing one element
there. Candidate form: the possible-world sum is the unique (or the
least, in the natural order) element that specializes correctly under
every homomorphism to 𝔹 (evaluates to the truth of ψ on every
sub-instance) and satisfies a normal-form or exclusivity condition.
Homomorphisms to 𝔹 alone do not separate elements of the free
m-semiring (x ⊕ x vs x), which is exactly why the extra condition is
needed; identifying the right one is the open question.

## 4. Grädel–Tannen dual indeterminates

In the Grädel–Tannen framework for semiring semantics of full FO over
absorptive semirings, a negated atom is interpreted by a fresh negative
indeterminate x̄; the factor 𝟙 ⊖ (⊕α) plays exactly that role, realized
by the monus instead of a fresh symbol. A comparison such as
COUNT(*) ≥ C is FO-definable on the group, so it has a Grädel–Tannen
semantics. Target: on FO-definable HAVING conditions over absorptive
m-semirings with ⊗ distributive over ⊖, the possible-world semantics
coincides with the Grädel–Tannen semantics of the defining formula
under x̄ ↦ 𝟙 ⊖ x. This would justify the definition for all such
conditions at once and tie the "possible worlds" to their
model-checking games. Care needed: their setting is set-based, ours is
bags.

## 5. The ℕ specialization: forgetting commutes with evaluation

Open remainder of the ground-truth program (the monotone/witness part
became item 1 and is in the paper). In ℕ, 1 ∸ s = 0 for s ≥ 1, so
(𝟘-annotated tuples being absent) every world except W = U is
annihilated, and the predicate provenance is
[ψ holds on the full group] · Π_i α_i (confirmed on 300/300 random
instances in `msemiring_experiments.py`).

**Lemma B (ℕ site collapse).** In 𝕂 = ℕ, for any aggregate comparison
ψ and any group with occurrence sequence U with positive annotations,
⟦ψ⟧(u) = [ψ holds on the full sequence U] · Π_{(u,α)∈U} α.

**Proposition B (ℕ, forgetting commutes with evaluation).** In ℕ, for
every query in the scope of Definition `def:semantics` and every
ℕ-instance with positive annotations, an output occurrence has
positive annotation exactly when it belongs to the ordinary bag
evaluation ⟦·⟧ of the underlying unannotated instance (appendix
semantics, HAVING read as "keep a group iff ψ holds on its full
occurrence sequence"). Induction on operators; every inherited case is
a one-line check against the appendix table (− matches because both
sides use NOT IN), and the HAVING site is Lemma B. Lean cost is the
ordinary-vs-annotated bridge, which `Query.evaluate` /
`Query.evaluateAnnotated` already provide for the aggregate-free
fragment.

Cautions established along the way:
- "SQL" cannot be the plain ground truth: the inherited algebra
  already deviates from SQL at the difference operator (NOT IN, not
  EXCEPT ALL, as the paper's appendix documents). The right ground
  truth is the paper's own ordinary-relation semantics ⟦·⟧, and both
  sides of Proposition B use the same −, so the caveat is absorbed.
  Agreement with SQL itself then holds on the NOT-IN-compatible
  fragment (in particular on difference-free queries), one physical
  row per occurrence.
- The specialization is *not* invariant under trading
  occurrence-multiplicity for annotation-multiplicity: one occurrence
  annotated 3 is not three occurrences annotated 1 (COUNT(*) sees 1
  vs 3). Coherent with the design choice defended in the PODS
  rebuttal, but it means the ℕ-annotation must be read as a
  derivation weight, not a bag multiplicity, once aggregation is in
  play. Should be said wherever this is written up.
- For non-unit annotations the group's output annotation is Π α_i,
  whose support is right but whose value is odd as a multiplicity;
  composing with δ would normalize it to group existence.

## 6. Why not a dichotomy

A Ré–Suciu-style classification (their VLDB J. 2009 trichotomy covers a
single HAVING aggregate compared to a constant, on conjunctive queries
without self-joins, probabilistic setting only) does not transfer: in
the m-semiring setting the complexity of the possible-world sum is
governed by the family of valid worlds, and for monotone conditions in
absorptive semirings that family is an arbitrary monotone Boolean
function of the occurrences. A complete classification of which
conditions admit polynomial-size provenance would subsume monotone
circuit/formula complexity of (weighted) threshold functions. Islands
of tractability plus NP-hardness is the honest state; at most a
sentence in the conclusion.
