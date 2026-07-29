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
   - `./corpus-validate.py --json out.json <corpus>` → diff the exact
     failing-file set (the `by_file` keys in the JSON dump) against a
     pre-change baseline; the failing-file set must not grow
     (message-count drift inside already-invalid files is jing recovery
     noise and acceptable).  Do NOT diff the printed report: its file
     list is top-40 only, so small-error-count files are invisible there.
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
3. ~~**`ltx_missing_image`.**~~  Done in the pass-2 round: modeled as a
   dedicated img variant (`src=""` + the ltx_missing markers), accepted
   as faithful conversion output like `ltx_ERROR`.
4. ~~**Author-metadata span scoping.**~~  Done in the pass-2 round:
   authors > (creator | before/after separator); creator > personname?,
   author-notes?; contact scoped inside author-notes.  Re-confirm at
   arXiv scale that nothing emits these spans mid-prose.
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

## Pass-2 leftovers (2026-07-29 round)

The second audit pass tightened the attribute contract (hyperlink/img/
cell attrs cut to the emitted set), pruned the scaffold element list to
the witnessed chrome, scoped the author block, cut `p` from equation
cells, replaced the never-matching csquotes/citemacro prefix entries
with their real forms (bare quote tokens; dynamic `ltx_citemacro_*` and
`ltx_lst_*` families), added missed upstream tokens (`ltx_parbox`,
`ltx_align_justify`, flex sizes, logos, `ltx_Url`, ...), and modeled
`ltx:verbatim` (`code`/`pre`) and the missing-image img.  New leftovers:

- **Inline span-stack cell structure**: the unmodeled inline renditions
  carry `rowspan`/`colspan` attributes and `ltx_colspan_N`/
  `ltx_rowspan_N` tokens on `span.ltx_td` — fold into worklist item 2.
- **`div.ltx_inline-block` inside equation cells** (~9 witnesses, from
  `\parbox` in display math): currently rejected because equation cells
  admit only inline Misc; confirm the upstream emission context, then
  admit `ltx.Misc.block.class` in `ltx.equation.number.cell.inner` if
  sanctioned.
- **Element gaps with few witnesses**: `div.ltx_epigraph` (+ source/
  text spans), `div.ltx_titlepage` — model when the arXiv sample set
  provides enough witnesses.
- **`headers`/`scope` on cells**: cut as never-emitted; revisit if an
  accessibility postprocessing pass starts adding them.

## Where things live

- Gates: `tests/html-scholarly/` (9 valid must pass, `invalid/` must fail).
- Local witness corpus (mixed quality, not a gate):
  `~/data/html_regressions` — `unpacked/` is perl-latexml,
  `rust_*_unpacked/` are oxide builds.
- Upstream checkout: `~/LaTeXML`.
- Docs regeneration: `tools/generate-scholarly-schema-docs` (needs the
  latexml-oxide sibling checkout).
