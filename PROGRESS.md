# Scholarly HTML Validation Progress

## Current Status

- Added representative arXiv/ar5iv HTML fixtures under `tests/html-scholarly/`.
- Rebuilt `build/dist/vnu.jar` with the scholarly schema and checker updates.
- Confirmed the full `tests/html-scholarly` directory validates with:

```sh
java -jar build/dist/vnu.jar --schema http://s.validator.nu/html5-scholarly.rnc --format gnu --skip-non-html tests/html-scholarly
```

## Recent Schema/Checker Work

- Expanded the LaTeXML scholarly profile to cover observed appendix, quote,
  listing, flex-figure, transformed-table, standalone-rule, and subscript
  structures.
- Split listing structure into outer listing, data wrapper, and line elements
  instead of treating all listing `div`s as one recursive shape.
- Split flex figures into container, cell, and break elements so flex layout is
  modeled compositionally.
- Separated inline listing token modifiers from the general class modifier
  bucket.
- Allowed MathML Content expressions inside `annotation-xml`.
- Removed the checker's hardcoded MathML known-element assertion; MathML
  vocabulary and placement now fall through to Relax NG validation.
- Adjusted heading hierarchy checking to ignore LaTeXML generated non-outline
  headings such as theorem, proof, abstract, keyword, and classification labels.
- Kept `title` and `target` support on `a` elements through the existing common
  and hyperlink attribute paths.

## Schema Organization

The scholarly LaTeXML profile is split into focused RELAX NG compact modules
under `schema/html5/`.  `scholarly-ltx.rnc` remains the public entry point and
declares only the profile start pattern plus module includes, so existing
drivers can continue to include it unchanged.

- `scholarly-ltx-model.rnc`: the class system — union bases (`ltx.Inline.class`,
  `ltx.Block.class`, `ltx.Para.class`, `ltx.Misc.inline.class`,
  `ltx.Misc.block.class`, `ltx.Meta.class`) and the four shared content models
  mirroring LaTeXML's `Inline.model` / `Block.model` / `Para.model` /
  `Flow.model`.
- `scholarly-ltx-classes.rnc`: shared attributes and class-token contracts.
- `scholarly-ltx-inline.rnc`: inline phrasing, links, images, breaks, errors,
  and MathML hooks.
- `scholarly-ltx-scaffold.rnc`: hosted arXiv/ar5iv chrome, table of contents,
  page shell, and generated footer provenance.
- `scholarly-ltx-structure.rnc`: article, front matter, headings, CV header, and
  per-level sectional structure.
- `scholarly-ltx-blocks.rnc`: paragraphs, logical blocks, generic blocks,
  quotations, listings, pagination, and standalone rules.
- `scholarly-ltx-floats.rnc`: theorem-like blocks, bibliography, figures,
  flex/transformed wrappers, equations, tables, and lists.

Build support for the split lives in `build/build.py` and
`resources/entity-map.txt`.  Both need entries for every included module so
local schema resolution works from `http://s.validator.nu/html5/...` inside the
packaged `vnu.jar`.

## Fixture Normalization Policy

The scholarly fixtures are intended to be validator-valid regression fixtures,
not byte-for-byte upstream archives. Repairs should be minimal and documented.

Current repairs include:

- Removed parser-invalid duplicate `title` attributes from hosted arXiv header
  links.
- Removed invalid `target` from a canonical `link`.
- Replaced invalid negative `padding-top` inline styles with negative
  `margin-top` in one fixture.

## Critical Design Improvements

### 1. Separate Base Classes From Modifiers

Status: partially complete.

The current `ltx.class.extra` bucket is too broad. It lets many class tokens
appear in contexts where LaTeXML probably does not intend them.

Improve the model by separating:

- base classes that identify the LaTeXML element intent, such as `ltx_para`,
  `ltx_p`, `ltx_figure`, `ltx_listingline`, and `ltx_text`;
