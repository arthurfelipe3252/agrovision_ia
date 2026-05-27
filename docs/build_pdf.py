"""Converte docs/relatorio_atividade.md em PDF estilizado.

Pipeline:
    Markdown  -->  HTML (com syntax highlighting via Pygments)
              -->  HTML embrulhado em template com CSS profissional
              -->  PDF via Chrome headless

Uso:
    python docs/build_pdf.py
"""

import shutil
import subprocess
import sys
from pathlib import Path

import markdown


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "relatorio_atividade.md"
BUILD_DIR = ROOT / "_build"
HTML_PATH = BUILD_DIR / "relatorio_atividade.html"
PDF_PATH = ROOT / "relatorio_atividade.pdf"


def find_chrome() -> str:
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]
    for path in candidates:
        if Path(path).exists():
            return path
    found = shutil.which("chrome") or shutil.which("msedge")
    if found:
        return found
    raise SystemExit("Chrome ou Edge nao encontrado. Instale um deles ou ajuste find_chrome().")


CSS = """
@page {
    size: A4;
    margin: 22mm 22mm 24mm 22mm;
    @bottom-right {
        content: counter(page);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-size: 9pt;
        color: #6a737d;
    }
}

@page cover {
    margin: 22mm;
    @bottom-right { content: normal; }
}

* { box-sizing: border-box; }

html, body { margin: 0; padding: 0; }

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    color: #1f2328;
    font-size: 11pt;
    line-height: 1.65;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
}

/* ===== Capa ===== */
section.cover {
    page: cover;
    page-break-after: always;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
    min-height: 92vh;
    padding: 0 8mm;
}

section.cover h1 {
    font-size: 30pt;
    color: #0d2e4d;
    font-weight: 800;
    line-height: 1.2;
    margin: 0 0 28pt;
    border: none;
    padding: 0;
    letter-spacing: -0.5pt;
}

section.cover h1::after {
    content: "";
    display: block;
    width: 90pt;
    height: 3pt;
    background: #1e7e34;
    margin: 18pt auto 0;
    border-radius: 2pt;
}

section.cover blockquote {
    border: none;
    background: none;
    margin: 0 auto;
    padding: 0;
    max-width: 480pt;
    font-size: 12pt;
    line-height: 2;
    color: #344054;
    font-style: normal;
    text-align: center;
}

section.cover blockquote p {
    margin: 0 0 4pt;
}

section.cover hr { display: none; }

/* ===== Conteudo principal ===== */
section.content { counter-reset: page 1; }

h1, h2, h3, h4 {
    color: #0d2e4d;
    font-weight: 700;
    line-height: 1.3;
}

/* h2 = secoes principais (Sumario, Introducao, Parte 1...). Cada uma comeca em nova pagina. */
h2 {
    font-size: 19pt;
    margin: 0 0 14pt;
    padding-bottom: 8pt;
    border-bottom: 2pt solid #0d2e4d;
    page-break-before: always;
}

/* O primeiro h2 (Sumario) nao precisa de page-break antes — a capa ja fez isso. */
section.content > h2:first-child {
    page-break-before: avoid;
}

h3 {
    font-size: 14pt;
    margin: 22pt 0 8pt;
    color: #14532d;
}

h4 {
    font-size: 12pt;
    margin: 16pt 0 6pt;
    color: #1a3a5c;
}

p {
    margin: 0 0 10pt;
    text-align: justify;
    hyphens: auto;
}

a { color: #0969da; text-decoration: none; }

ul, ol {
    margin: 0 0 12pt;
    padding-left: 22pt;
}

li {
    margin-bottom: 4pt;
    line-height: 1.6;
}

strong { color: #0d2e4d; font-weight: 700; }

em { color: #1f2328; }

/* ===== Blockquote ===== */
blockquote {
    border-left: 3pt solid #1e7e34;
    background: #f1f8f4;
    margin: 14pt 0;
    padding: 10pt 14pt;
    color: #25433a;
    border-radius: 0 4pt 4pt 0;
    page-break-inside: avoid;
}

blockquote p {
    margin: 0 0 6pt;
    text-align: left;
}

blockquote p:last-child { margin-bottom: 0; }

/* ===== Tabelas ===== */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 14pt 0;
    font-size: 10pt;
    page-break-inside: avoid;
}

th, td {
    border: 0.5pt solid #d0d7de;
    padding: 7pt 9pt;
    text-align: left;
    vertical-align: top;
    line-height: 1.4;
}

th {
    background: #eef3f8;
    color: #0d2e4d;
    font-weight: 700;
    border-bottom: 1.5pt solid #0d2e4d;
}

tr:nth-child(even) td { background: #fbfcfd; }

/* ===== Codigo ===== */
code {
    font-family: "Cascadia Code", "Fira Code", "JetBrains Mono", Consolas, "Courier New", monospace;
    background: #f3f4f6;
    color: #be185d;
    padding: 1pt 5pt;
    border-radius: 3pt;
    font-size: 9.5pt;
}

pre {
    background: #f6f8fa;
    border: 1pt solid #d0d7de;
    border-left: 3pt solid #0d2e4d;
    padding: 10pt 12pt;
    border-radius: 4pt;
    overflow-x: hidden;
    margin: 12pt 0;
    page-break-inside: avoid;
    white-space: pre-wrap;
    word-wrap: break-word;
}

pre code {
    background: transparent;
    color: #1f2328;
    padding: 0;
    font-size: 8.8pt;
    line-height: 1.55;
}

/* Pygments codehilite */
.codehilite { background: transparent; }
.codehilite pre { background: #f6f8fa; }
.codehilite .k, .codehilite .kn, .codehilite .kc, .codehilite .kr, .codehilite .kt { color: #cf222e; font-weight: 600; }
.codehilite .s, .codehilite .s1, .codehilite .s2, .codehilite .sa, .codehilite .sb, .codehilite .sc, .codehilite .sd, .codehilite .se, .codehilite .si, .codehilite .sh, .codehilite .sx, .codehilite .sr, .codehilite .ss { color: #0a3069; }
.codehilite .c, .codehilite .c1, .codehilite .cm, .codehilite .cp, .codehilite .cs { color: #6e7781; font-style: italic; }
.codehilite .n { color: #1f2328; }
.codehilite .nb, .codehilite .bp { color: #0550ae; }
.codehilite .nf { color: #6639ba; }
.codehilite .nc, .codehilite .ne { color: #953800; font-weight: 600; }
.codehilite .nd { color: #6639ba; }
.codehilite .o, .codehilite .ow { color: #cf222e; }
.codehilite .mi, .codehilite .mf, .codehilite .mh, .codehilite .mo { color: #0550ae; }
.codehilite .nn { color: #6639ba; }
.codehilite .nt { color: #116329; }

/* ===== Detalhes ===== */
hr {
    border: none;
    border-top: 0.5pt solid #d0d7de;
    margin: 18pt 0;
}

/* Evita orfaos/viuvas em paragrafos */
p, li, blockquote { orphans: 3; widows: 3; }

/* Forca tabela e codigo a quebrarem antes de cortar feio */
table, pre, blockquote { page-break-inside: avoid; }

/* Sumario: linkado, mas sem azul gritante */
section.content > h2:first-child + ol a,
section.content > h2:first-child + ul a {
    color: #1f2328;
    font-weight: 500;
}
"""


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
<section class="cover">
{cover_html}
</section>
<section class="content">
{content_html}
</section>
</body>
</html>
"""


def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"Markdown nao encontrado: {SRC}")

    BUILD_DIR.mkdir(exist_ok=True)
    raw = SRC.read_text(encoding="utf-8")

    parts = raw.split("\n---\n", 1)
    if len(parts) != 2:
        raise SystemExit("Separador '---' esperado entre capa e conteudo nao encontrado.")
    cover_md, content_md = parts

    md = markdown.Markdown(
        extensions=["tables", "fenced_code", "codehilite", "toc"],
        extension_configs={
            "codehilite": {"guess_lang": False, "noclasses": False, "linenums": False},
            "toc": {"toc_depth": "2-3"},
        },
    )
    cover_html = md.convert(cover_md)
    md.reset()
    content_html = md.convert(content_md)

    html = HTML_TEMPLATE.format(
        title="Relatorio - AgroVision AI",
        css=CSS,
        cover_html=cover_html,
        content_html=content_html,
    )
    HTML_PATH.write_text(html, encoding="utf-8")
    print(f"[ok] HTML em {HTML_PATH}")

    chrome = find_chrome()
    print(f"[ok] usando {chrome}")
    print("[..] renderizando PDF via Chrome headless...")

    cmd = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--no-pdf-header-footer",
        f"--print-to-pdf={PDF_PATH}",
        HTML_PATH.as_uri(),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0 or not PDF_PATH.exists():
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr, file=sys.stderr)
        raise SystemExit("Falha ao gerar PDF")

    size_kb = PDF_PATH.stat().st_size / 1024
    print(f"[ok] PDF gerado: {PDF_PATH}  ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
