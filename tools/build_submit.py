#!/usr/bin/env python3
"""
간결한 제출용 제안서(docs/proposal-submit.md) 하나를 인쇄 최적화 HTML로 변환.
표지/목차 없이 문서 자체만 담아 PDF 제출에 바로 쓰도록 만든다.
build_html.py 의 Markdown 변환기와 CSS를 재사용한다.
"""
from pathlib import Path
import importlib.util

# build_html.py 모듈 로드 (md_to_html, CSS 재사용)
spec = importlib.util.spec_from_file_location(
    "build_html", str(Path(__file__).parent / "build_html.py"))
bh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bh)


def main():
    src = Path("/projects/sandbox/docs/proposal-submit.md")
    md = src.read_text(encoding="utf-8")
    body = bh.md_to_html(md)

    hint = ('<div class="print-hint">💡 브라우저에서 <b>Ctrl+P</b> (Mac: <b>Cmd+P</b>) → '
            '"<b>PDF로 저장</b>"을 선택하면 제출용 PDF가 생성됩니다.</div>')

    doc = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Ticketing System - Project Proposal</title>
<style>{bh.CSS}</style>
</head>
<body>
{hint}
<section>{body}</section>
</body>
</html>"""

    out = Path("/projects/sandbox/Ticketing-System-Proposal.html")
    out.write_text(doc, encoding="utf-8")
    print(f"OK -> {out} ({len(doc)} bytes)")


if __name__ == "__main__":
    main()
