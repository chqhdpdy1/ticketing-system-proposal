#!/usr/bin/env python3
"""
간결한 제출용 제안서(report/proposal-submit.md) 하나를 인쇄 최적화 HTML로 변환.
표지/목차 없이 문서 자체만 담되, 페이지가 깔끔하게 나뉘도록 <h2> 단위로 섹션을 묶는다.
build_html.py 의 Markdown 변환기와 CSS를 재사용한다.
"""
from pathlib import Path
import importlib.util
import re

# build_html.py 모듈 로드 (md_to_html, CSS 재사용)
spec = importlib.util.spec_from_file_location(
    "build_html", str(Path(__file__).parent / "build_html.py"))
bh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bh)

# 제출용 추가 CSS: 페이지 나눔·표 잘림 방지 보강
EXTRA_CSS = """
/* 표가 큰 섹션·참고문헌은 새 페이지에서 시작해 깔끔하게 나눈다 */
.page-break { page-break-before: always; }
h2, h3, h4 { page-break-after: avoid; }         /* 제목 바로 뒤에서 페이지가 끊기지 않게 */
table, tr, pre, blockquote { page-break-inside: avoid; }  /* 표가 페이지 경계에서 잘리지 않게 */
p, li { orphans: 2; widows: 2; }
section { page-break-inside: auto; }
@media print { .print-hint { display: none; } body { padding: 0; } }
"""


def split_into_sections(body_html: str) -> str:
    """변환된 HTML을 <h2> 기준으로 잘라 섹션으로 감싼다.
    표(<table>)가 포함된 큰 섹션과 참고문헌은 새 페이지에서 시작하도록 표시한다.
    (짧은 앞 섹션 1·2·3은 자연스럽게 이어져 여백 낭비를 줄인다.)"""
    parts = re.split(r'(?=<h2>)', body_html)
    parts = [p for p in parts if p.strip()]
    out = []
    for i, p in enumerate(parts):
        # 표가 있거나 '참고문헌' 섹션이면 새 페이지에서 시작.
        # 단, 맨 첫 섹션(i==0)에는 페이지 나눔을 넣지 않는다(첫 페이지 상단 여백 방지).
        is_big = ("<table>" in p) or ("참고문헌" in p)
        cls = "page-section page-break" if (is_big and i > 0) else "page-section"
        out.append(f'<section class="{cls}">{p}</section>')
    return "\n".join(out)


def main():
    src = Path("/projects/sandbox/report/proposal-submit.md")
    md = src.read_text(encoding="utf-8")
    body = bh.md_to_html(md)
    body = split_into_sections(body)

    hint = ('<div class="print-hint">💡 브라우저에서 <b>Ctrl+P</b> (Mac: <b>Cmd+P</b>) → '
            '"<b>PDF로 저장</b>"을 선택하면 제출용 PDF가 생성됩니다. '
            '(여백: 기본 / 배율: 기본 100% 권장)</div>')

    doc = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Ticketing System - Project Proposal</title>
<style>{bh.CSS}
{EXTRA_CSS}</style>
</head>
<body>
{hint}
{body}
</body>
</html>"""

    out = Path("/projects/sandbox/report/Ticketing-System-Proposal.html")
    out.write_text(doc, encoding="utf-8")
    print(f"OK -> {out} ({len(doc)} bytes)")


if __name__ == "__main__":
    main()
