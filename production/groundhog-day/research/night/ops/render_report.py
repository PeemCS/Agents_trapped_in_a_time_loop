"""Render a portable reading copy of the morning report, with its recorded film embedded."""
import html
from pathlib import Path
import re
from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[3]


def main():
    source = (ROOT/"MORNING-REPORT.md").read_text()
    source = re.sub(r"^<!-- (?:end-)?provider-meter -->\n?", "", source, flags=re.MULTILINE)
    title, date, intro, rest = source.split("\n\n",3)
    renderer = MarkdownIt("commonmark",{"html":False}).enable("table")
    tokens = renderer.parse(rest)
    sections = []
    for i,token in enumerate(tokens):
        if token.type == "heading_open" and token.tag == "h2":
            label = tokens[i+1].content
            identifier = re.sub(r"[^a-z0-9]+","-",label.lower()).strip("-")
            token.attrSet("id",identifier)
            sections.append((identifier,label))
    body = renderer.renderer.render(tokens,renderer.options,{})
    body = body.replace("<table>",'<div class="table-wrap" tabindex="0"><table>').replace("</table>","</table></div>")
    links = "".join(f'<a href="#{key}">{html.escape(label)}</a>' for key,label in sections)
    intro_html = renderer.render(intro)
    css = """
    *{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f7f4eb;color:#25332e;font:17px/1.65 "DM Sans",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
    a{color:#185d52;text-underline-offset:.17em}a:focus-visible,summary:focus-visible,video:focus-visible{outline:3px solid #a34c26;outline-offset:3px}
    main{max-width:1190px;padding:22px 44px 70px;margin:auto}.top{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;font-size:.83rem;border-bottom:1px solid #aaa998;padding-bottom:11px}
    .hero{display:grid;grid-template-columns:1fr 1.13fr;gap:35px;align-items:center;margin:28px 0}
    h1,h2{font-family:Georgia,"Times New Roman",serif;font-weight:400}h1{font-size:clamp(3rem,7vw,6.4rem);letter-spacing:-.065em;line-height:.93;margin:0 0 18px}
    .hero p{font-size:1rem;margin:0}.hero video{display:block;width:100%;border:1px solid #314943;aspect-ratio:16/9;background:#18302d}.hero figure{margin:0}
    figcaption{font-size:.8rem;color:#48554e;margin-top:6px}details{border-block:1px solid #abae9e;padding:9px 0;margin:20px 0}summary{cursor:pointer;font-weight:650}
    nav{display:grid;grid-template-columns:1fr 1fr;gap:5px 24px;padding:12px 0}article{max-width:880px;margin:0 auto}article p{margin:.9em 0}h2{font-size:clamp(1.85rem,4vw,2.65rem);line-height:1.1;letter-spacing:-.035em;margin:1.35em 0 .45em;scroll-margin-top:14px}
    .table-wrap{overflow-x:auto;margin:20px 0}table{border-collapse:collapse;font-size:.91rem;width:100%}th,td{padding:10px 12px;vertical-align:top;text-align:left;border-top:1px solid #c1c3b5}th{background:#e2e7db}
    article img{max-width:100%;height:auto;display:block}code{font: .9em ui-monospace,monospace;overflow-wrap:anywhere}
    @media(max-width:760px){main{padding:14px 19px 42px}.hero{grid-template-columns:1fr;gap:18px;margin:22px 0}.hero video{max-height:60vh}nav{grid-template-columns:1fr}body{font-size:16px}.table-wrap table{min-width:530px}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
    """
    title = html.escape(title.removeprefix("# "))
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} · Morning report</title><style>{css}</style></head><body><main>
    <div class="top"><span>{html.escape(date)}</span><a href="MORNING-REPORT.md">Markdown copy</a></div>
    <header class="hero"><div><h1>{title}</h1>{intro_html}</div><figure><video controls playsinline preload="metadata" poster="research/night/screening/rialto-cut.jpg" src="research/night/editor/rialto-cut/film.mp4" aria-label="Eight Bars, an eighty-second recorded performance"></video>
    <figcaption><strong>Eight Bars</strong> · 80 seconds · Three independent actors · <a href="research/night/screening/index.html#rialto-cut">Open the shot ledger</a></figcaption></figure></header>
    <details><summary>Jump to a finding</summary><nav aria-label="Sections">{links}</nav></details><article>{body}</article></main></body></html>"""
    (ROOT/"MORNING-REPORT.html").write_text(page+"\n")


if __name__ == "__main__":
    main()