- global modifiers;
- inline modifiers;
- block modifiers;
- float and layout modifiers;
- bibliography modifiers.

This is the highest-value cleanup because it will make the schema stricter
without losing LaTeXML expressiveness.

Completed so far:

- listing structural classes are no longer general modifiers;
- listing inline token classes are accepted through a separate inline modifier
  path.

Remaining work:

- split the rest of `ltx.class.extra` into context-specific modifier sets for
  block, float, bibliography, table, and generated-layout contexts.

### 2. Model Listings as a Family

Status: complete for current fixtures.

The current listing model treats `ltx_listing`, `ltx_listing_data`, and
`ltx_listingline` as one recursive generic `div` shape. That validates current
examples but does not capture the real structure.

Target model:

- `ltx.listing.elem`: outer listing block, class `ltx_listing` or
  `ltx_lstlisting`;
- `ltx.listing.data.elem`: data wrapper, class `ltx_listing_data`;
- `ltx.listing.line.elem`: line wrapper, class `ltx_listingline`;
- listing line content should be inline-like and allow math, spans, anchors,
  emphasis, subscripts, and line breaks.

### 3. Stop Hand-Maintaining MathML Element Names

Status: complete.

The checker no longer keeps a separate MathML known-element set. MathML
vocabulary and placement are left to the Relax NG schema, which is the source of
truth.

### 4. Tighten Figure, Flex, and Transformed Wrappers

Status: partially complete.

The current figure model is broader than ideal. It accepts enough observed
LaTeXML material to validate the examples, but it should become more
compositional.

Target shape:

- `figure` contains captions plus `ltx.figure.body`;
- `ltx.figure.body` contains known figure payloads;
- flex figures contain flex cells and breaks;
- flex cells contain figure body;
- transformed wrappers contain table, image, equation, or similarly concrete
  visual payloads.

Completed so far:

- flex figures now distinguish container, cell, and break elements;
- flex cells are constrained around `ltx.figure.body`;
- transformed wrappers remain explicit table/image/equation payload wrappers.

Remaining work:

- continue narrowing `ltx.figure.body` once more examples clarify whether
  direct listing lines, lists, and rules are stable LaTeXML outputs or fixture
  edge cases.

### 5. Document Fixture Repairs

Each fixture repair should be easy to audit and should explain whether it is:

- a parser-level repair;
- a CSS-validity repair;
- a hosted-page chrome repair; or
- a deliberate upstream-output normalization.

### 6. Keep Hosted Chrome Separate

The arXiv/ar5iv hosted page scaffolds should stay separate from the LaTeXML
article model. Header/footer/forms/buttons/classes from hosted chrome should not
leak into scholarly article content.

## 2026-06-06: Sandbox-Corpus Round + LaTeXML.rnc Audit

Converted three fresh arXiv sources (`/data/sandbox_sample/1905`) with
latexml-oxide master (`968ebd586a`) and validated against the scholarly
profile. New fixtures: `1905.03077.html` (amsart), `1905.03079.html` (CVPR,
multi-file), `1905.03080.html` (MNRAS). Initial run: 0 / 31 / 139 errors;
all clean after the schema round below.

Schema additions, each verified against the source-of-truth intent in
latexml-oxide's `resources/RelaxNG/` + `resources/XSLT/`:

- `ltx.glossaryref.elem` (`abbr`/`span`, class `ltx_glossaryref`): the
  HTML transform picks `abbr` when the short form is shown, `span`
  otherwise (`LaTeXML-inline-xhtml.xsl`); `glossaryref` is Inline.class.
- `ltx.logical-block.elem` (`div.ltx_logical-block`): Para.class member;
  `logical-block_model = Para.model`, so its content is `ltx.block.content*`.
- Frontmatter notes: the document model admits `Meta.class` (which includes
  `ltx:note`) among front matter — MNRAS `\pubyear`/`\pagerange` emit
  `span.ltx_note.ltx_note_frontmatter.ltx_role_*` there. Added
  `ltx.note.elem` to `ltx.document.front.elem`, plus `ltx_note_type` as a
  span base token (emitted for every non-footnote note role).
