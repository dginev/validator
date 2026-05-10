# Schema Documentation: Plan

End-to-end plan for the scholarly-schema documentation site driven by
`tools/generate-scholarly-schema-docs`. Source of truth: the RelaxNG
Compact (`.rnc`) schema set under `schema/html5/`. Output: a
rustdoc-styled HTML site at `build/docs/scholarly-schema/`.

## Reader

A developer who needs to locate a definition by name and read its
content model. Discovery and learning workflows exist but don't
reshape the design.

## Acceptance criteria

The site is done when:

1. Any content model reads as a structural expression at a glance —
   sequence/choice/repetition visible without parsing operator chars
   in linear order.
2. Any definition is locatable by name in ≤5 seconds (sidebar scroll
   + browser Ctrl-F; no search engine).
3. Cross-reference is one click; back-button restores scroll position.
4. Every definition's kind is visible without reading the label
   (kind chip + typographic distinction).
5. Dark theme passes WCAG AA on body text.

## Pipeline (target shape)

```
.rnc files  ──trang──▶  .rng  ──genschema──▶  schema.tex
                                                    │
                                       schema-doc.tex (template)
                                                    │
                            latexml_oxide --schemadocs
                                --split --splitat=section ─┐
                                                           ▼
                                       rustdoc-styled HTML site
```

Everything from `schema-doc.tex` onward runs in a single
`latexml_oxide` process: TeX → ltx XML → Split → Scan →
MakeBibliography → CrossRef → Graphics → MathML → XSLT →
`schema_docs` post-pass → write. One in-memory `ObjectDB` shared
across phases; no inter-process file round-trips.

## Move to Rust

The original pipeline used three Python post-processors over LaTeXML's
stock HTML, plus the Perl `latexmlman.sty` and a hand-curated TOML for
narratives. Goal: pure Rust except for trang (Java RNC→RNG) and
genschema (Perl, the next item to port).

### Landed

On `split-for-schema` (dginev/latexml-oxide):

* **`latexmlman.sty` → `latexml_contrib/src/latexmlman_sty.rs`** — native
  binding for `\schemamodule`, `\elementdef`, `\attrdef`, `\patterndef`,
  `\patternadd`, `\patterndefadd`, `\moduleref`, `\patternref`,
  `\elementref`, `\attrval`, `\typename`, `\moduleabstract`. Two
  intentional divergences from upstream: (a) bare
  `\section{Module \texttt{#1}}` because oxide's `\section` lacks
  optional-arg parsing; `[short]{long}` would silently drop the
  section; (b) no `\cleanhypername` — HTML5 ids accept `:`. Note:
  `DefEnvironment!` emits XML directly, not TeX; envs whose body needs
  TeX expansion (`schemamodule`, `moduledescription`) are decomposed
  into `\X` / `\endX` `DefMacro` pairs.

* **`xslt::process` per-doc href relativization** — split sub-pages
  in `Ch1/` need `../foo.css` etc. The XSLT pipeline now rewrites
  the `CSS` / `JAVASCRIPT` / `ICON` parameters per-doc with `../` ×
  dest-depth-below-site.

* **`latexml_post::schema_docs` post-pass** — replaces three Python
  scripts. Triggered by `latexml_oxide --schemadocs`; no-op on inputs
  without the marker classes. Does, in order: (i) lift the
  `<p class="schema_module_narrative">` paragraph out of the
  description list it lands in into a clean `<aside>` below the
  section heading; (ii) pretty-print content models with
  operator-leading multi-line layout (inline iff ≤4 operands and no
  nested group); (iii) decorate definition `<dt>`s with kind chips,
  promote `<a id="schema.X">` anchors onto the parent `<dt>` for
  stable URLs, append `§` permalinks; (iv) build the per-module
  sidebar item index, alphabetised within
  Patterns / Elements / Attributes / Pattern Additions. (Rust's
  `regex` is RE2-based and lacks backreferences; the kind/anchor
  matchers identify name and id tokens independently.)

* **Module narratives via RNC `## comments`** — trang preserves them
  as `<a:documentation>` annotations; `RelaxNG.pm`'s emitter folds
  them into the doc-arg of whichever `\patterndef` happens to come
  first per module; `tools/genschema` post-processes its own output
  to lift that doc-arg into a `\moduleabstract{…}` macro at module
  level. One source of truth (the `.rnc` file); no parallel TOML.

* **Validator-side cleanup** — three `.py` post-processors deleted;
  CSS shipped from oxide's `resources/CSS/`;
  `tools/module-annotations.toml` deleted; the validator wrapper
  collapsed to ~25 lines that point oxide's tool at
  `schema/html5/scholarly-ltx.rnc`.

