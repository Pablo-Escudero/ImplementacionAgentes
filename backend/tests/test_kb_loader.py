from scripts.load_knowledge_base import (
    build_document_text,
    cut_trailing_sections,
    html_to_text,
    safe_filename,
    truncate,
)

HTML = """
<div class="mw-parser-output">
<aside class="portable-infobox"><div class="pi-item pi-data">
  <h3 class="pi-data-label">Born</h3><div class="pi-data-value">November 16, 1988</div></div>
  <div class="pi-item pi-data"><h3 class="pi-data-label">Occupation</h3>
  <div class="pi-data-value">Rockerboy</div></div></aside>
<p><b>Johnny Silverhand</b> was the <a href="/x">lead singer</a> of <i>Samurai</i>.<sup class="reference">[1]</sup></p>
<h2><span class="mw-headline">Biography</span><span class="mw-editsection">[edit]</span></h2>
<p>Born in   Texas.</p>
<ul><li>Fought in the war</li></ul>
<table><tr><td>ruido de tabla</td></tr></table>
<h2><span class="mw-headline">Gallery</span></h2><p>no debe aparecer</p>
</div>
"""


def test_html_to_text_cleans_and_keeps_structure():
    text = html_to_text(HTML)
    assert "Born: November 16, 1988" in text and "Occupation: Rockerboy" in text
    assert "Johnny Silverhand was the lead singer of Samurai." in text
    assert "[1]" not in text and "[edit]" not in text and "ruido de tabla" not in text
    assert "== Biography ==" in text and "- Fought in the war" in text and "Born in Texas." in text


def test_cut_trailing_sections():
    raw = "Intro\n\n== Historia ==\nTexto\n\n== Referencias ==\n1. algo\n== Otra ==\nmás"
    out = cut_trailing_sections(raw)
    assert "Texto" in out and "Referencias" not in out and "algo" not in out
    assert "== References ==" not in cut_trailing_sections(html_to_text(HTML) + "\n== References ==\nx")
    assert "no debe aparecer" not in cut_trailing_sections(html_to_text(HTML) + "")  # Gallery cortada


def test_truncate_and_filename_and_header():
    text = "linea\n" * 1000
    out = truncate(text, 100)
    assert len(out) <= 100 and truncate("corto", 100) == "corto"
    assert safe_filename("wikipedia-es", "Cyberpunk 2077: Phantom Liberty") == "wikipedia-es__Cyberpunk_2077_Phantom_Liberty.txt"
    assert safe_filename("fandom", "V") == "fandom__V.txt"
    doc = build_document_text("V", "Cyberpunk Wiki (Fandom)", "https://x/V", "cuerpo")
    assert doc.startswith("V\nFuente: Cyberpunk Wiki (Fandom) (https://x/V). Licencia: CC BY-SA") and doc.endswith("cuerpo")
