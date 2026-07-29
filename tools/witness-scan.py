#!/usr/bin/env python3
"""Tabulate corpus witnesses for each questionable variant in the
scholarly schema. Walks start tags with a context stack."""
import collections
import html.parser
import os
import sys

VOID = {"br", "img", "input", "meta", "link", "hr", "col", "wbr",
        "source", "area", "base", "embed", "param", "track"}

counts = collections.Counter()
samples = {}


def note(key, where):
    counts[key] += 1
    samples.setdefault(key, where)


class Scan(html.parser.HTMLParser):
    def __init__(self, fname):
        super().__init__(convert_charrefs=True)
        self.fname = os.path.basename(fname)
        self.stack = []  # (tag, first_class_token, full_class)

    def loc(self):
        line, col = self.getpos()
        return f"{self.fname}:{line}"

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        cls = (d.get("class") or "").split()
        first = cls[0] if cls else ""
        parent = self.stack[-1] if self.stack else ("", "", [])
        ptag, pfirst, pcls = parent
        w = self.loc()

        if tag == "a":
            key = ("a",
                   "href" if "href" in d else "nohref",
                   first or "noclass",
                   "name" if "name" in d else "")
            note(key, w)
        if tag == "span" and first:
            note(("span", first), w)
            if first == "ltx_rule":
                note(("span-rule-parent", ptag, pfirst), w)
            if first in ("ltx_text",) and len(cls) > 1:
                pass
        if tag in ("sup", "sub") and first:
            note((tag, first), w)
        if tag == "br":
            if cls.count("ltx_break") > 1:
                note(("br-dup-class", " ".join(cls)), w)
            else:
                note(("br", first or "noclass"), w)
        if tag in ("li", "dt", "dd"):
            note((tag, first or "noclass", pfirst), w)
        if tag == "tr":
            note(("tr", " ".join(cls) or "noclass"), w)
        if tag in ("td", "th"):
            # find enclosing table's first class
            tbl = next((c for t, c, _ in reversed(self.stack)
                        if t == "table"), "")
            note((tag, first or "noclass", "in", tbl), w)
        if tag == "table":
            note(("table", first or "noclass"), w)
        if tag in ("thead", "tbody", "tfoot"):
            note((tag, " ".join(cls) or "noclass"), w)
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            kind = [c for c in cls if c.startswith("ltx_title_")]
            note(("heading", tag, ",".join(kind) or ("cls:" + first if first else "noclass"),
                  "in", ptag, pfirst), w)
        if tag == "figure":
            note(("figure", first or "noclass"), w)
        if tag == "img" or tag == "object":
            note((tag, first or "noclass"), w)
        if tag == "abbr":
            note(("abbr", first or "noclass"), w)
        if tag == "cite":
            note(("cite", first or "noclass"), w)
        if tag == "em":
            note(("em", first or "noclass"), w)
        if tag == "div" and first in ("ltx_rdf",):
            note(("div", first), w)
        if tag == "section":
            note(("section", first or "noclass"), w)
        if tag == "footer":
            note(("footer", first or "noclass"), w)
        # Inline.class members directly inside li.ltx_bibitem
        if ptag == "li" and pfirst == "ltx_bibitem":
            note(("bibitem-child", tag, first or "noclass"), w)
        # figure children
        if ptag == "figure":
            note(("figure-child", tag, first or "noclass"), w)
        # frontmatter/theorem h6 title kinds
        if tag == "h6":
            kind = [c for c in cls if c.startswith("ltx_title_")]
            note(("h6-kind", ",".join(kind) or "none", "in", pfirst), w)
        # equation table structure
        if pfirst.startswith("ltx_equation") and tag == "tbody":
            note(("eqn-tbody", " ".join(cls) or "noclass"), w)

        if tag not in VOID:
            self.stack.append((tag, first, cls))

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        # pop back to matching open tag if present
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                return


def main(paths):
    files = []
    for p in paths:
        if os.path.isfile(p):
            files.append(p)
        else:
            for root, _d, names in os.walk(p):
                files.extend(os.path.join(root, n)
                             for n in names if n.endswith(".html"))
    for f in sorted(files):
        with open(f, encoding="utf-8", errors="replace") as fh:
            try:
                Scan(f).feed(fh.read())
            except Exception as e:
                print(f"parse-fail {f}: {e}", file=sys.stderr)
    for key, n in sorted(counts.items(), key=lambda kv: (kv[0][0], -kv[1])):
        print(f"{n:7d}  {key}   e.g. {samples[key]}")


if __name__ == "__main__":
    main(sys.argv[1:])
