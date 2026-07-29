# HANDOFF: scholarly-schema tightening, next round

State as of 2026-07-28, after the witness-driven tightening audit of
`schema/html5/scholarly-ltx-*.rnc`.  This file is the worklist for the
next round, intended to run on the machine that holds the full arXiv
HTML sample set, where witness evidence is decisive rather than
suggestive.

## Method (keep it)

A variant earns its place in the grammar only if it is **witnessed** in
real transform output or **provably emittable** by the upstream XSLT
(`LaTeXML/lib/LaTeXML/resources/XSLT/`, plus the XML content models in
`.../RelaxNG/`).  The loop:

1. `tools/witness-scan.py PATH...` — tabulates element / first-class-token /
   parent-context witnesses over an HTML tree (fixtures, regression dirs,
   or the full arXiv set).  Every row is a justification; every schema
   alternative without a row is a cut candidate.
2. Check cut candidates against the XSLT before cutting (e.g. `a[name]`
   had zero witnesses but is unconditional upstream output for
   `ltx:anchor`, so it stays).
3. Apply, then verify:
   - `JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 python3 checker.py build`
   - `./corpus-validate.py tests/html-scholarly/*.html` → must be 9/9 clean
   - `tests/html-scholarly/invalid/*` → must all exit non-zero
   - `./corpus-validate.py <corpus>` → diff the category table and the
     failing-file set against a pre-change baseline; the failing-file set
     must not grow (message-count drift inside already-invalid files is
     jing recovery noise and acceptable)
   - probe documents for each new rejection/acceptance (see the pattern
     in the audit round: minimal valid shell + one injected construct,
     asserting exact exit codes both ways)

Heading-rank ground truth: `f:seclev-aux` in
`LaTeXML-structure-xhtml.xsl` — one document-global rank per unit type,
floor h2 (h1 is the document title), each potential host type adds one,
cap h6.  The per-unit rank ranges in `scholarly-ltx-structure.rnc` are
derived from it under the assumption that `ltx:part` is absent; adding
part shifts them (see below).

## Next steps, in rough priority order

1. **`ltx:part`** (witnessed: `section.ltx_part` + `h2.ltx_title_part`,
   ~6 occurrences even in the small regression corpus; books will bring
   more).  Model `part` as a sectional unit above `chapter` in
   `document.body.class`.  Consequence: every per-unit title rank range
   widens by one at the deep end for units hostable under part
   (chapter h2–h3, section h2–h4, subsection h2–h5, ...), and
   appendices/bibliography/index may reach h4.  Re-derive from
   `f:seclev-aux` rather than guessing, and confirm each widened rank
   with an arXiv-scale witness.
2. **Inline span renditions of block elements.**  `f:blockelement`
   serializes any block element as `span` with the same class token when
   it lands in inline context (footnote bodies are the big producer).
   Witnessed-but-unmodeled renditions from the regression corpus, with
   counts: `span.ltx_para` 1112, `span.ltx_item` 727, `span.ltx_itemize`
   63, `span.ltx_enumerate` 63, `span.ltx_listing` 187,
   `span.ltx_listingline` 1421, `span.ltx_listing_data` 147,
   `span.ltx_inline-logical-block` 138, `span.ltx_equation` 116,
   `span.ltx_equationgroup` 11, `span.ltx_eqn_cell` 246,
   `span.ltx_eqn_row` 4, `span.ltx_theorem` 9 (with `h6` headings
   inside spans!), `span.ltx_float` 66, `span.ltx_figure` 1,
   `span.ltx_caption` 2, `span.ltx_block` 4, `span.ltx_picture` 114.
   These account for a large share of current corpus errors.  Model as a
   parallel "inline rendition" family mirroring the block defs (the
   inline tabular span stack in `scholarly-ltx-floats.rnc` is the
   template for how to do this), scoped to inline contexts — do not just
   widen `ltx.class.span`.
3. **`ltx_missing_image`.**  A failed `ltx:graphics` emits
   `img.ltx_graphics ltx_missing ltx_missing_image` *without* `src` —
   currently unrepresentable (token missing from the semantic modifiers,
   and `ltx.image.attrs` requires src/srcset).  Decide whether it is
   accepted-as-faithful (like `ltx_ERROR`) and model it, or leave it a
   validation error by policy.  Document the decision either way.
4. **Author-metadata span scoping.**  `ltx.author.span.elem`
   (`ltx_personname`, `ltx_contact`, `ltx_author_before/after`, ...) is
   still a member of the general `ltx.Inline.class`, so author spans
   validate in arbitrary prose.  Scope them: `ltx_personname`/`ltx_contact`
   inside `span.ltx_creator`, the before/after separators inside
   `div.ltx_authors`.  Needs witness confirmation that nothing else
   emits them mid-prose (check `\thanks`/`\and` edge cases at scale).
5. **Re-confirm the narrow unions at arXiv scale.**  Cheap re-runs of
   the witness scan to either harden or relax with evidence:
   - appendix/bibliography/index title ranks (h3 witnesses currently come
     only from files that are invalid for other reasons);
   - `tfoot` (upstream-sanctioned, zero witnesses so far);
   - `br.ltx_break ltx_break` duplicate-token quirk (still emitted by
     current oxide? if oxide fixes it, drop the optional duplicate);
   - `dt`/`dd` never carrying anything but `ltx_item`;
   - equation-row class shapes (only two shapes are modeled:
     `ltx_eqn_row ...` and `ltx_equation ... ltx_eqn_row ...`);
   - moderncv (`ltx.cv.*`) and the any-rank `ltx.heading.elem` — zero
     witnesses in the current corpora; find real moderncv output or cut
     the whole cv module into a separate opt-in profile.
6. **Scaffold attribute wildcard.**  arXiv/ar5iv chrome elements accept
   `attribute * - class { text }*`.  The class vocabulary is pinned but
   attributes are open.  If the arXiv chrome templates are stable enough
   on the sample set, pin the attribute vocabulary per element; keep the
   wildcard only if the templates churn in practice.
7. **Known accepted limitation** (document, don't chase): rank
   consistency across a document (all `ltx:section`s share one rank per
   `f:seclev-aux`) is not expressible in RELAX NG; the schema enforces
   per-unit rank *ranges* only.

## Where things live

- Gates: `tests/html-scholarly/` (9 valid must pass, `invalid/` must fail).
- Local witness corpus (mixed quality, not a gate):
  `~/data/html_regressions` — `unpacked/` is perl-latexml,
  `rust_*_unpacked/` are oxide builds.
- Upstream checkout: `~/LaTeXML`.
- Docs regeneration: `tools/generate-scholarly-schema-docs` (needs the
  latexml-oxide sibling checkout).
