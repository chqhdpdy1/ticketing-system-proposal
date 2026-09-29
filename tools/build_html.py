#!/usr/bin/env python3
"""
외부 의존성 없이(표준 라이브러리만) 여러 Markdown 문서를 하나의
인쇄 최적화 HTML 문서로 합칩니다. 브라우저에서 열고 Ctrl+P -> PDF로 저장하면
한글이 완벽한 제출용 PDF가 생성됩니다.

지원 문법: 헤딩(#~######), 표(GFM), 코드블록(```), 인용구(>), 순서/비순서 리스트,
굵게(**), 기울임(*), 인라인 코드(`), 링크([text](url)), 수평선(---).
"""
import html
import re
import sys
from pathlib import Path

# ----- 인라인 변환 -----
def inline(text: str) -> str:
    # 코드 조각을 먼저 자리표시자로 빼서 escape 충돌 방지
    codes = []
    def stash_code(m):
        codes.append(m.group(1))
        return f"\x00CODE{len(codes)-1}\x00"
    text = re.sub(r"`([^`]+)`", stash_code, text)

    text = html.escape(text, quote=False)

    # 링크 [text](url)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
                  lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', text)
    # 굵게 **...**
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    # 기울임 *...*  (단, ** 는 위에서 처리됨)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", text)

    # 코드 복원
    def restore_code(m):
        idx = int(m.group(1))
        return f"<code>{html.escape(codes[idx], quote=False)}</code>"
    text = re.sub(r"\x00CODE(\d+)\x00", restore_code, text)
    return text


def render_table(rows):
    # rows: list of raw '| a | b |' lines (헤더, 구분선, 본문...)
    def cells(line):
        line = line.strip()
        if line.startswith("|"):
            line = line[1:]
        if line.endswith("|"):
            line = line[:-1]
        return [c.strip() for c in line.split("|")]

    header = cells(rows[0])
    body = [cells(r) for r in rows[2:]]  # rows[1] 은 구분선
    out = ['<table>', '<thead><tr>']
    for h in header:
        out.append(f"<th>{inline(h)}</th>")
    out.append('</tr></thead><tbody>')
    for r in body:
        out.append('<tr>')
        for c in r:
            out.append(f"<td>{inline(c)}</td>")
        # 열 개수 보정
        for _ in range(len(header) - len(r)):
            out.append("<td></td>")
        out.append('</tr>')
    out.append('</tbody></table>')
    return "\n".join(out)