- `ltx.object.elem`: `ltx:graphics` renders as `object type="image/svg+xml"`
  when the graphic converts to SVG; folded into `ltx.image.elem` as a union
  so object embeds are legal wherever images are.
- Inline tabular family (`span` stand-ins for `table/thead/tbody/tfoot/tr/td`
  with the same `ltx_*` classes): the XSLT's `f:blockelement` serializes
  tabular material with spans in inline context.
- `ltx_eqn_left_padleft`/`ltx_eqn_left_padright`: the XSLT computes
  `ltx_eqn_{$eqpos}_pad{left,right}` with `$eqpos ∈ {left, center}`
  (`fleqn` → left); only the center pair was previously modeled.
- `ltx_href` reference modifier (hyperref's `\href` marker on `a.ltx_ref`).
- Figures allowed inside `span.ltx_transformed_inner`: the upstream XSLT
  hard-codes the inner transform wrapper as `span` even around block
  content (rotated minipage → `figure`), a documented spec deviation we
  accept as dialect.

Conversion-quality issues observed (latexml-oxide bugs, not schema gaps):

- `acronym` package: `\ac{...}` renders as empty
  `<abbr title="" class="ltx_glossaryref"></abbr>` — structure right,
  expansion text and title both lost (witness: 1905.03079).
- `mnras.cls`: `\upmu` undefined, leaks literal `<mtext>\upmu</mtext>`
  into MathML (witness: 1905.03080).

### LaTeXML.rnc audit notes (vs. latexml-oxide master)

Recent intent-schema changes and their scholarly-profile disposition:

- `rule` moved from Inline.class to Para.class | Misc.class — already
  consistent: `ltx.block.rule.elem` sits in `ltx.block.content`, and
  `ltx_rule` remains a span base token for inline appearances.
- `ARIA.attributes` added to `Common.attributes` (all elements may carry
  `aria:*`, surfacing as `aria-*`). The profile currently allows
  `aria.global` everywhere via `ltx.attrs.no-class`; the role-specific
  ARIA states/properties stay gated by the stock HTML5 role machinery.
  Revisit only when LaTeXML output actually emits role-specific `aria-*`.
- `role_side` on XMath: internal math-grammar refinement; does not surface
  in HTML output. No action.

Audit gaps still open (no fixture witnesses yet, deferred until observed):

- `ltx:del` (Inline.class) has no HTML-side pattern;
- `ltx:pagination` is not allowed inside `div.ltx_para` (Para.class allows
  it in the XML model);
- metadata elements (`indexmark`, `glossarydefinition`, `rdf`, `resource`,
  `navigation`) have no HTML-side modeling — most are dropped or
  head-hoisted by the transform, so likely correct to omit.

## 2026-06-06 (later): Three-Layer Architecture Rationalization

The profile was rewritten as a structural mirror of LaTeXML's own schema
architecture, replacing the hand-rolled `ltx.block.content` /
`ltx.inline.elem` unions that had accreted empirically.

**Layer 1 — projection primitives** (`scholarly-ltx-classes.rnc`): attribute
contracts and class-token buckets, unchanged in role.

**Layer 2 — element renditions** (inline/blocks/floats/structure modules):
each `ltx:*` element's HTML rendition(s).  Misc.class members have dual
renditions chosen by the XSLT's `f:blockelement` context: ltx:tabular is
`table.ltx_tabular` in block context but a `span.ltx_tabular` stack inline.

**Layer 3 — class unions and shared models** (`scholarly-ltx-model.rnc`):
union bases declared once (`= notAllowed`) and populated via `|=` next to
each element definition, exactly as LaTeXML-common.rnc and the Nu checker's
own common.rnc do.  Container content models reference the four shared
models per LaTeXML's table: `para_model = Block.model`,
`item_model = tags?, Para.model`, `quote_model = Block.model`,
`abstract_model = Block.model`, `theorem_model = title?, Para.model`,
sections = `title?, (Para.model | deeper sectional units)`.

Sectional units are now per-level elements with monotone descent
(section > subsection > subsubsection > paragraph > subparagraph; appendix
admits all levels), mirroring `section.body.class` et al.  An inverted
hierarchy no longer validates.

Strictness deltas, all verified against a children-tally over every fixture
(zero violations of the LaTeXML models were found in real output):

- tightened: Block.class content (equations, lists, quotes, listings,
  tabulars) is no longer accepted directly inside sections — it must sit
  inside `div.ltx_para`; `li`/`dd` are `tag?, Para.model`; theorem/proof
  bodies are `Para.model`; `div.ltx_para` no longer accepts figures or
  theorems directly.
- loosened uniformly per the models: `ltx:note` (Meta.class) is valid in
  all four models; img/object/br/svg/inline-tabular are available wherever
  the models admit Misc.class; `span.ltx_ERROR` (conversion errors) is
  accepted as faithful output — quality gates should grep for the token.

Deliberate deviations from the XML models, kept and documented in-schema:
`div.ltx_block` carries Flow (not Block.model) because the transform
serializes inline material directly into it; figure payloads admit
Inline.class (minipage serialization); the transform-inner wrapper is a
span that may carry figures (hard-coded span in the upstream XSLT); the
projection scaffolding families (equation tables, note wrappers, flex
figures, inline span-tabular, listing lines, bib internals, page chrome)
stay hand-rolled outside the class system.

Two synthetic negative fixtures lock in the tightenings:
`invalid/synthetic-block-in-section.html`,
`invalid/synthetic-inverted-sections.html`.

## 2026-06-06 (book round): Analysis of Boolean Functions

Converted O'Donnell's AoBF book (gsm-l-odonnell.cls, ~8 MB HTML, 14
chapters, index, TOC) with latexml-oxide master and drove the profile
from 1243 errors to 0.  First book-class source the profile has seen:

- chapter sectional level (`section.ltx_chapter`, `ltx_title_chapter`),
  admitting all deeper units plus hoisted BackMatter (bibliography and
  index land inside chapters in book classes);
- index family per the XML models (`index.body.class = Para.model |
  indexlist`, `indexentry_model = indexphrase, indexrefs?, indexlist?`):
  section.ltx_index > ul.ltx_indexlist > li.ltx_indexentry with nested
  sublists;
- in-document TOC: `nav.ltx_TOC` is Para.class (the XML schema's
  `Para.class |= TOC`), `TOC_model = title?, toclist?`; `toc` and `list`
  prefixes added to the generated-token pattern for `ltx_toc_toc` /
  `ltx_list_toc`;
- `ltx:anchor` renders as `a.ltx_anchor` with a legacy `name` attribute
  alongside `id` — obsolete in HTML5 but deliberate upstream output;
  accepted as a documented deviation;
- `ltx:bibblock` is Inline.model in the XML schema, which includes
  Misc.class; the transform emits the block rendition (table) for
  tabular material inside the bibblock span — accepted, documented;
- bare rows in tabular_model: the parser inserts an implicit class-less
  tbody, so the tbody class token is optional;
- `ltx_align_top`/`ltx_align_bottom` layout modifiers;
- heading-rank skips (h3→h5) suppressed in the scholarly checker mode:
  LaTeXML assigns rank by sectional type and its models permit
  skip-level nesting (\paragraph under \section), so outline-skip
  complaints are generic-profile-only now.

The `\ell@`-undefined conversion error in the book exercised the new
`span.ltx_ERROR` acceptance end-to-end.  Not added as a fixture (8 MB);
the structures it introduced are all model-cited above.

## 2026-06-06 (architect round): error-message precision, docs, corpus harness

- Split the 23-token generic span bucket into role-aligned patterns
  (prose spans, note scaffolding, author metadata); `ltx_tag` now rides
  `ltx.item.tag.elem` and `ltx_bibblock` its dedicated element, so a
  failing span is reported against the intent that failed.
- Equation-table tokens (`ltx_eqn_*`, `ltx_intertext`) moved from the
  global layout bucket into an equation-scoped modifier set -- they can
  no longer appear on unrelated elements.
- Collapsed the duplicated theorem/bibliography h2-h6 title unions into
  references to the shared frontmatter title pattern.
- Docs hardening for the generated schema site: ASCII/TeX-safe comments
  (the pipeline is TeX -- raw `|` and em-dashes mangle), `##` prose on
  every class pattern and union base, ltx:* renditions named in element
  prose, cross-links via \patternref/\moduleref, a landing overview on
  the driver, single banner per module.  Known cosmetic issue left in
  the generator (latexml-oxide): modules carrying the start/document
  patterns appear twice in the site TOC.
- `corpus-validate.py`: batched vnu JSON runs over a directory tree
  with message-category aggregation and per-file ranking -- the tool
  for validating parity-campaign output at arXiv scale.  Demo over the
  current corpus: 12 files, 9 clean, findings only in the invalid set.

## Binding-Introduced Extension Vocabularies (audit, 2026-06-06)

LaTeXML bindings (`*.sty.ltxml` / `*_sty.rs`) introduce their own attribute
mini-languages beyond the core schema; for several, the real abstraction is
added by the XSLT.  Survey of latexml-oxide master:

- **Generated class-token families.**  Open generative (user-controlled
  names, only regex-validatable): `ltx_theorem_<name>` (\newtheorem),
  `ltx_lst_language_<lang>` (listings), `ltx_tocentry_<type>` /
  `ltx_toclist_<type>`, `ltx_glossary_<key>[-plural|-indefinite]`,
  `ltx_role_<name>`.  Closed enumerations: `ltx_bib_*` (BibTeX types and
  field specs, make_bibliography.rs), `ltx_lst_<style>` syntax categories,
  `ltx_align_*`, `ltx_font_*` / `ltx_mathvariant_*`, `ltx_framed_*`,
  `ltx_eqn_*`, `ltx_math_<mime>`, `ltx_unit`.  The current
  `ltx.class.generated.modifier` NMTOKEN pattern covers the open families;
  the closed families live in the modifier buckets.
- **ARIA.**  Bindings emit `aria:*` (fontawesome `aria:hidden`, acmart
  `aria:labelledby`); the XSLT maps `aria:*`→`aria-*` and `aria:role`→`role`.
  Both observed attributes are within `aria.global`, which the profile
  already allows everywhere.
- **data-\*.**  `data:sourcepos` → `data-sourcepos` (source maps); the XSLT
  maps any foreign-prefix attribute to `data-<prefix>-*`.  Not yet admitted
  by `ltx.attrs.no-class` — add when sourcemap-bearing output needs
  validation.
- **Raw HTML / foreign namespaces.**  `{rawhtml}`/`{htmlonly}` environments
  (html_sty) pass arbitrary HTML through; orcidlink/xy emit `svg:*` elements
  directly.  The profile accepts `svg` via the host grammar; raw HTML
  pass-through is an open extension surface to model when witnessed.

Direction for modularization (not yet implemented): keep the core class
system closed, and add per-convention extension modules
(e.g. `scholarly-ltx-ext-theorems.rnc`, `-ext-listings.rnc`) that `|=` extra
members into the unions and modifier buckets, so package vocabularies stay
auditable units rather than folding into the core.  Open families stay
regex-validated; closed families get explicit enumerations with their
emitting binding cited.

## Guiding Principle

The scholarly schema should validate that HTML is a faithful LaTeXML rendering
of the XML model, not merely that a recent arXiv page happened to contain a set
of class tokens.
