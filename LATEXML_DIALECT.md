# LaTeXML HTML Dialect

## Quickstart

### Validate any HTML file against the LaTeXML profile

```sh
java -jar build/dist/vnu.jar \
  --schema http://s.validator.nu/html5-scholarly.rnc \
  path/to/file.html
```

A few useful variants:

```sh
# Multiple files at once
java -jar build/dist/vnu.jar --schema http://s.validator.nu/html5-scholarly.rnc \
  doc1.html doc2.html

# A directory tree (recursive)
java -jar build/dist/vnu.jar --schema http://s.validator.nu/html5-scholarly.rnc \
  path/to/html-dir/

# A live URL (e.g. arXiv- or ar5iv-hosted document)
java -jar build/dist/vnu.jar --schema http://s.validator.nu/html5-scholarly.rnc \
  https://ar5iv.labs.arxiv.org/html/2110.06709

# Read from stdin
cat path/to/file.html | \
  java -jar build/dist/vnu.jar --schema http://s.validator.nu/html5-scholarly.rnc -

# Other formats: --format text|gnu|xml|json
java -jar build/dist/vnu.jar --schema http://s.validator.nu/html5-scholarly.rnc \
  --format gnu path/to/file.html
```

### Convert a LaTeXML source to HTML5 for round-trip testing

```sh
latexmlc --format=html5 \
  --destination=/tmp/article.html \
  path/to/source.tex
```

Then run the validator on `/tmp/article.html` using the command above.

### Notes

The acceptance path for this project is the nuvalidator HTML5 engine. Do not
normalize through XHTML for conformance testing: that bypasses the parser path
we need to harden and introduces XML-only namespace and case artifacts that are
not part of the emitted HTML5 dialect.

## Approach

This schema is a constrained publication profile for the HTML5+MathML+SVG
dialect emitted by LaTeXML. The goal is not general scholarly HTML validation.
The goal is to require the structural scaffolds, class tokens, and co-occurring
attributes that carry LaTeXML semantics after XML is transformed to HTML.

The top-level design separates page scaffolding from article content:

```rnc
ltx.content.start =
  ( ltx.page.elem | ltx.arxiv.body | ltx.ar5iv.body )
```

Those three wrappers represent the currently supported top-level page shapes:
vanilla LaTeXML, arXiv-hosted HTML, and ar5iv-hosted HTML. All three converge on
the same shared LaTeXML content model through `ltx.page.content.elem` and
`ltx.document.elem`.

The content model is intentionally named by publication intent rather than by
raw HTML tags. For example, titles, abstracts, theorem-like blocks,
bibliographies, equation tables, and generated page shells each have their own
named patterns. This keeps validation failures close to the semantic contract
that failed.

Class validation is central. LaTeXML's XML schema records semantics in element
names such as `section`, `para`, `equation`, `bibblock`, and `theorem`. The
HTML transform preserves those semantics mostly as `class` tokens such as
`ltx_section`, `ltx_para`, `ltx_equation`, `ltx_bibblock`, and `ltx_theorem`.
The profile therefore removes generic `class` from LaTeXML attribute helpers and
reintroduces class requirements through named patterns such as
`ltx.class.section`, `ltx.class.para`, and `ltx.class.equation.table`.

Hosted page chrome is modeled separately from authored article content. The
arXiv and ar5iv wrappers may contain navigation, issue-report controls, footer
links, and generated provenance. Those controls should be admitted only at the
scaffold level and should not broaden what is valid inside the LaTeXML article.

MathML and SVG are parsed through the HTML5 parser and delegated to the existing
validator.nu schemas, with narrow profile extensions for observed LaTeXML
output. Current examples include MathML `intent` on `math` and an ar5iv/LaTeXML
SVG label pattern where SVG `text` contains a transformed `g` that wraps a
MathML `foreignObject`.

## Generating Schema Documentation

Use the repository helper to generate a standalone split HTML documentation site:

```sh
tools/generate-scholarly-schema-docs
```

By default, this writes the site to:

```text
build/docs/scholarly-schema/index.html
```

Use `--output DIR`, `--work DIR`, or `--latexml-dir DIR` to override the output
site directory, intermediate build directory, or LaTeXML checkout.

The LaTeXML manual has a schema documentation generator at:

```sh
/home/deyan/git/my-LaTeXML/doc/manual/genschema
```

That script does not read RELAX NG compact syntax directly. The helper above
performs the full workflow: copy the split schema modules to a work directory,
convert them to XML RELAX NG `.rng`, run `genschema`, wrap the generated
`schema.tex`, and run `latexmlc`.

The manual equivalent is:

```sh
DOCBUILD=/tmp/ltx-schema-doc
rm -rf "$DOCBUILD"
mkdir -p "$DOCBUILD"

cp schema/html5/scholarly-ltx*.rnc "$DOCBUILD"/
trang "$DOCBUILD/scholarly-ltx.rnc" "$DOCBUILD/scholarly-ltx.rng"

cd "$DOCBUILD"
/home/deyan/git/my-LaTeXML/doc/manual/genschema --force \
  scholarly-ltx.rng schema.tex
```

`trang` converts the included compact modules as sibling `.rng` files, so the
generated `schema.tex` preserves the module split.

To build a standalone HTML documentation site, wrap the generated `schema.tex`
in a small LaTeX document:

```tex
\documentclass{book}
\usepackage{latexml}
\usepackage{latexmlman}
\usepackage{makeidx}
\makeindex
\title{Scholarly LaTeXML HTML Schema}
\author{validator}
\date{\today}
\begin{document}
\maketitle
\tableofcontents
\chapter{Scholarly LaTeXML HTML Schema}
\input{schema}
\end{document}
```

Save that wrapper as `schema-doc.tex` in `$DOCBUILD`, then run:

```sh
TEXINPUTS=/home/deyan/git/my-LaTeXML/doc/sty:/home/deyan/git/my-LaTeXML/blib/lib/LaTeXML/texmf:: \
latexmlc --format=html5 \
  --split --splitnaming=labelrelative --splitat=section \
  --sourcedir="$DOCBUILD" \
  --destination="$DOCBUILD/site/index.html" \
  "$DOCBUILD/schema-doc.tex"
```

The resulting site has an index page plus one split page per schema module. A
focused scholarly-profile build will leave cross references to upstream HTML5
patterns such as `common.attrs.id`, `aria.global`, and `img.attrs.src`
unresolved unless the broader HTML5 schema is also documented.