### Remaining: `tools/genschema` (Perl) → Rust

The only Perl left in the pipeline. Shells
`LaTeXML::Common::Model::RelaxNG.pm` (819 lines, ~30 subs) to walk the
RNG and emit `schema.tex`.

**Existing target**: `latexml-oxide/latexml_core/src/common/relaxng.rs`
is a 43-line stub whose struct fields, method names, and TODO slots
already match `RelaxNG.pm`. Wired into `latexml_core::common::model`
(the umbrella schema-model); the parent abstraction is in place.

**Proposed structure** — promote the stub to a directory module so
the three sub-concerns each get their own file:

```
latexml_core/src/common/
  model.rs                  schema-model umbrella (~920 LoC, exists)
  relaxng/
    mod.rs                  Relaxng struct, Pattern enum, re-exports
    scan.rs                 RNG XML → AST              (RelaxNG.pm L100–390)
    simplify.rs             AST normalization          (L438–525)
    tex.rs                  schema-doc emission        (L550–815)
```

**Binary entry point**: `latexml_oxide/bin/genschema_oxide.rs`, sibling
to existing `latexmlmath_oxide.rs` / `latexmlpost_oxide.rs`. Thin
shim: `Relaxng::load_schema` → `Relaxng::document_modules` → stdout.

**Phases** (each compiles + has a golden test):

1. **AST + scanner.** Walk the RNG XML via libxml; build the typed
   AST. Test: snapshot the `Relaxng` Debug dump and verify against
   the Perl `showSchema` output for `scholarly-ltx.rng`.
2. **Simplifier.** Port `simplify*`, `simplifyCombination`,
   `extractStart`, `eqOp`. Test: post-simplify snapshot matches.
3. **TeX emitter.** Port `documentModules` + `toTeX*` family. Test:
   emitted `schema.tex` byte-equivalent to Perl `tools/genschema`
   output, on `scholarly-ltx.rng` and on LaTeXML's `LaTeXML.rng` as
   a wider-feature corpus.
4. **Wire-up.** Switch `tools/generate-scholarly-schema-docs` from
   `tools/genschema` to `genschema_oxide`. Keep the Perl version as
   the golden-test oracle; delete only after Phase 3 byte-equivalence
   holds across the full corpus.

**Subtleties / risk areas**:

* **`include` with overrides.** Our schema chains
  `scholarly-ltx.rnc → scholarly-ltx-classes.rnc` etc.; trang
  flattens to one RNG, so the scanner sees one tree. Module
  boundaries come from the `urn:x-LaTeXML:RelaxNG:` URI-prefix logic
  inside `documentModules`; bit-for-bit fidelity required.
* **Combine semantics.** `combine="choice"` and `combine="interleave"`
  on `<define>` produce `defchoice` / `definterleave` AST ops; the
  TeX emitter routes these to `\patternadd` (no hypertarget) vs
  `\patterndef`. The `defined_patterns` map tracks which names have
  a base definition, retroactively upgrading `\patternadd` to
  `\patterndefadd` if no base is found. Silent misrouting hazard.
* **`getSymbolUses` ("Used by:" lists).** Built during scan from every
  `<ref>` site; emitted in `toTeX_def` as the trailing `Used by`
  item. Must be globally consistent across the simplification pass.
* **`doc` op routing.** Today the validator-side `tools/genschema`
  post-processes its own emission to lift the first `doc` op of each
  module into `\moduleabstract`. Native port can do this lift in
  `tex.rs` without the regex step — emit `\moduleabstract{…}`
  directly the first time a `doc` op is hit inside a module.
* **`SKIP_SVG` / `SKIP_ARIA` / `SKIP_XHTML` flags** — module-elision
  in `documentModules`. Port with the same defaults; consider exposing
  on the public API as an `Options` struct.
* **Namespace cleanup.** `cleanTeX` / `cleanTeXName` strip
  `urn:x-LaTeXML:RelaxNG:` and `ltx:` prefixes. Behaviour pinned by
  the golden corpus.

## Out of scope

Client-side search; hover popovers; per-element / per-pattern pages;
visualisations; hand-curated semantic categories; a "Reading the
schema" tutorial; corpus examples; porting trang.

## Open risks

* **Golden-test fragility.** Perl and Rust may diverge on whitespace,
  attribute-list ordering, or numeric formatting. Tokenise both
  outputs before comparison rather than raw `diff`.
* **`RelaxNG.pm` behavioural drift.** Periodic re-runs of the golden
  test against the upstream Perl as it evolves.