def md_to_html(md: str) -> str:
    lines = md.split("\n")
    out = []
    i = 0
    n = len(lines)

    # 리스트 스택: [(type, indent)]
    list_stack = []

    def close_lists(to_depth=0):
        while len(list_stack) > to_depth:
            t, _ = list_stack.pop()
            out.append("</ul>" if t == "ul" else "</ol>")

    while i < n:
        line = lines[i]

        # 코드블록
        m = re.match(r"^```(\w*)\s*$", line)
        if m:
            close_lists()
            lang = m.group(1)
            i += 1
            buf = []
            while i < n and not re.match(r"^```\s*$", lines[i]):
                buf.append(lines[i])
                i += 1
            i += 1  # closing ```
            code = html.escape("\n".join(buf), quote=False)
            cls = f' class="lang-{lang}"' if lang else ""
            out.append(f'<pre><code{cls}>{code}</code></pre>')
            continue

        # 표 (헤더 + |---| 구분선 패턴)
        if line.strip().startswith("|") and i + 1 < n and re.match(r"^\s*\|?[\s:\-|]+\|?\s*$", lines[i+1]) and "-" in lines[i+1]:
            close_lists()
            tbl = [line, lines[i+1]]
            i += 2
            while i < n and lines[i].strip().startswith("|"):
                tbl.append(lines[i])
                i += 1
            out.append(render_table(tbl))
            continue

        # 수평선
        if re.match(r"^\s*---+\s*$", line):
            close_lists()
            out.append("<hr/>")
            i += 1
            continue

        # 헤딩
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            close_lists()
            level = len(m.group(1))
            out.append(f"<h{level}>{inline(m.group(2).strip())}</h{level}>")
            i += 1
            continue

        # 인용구 (연속 라인 묶기)
        if line.strip().startswith(">"):
            close_lists()
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            inner = md_to_html("\n".join(buf))
            out.append(f"<blockquote>{inner}</blockquote>")
            continue

        # 리스트
        m = re.match(r"^(\s*)([-*+]|\d+\.)\s+(.*)$", line)
        if m:
            indent = len(m.group(1))
            depth = indent // 2 + 1
            ordered = bool(re.match(r"\d+\.", m.group(2)))
            ltype = "ol" if ordered else "ul"
            # 깊이 조정
            while len(list_stack) > depth:
                t, _ = list_stack.pop()
                out.append("</ul>" if t == "ul" else "</ol>")
            if len(list_stack) < depth:
                out.append("<ol>" if ordered else "<ul>")
                list_stack.append((ltype, indent))
            else:
                # 같은 깊이인데 타입이 다르면 교체
                if list_stack and list_stack[-1][0] != ltype:
                    t, _ = list_stack.pop()
                    out.append("</ul>" if t == "ul" else "</ol>")
                    out.append("<ol>" if ordered else "<ul>")
                    list_stack.append((ltype, indent))
            out.append(f"<li>{inline(m.group(3).strip())}</li>")
            i += 1
            continue

        # 빈 줄
        if line.strip() == "":
            close_lists()
            i += 1
            continue

        # 일반 문단 (연속 라인 합치기)
        close_lists()
        buf = [line]
        i += 1
        while i < n and lines[i].strip() != "" and not re.match(r"^(#{1,6}\s|```|>|\s*[-*+]\s|\s*\d+\.\s)", lines[i]) and not lines[i].strip().startswith("|") and not re.match(r"^\s*---+\s*$", lines[i]):
            buf.append(lines[i])
            i += 1
        out.append(f"<p>{inline(' '.join(s.strip() for s in buf))}</p>")

    close_lists()
    return "\n".join(out)


CSS = """
@page { size: A4; margin: 18mm 16mm; }
* { box-sizing: border-box; }
body {
  font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', 'Noto Sans KR', 'Nanum Gothic', sans-serif;
  color: #1a1a1a; line-height: 1.65; font-size: 10.5pt; margin: 0 auto; max-width: 820px;
  padding: 24px;
}
h1 { font-size: 20pt; color: #1b3a5c; border-bottom: 3px solid #1b3a5c; padding-bottom: 8px; margin-top: 8px; }
h2 { font-size: 15pt; color: #1b3a5c; border-bottom: 1px solid #c8d4e0; padding-bottom: 5px; margin-top: 26px; }
h3 { font-size: 12.5pt; color: #24557f; margin-top: 18px; }
h4 { font-size: 11pt; color: #365e82; margin-top: 14px; }
p { margin: 8px 0; }
a { color: #1857a8; text-decoration: none; word-break: break-all; }
strong { color: #12314f; }
hr { border: none; border-top: 1px solid #d8dee6; margin: 18px 0; }
ul, ol { margin: 6px 0 10px 0; padding-left: 26px; }
li { margin: 3px 0; }
blockquote {
  margin: 10px 0; padding: 8px 16px; background: #f2f6fb;
  border-left: 4px solid #4a7fb5; color: #33475b; border-radius: 3px;
}
blockquote p { margin: 4px 0; }
code {
  font-family: 'D2Coding','Consolas','Courier New',monospace; font-size: 9.5pt;
  background: #eef1f5; padding: 1px 5px; border-radius: 3px; color: #b5285a;
}
pre {
  background: #1e2733; color: #e6edf3; padding: 12px 14px; border-radius: 6px;
  overflow-x: auto; font-size: 8.8pt; line-height: 1.5; margin: 10px 0;
  white-space: pre; page-break-inside: avoid;
}
pre code { background: none; color: inherit; padding: 0; font-size: 8.8pt; }
table {
  border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 9.3pt;
  page-break-inside: avoid;
}
th, td { border: 1px solid #c3ccd6; padding: 6px 9px; text-align: left; vertical-align: top; }
th { background: #1b3a5c; color: #fff; font-weight: 600; }
tr:nth-child(even) td { background: #f6f8fb; }
.cover {
  text-align: center; padding: 60px 0 40px 0; page-break-after: always;
}
.cover .badge { color: #4a7fb5; font-size: 12pt; letter-spacing: 2px; }
.cover h1 { border: none; font-size: 30pt; margin: 24px 0 8px; }
.cover .sub { font-size: 14pt; color: #33475b; margin-bottom: 40px; }
.cover .meta { display: inline-block; text-align: left; font-size: 12pt; line-height: 2.0;
  background: #f2f6fb; padding: 20px 40px; border-radius: 8px; border: 1px solid #d3ddea; }
.cover .meta b { color: #1b3a5c; display: inline-block; width: 90px; }
.toc { page-break-after: always; }
.toc h2 { border: none; }
.toc ol { font-size: 11pt; line-height: 2.0; }
.doc-section { page-break-before: always; }
.print-hint {
  background: #fff8e1; border: 1px solid #ffe08a; color: #6b5300;
  padding: 12px 16px; border-radius: 6px; margin-bottom: 20px; font-size: 10pt;
}
@media print { .print-hint { display: none; } body { padding: 0; } }
"""


