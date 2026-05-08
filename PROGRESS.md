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

- `scholarly-ltx-classes.rnc`: shared attributes and class-token contracts.
- `scholarly-ltx-inline.rnc`: inline phrasing, links, images, breaks, and MathML
  hooks.
- `scholarly-ltx-scaffold.rnc`: hosted arXiv/ar5iv chrome, table of contents,
  page shell, and generated footer provenance.
- `scholarly-ltx-structure.rnc`: article, front matter, headings, CV header, and
  recursive section structure.
- `scholarly-ltx-blocks.rnc`: paragraphs, generic blocks, quotations, listings,
  pagination, and standalone rules.
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

## Guiding Principle

The scholarly schema should validate that HTML is a faithful LaTeXML rendering
of the XML model, not merely that a recent arXiv page happened to contain a set
of class tokens.