def main():
    root = Path("/projects/sandbox/docs")
    parts = [
        ("01-project-proposal.md", "제안서 (Project Proposal)"),
        ("02-architecture.md", "부록 A. 시스템 아키텍처 설계"),
        ("03-domain-model.md", "부록 B. 도메인 모델 및 데이터 설계"),
        ("04-tech-stack.md", "부록 C. 기술 스택 및 참조 시스템 조사"),
    ]

    sections_html = []
    toc_items = []
    for idx, (fname, title) in enumerate(parts):
        md = (root / fname).read_text(encoding="utf-8")
        body = md_to_html(md)
        anchor = f"sec{idx}"
        toc_items.append(f'<li><a href="#{anchor}">{html.escape(title)}</a></li>')
        cls = "doc-section" if idx > 0 else ""
        sections_html.append(f'<section id="{anchor}" class="{cls}">{body}</section>')

    cover = """
    <div class="cover">
      <div class="badge">KOOKMIN UNIVERSITY · SOFTWARE ARCHITECTURE</div>
      <h1>Ticketing System</h1>
      <div class="sub">범용 선착순(First-Come-First-Served) 판매 플랫폼<br/>
      &mdash; 첫 번째 도메인: 영화관 티켓 예매 &mdash;</div>
      <div class="meta">
        <div><b>과제</b> HW1. Project Proposal</div>
        <div><b>팀 명</b> Ticketing System (1인 팀)</div>
        <div><b>이름</b> 홍석준</div>
        <div><b>학번</b> 20213098</div>
        <div><b>소속</b> 소프트웨어학과 4학년</div>
      </div>
    </div>
    """

    toc = "<div class='toc'><h2>목차</h2><ol>" + "".join(toc_items) + "</ol></div>"

    hint = ('<div class="print-hint">💡 이 파일을 브라우저에서 연 뒤 '
            '<b>Ctrl+P</b> (Mac: <b>Cmd+P</b>) → 대상 "<b>PDF로 저장</b>"을 선택하면 '
            '제출용 PDF가 생성됩니다. (여백 기본, 배경 그래픽 켜기 권장)</div>')

    doc = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Ticketing System - Project Proposal</title>
<style>{CSS}</style>
</head>
<body>
{hint}
{cover}
{toc}
{''.join(sections_html)}
</body>
</html>"""

    out_path = Path("/projects/sandbox/Ticketing-System-Proposal.html")
    out_path.write_text(doc, encoding="utf-8")
    print(f"OK -> {out_path} ({len(doc)} bytes)")


if __name__ == "__main__":
    main()
