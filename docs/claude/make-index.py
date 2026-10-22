"""Read-only index builder for docs/claude and workspace/outputs (cs-1022b 5a, 2026-10-22).

Writes two files only: docs/claude/INDEX-auto.md and docs/claude/INDEX-outputs-auto.md.
Deterministic: content depends only on file names, headers and modification dates.
Usage: python3 docs/claude/make-index.py   (run from anywhere; repo root = two levels up)
"""
import datetime as dt
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
DOCS = HERE
OUTS = os.path.join(REPO, 'workspace', 'outputs')
PROMPTS = os.path.join(DOCS, 'scheduled-prompts')
SKIP = {'INDEX-auto.md', 'INDEX-outputs-auto.md'}
DATE_IN_NAME = re.compile(r'(\d{4}-\d{2}-\d{2})')


def read_head(path, n=4000):
    try:
        with open(path, 'rb') as f:
            raw = f.read(n)
    except OSError:
        return ''
    return raw.decode('utf-8-sig', errors='replace').replace('\r\n', '\n')


def front(text):
    if not text.startswith('---\n'):
        return {}
    end = text.find('\n---', 4)
    if end < 0:
        return {}
    out = {}
    for line in text[4:end].split('\n'):
        m = re.match(r'^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$', line)
        if m and m.group(1) not in out:
            out[m.group(1)] = m.group(2).strip()
    return out


def first_heading(text):
    for line in text.split('\n'):
        if line.startswith('# '):
            return line[2:].strip()
    return ''


def cell(s, n=110):
    s = re.sub(r'\s+', ' ', str(s or '')).replace('|', '/').strip()
    return s if len(s) <= n else s[:n - 1] + '…'


def mday(path):
    try:
        return dt.datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d')
    except OSError:
        return '?'


def docs_index():
    rows, others, subdirs = [], [], []
    for name in sorted(os.listdir(DOCS)):
        p = os.path.join(DOCS, name)
        if os.path.isdir(p):
            if not name.startswith('.'):
                cnt = sum(len(fs) for _, _, fs in os.walk(p))
                subdirs.append((name, cnt))
            continue
        if name in SKIP:
            continue
        if name.lower().endswith('.md'):
            t = read_head(p)
            fm = front(t)
            dm = DATE_IN_NAME.search(name)
            date = fm.get('date') or fm.get('as_of') or (dm.group(1) if dm else '')
            what = fm.get('summary') or fm.get('title') or first_heading(t)
            note = '' if fm else '머리말 없음'
            rows.append((name, cell(date, 16), cell(fm.get('id'), 28), cell(fm.get('status'), 14), cell(what), note))
        else:
            others.append((name, mday(p)))
    L = ['---', 'id: index-auto-docs', 'type: index', 'status: generated',
         'summary: docs/claude 자동 목록(make-index.py가 만듦 — 손으로 고치지 않음)', '---', '',
         '# docs/claude 자동 목록', '',
         f'- 문서(md) {len(rows)}개 · 머리말 없음 {sum(1 for r in rows if r[5])}개 · 기타 파일 {len(others)}개 · 하위 폴더 {len(subdirs)}개',
         '- 찾는 법: 이 파일에서 키워드 검색 → 파일 열기. 상태(status)가 비어 있으면 머리말에 없다는 뜻(현행 여부 확인 필요).', '',
         '## 문서', '', '| 파일 | 날짜 | id | 상태 | 요약·제목 | 비고 |', '|---|---|---|---|---|---|']
    L += [f'| {a} | {b} | {c} | {d} | {e} | {f} |' for a, b, c, d, e, f in rows]
    L += ['', '## 하위 폴더', '', '| 폴더 | 파일 수 |', '|---|---|']
    L += [f'| {a}/ | {b} |' for a, b in subdirs]
    L += ['', '## 기타 파일', '', '| 파일 | 수정일 |', '|---|---|']
    L += [f'| {a} | {b} |' for a, b in others]
    return '\n'.join(L) + '\n'


def prompt_texts():
    texts = {}
    if not os.path.isdir(PROMPTS):
        return texts
    for root, _, files in os.walk(PROMPTS):
        for f in files:
            if f.endswith(('.txt', '.py', '.md')):
                p = os.path.join(root, f)
                rel = os.path.relpath(p, PROMPTS).replace('\\', '/')
                if rel.startswith('pending-'):
                    continue
                try:
                    with open(p, 'rb') as fh:
                        texts[rel] = fh.read().decode('utf-8-sig', errors='replace')
                except OSError:
                    pass
    return texts


def outputs_index():
    texts = prompt_texts()
    rows = []
    if os.path.isdir(OUTS):
        for name in sorted(os.listdir(OUTS)):
            p = os.path.join(OUTS, name)
            if not os.path.isdir(p):
                continue
            n, last = 0, 0.0
            for root, _, fs in os.walk(p):
                for f in fs:
                    n += 1
                    try:
                        last = max(last, os.path.getmtime(os.path.join(root, f)))
                    except OSError:
                        pass
            lastd = dt.datetime.fromtimestamp(last).strftime('%Y-%m-%d') if last else '-'
            readme = 'O' if any(os.path.isfile(os.path.join(p, r)) for r in ('README.md', 'readme.md')) else '-'
            pat = re.compile(r'outputs[/\\]+' + re.escape(name) + r'(?![A-Za-z0-9_-])')
            who = sorted(k for k, v in texts.items() if pat.search(v))
            rows.append((name, n, lastd, readme, cell(', '.join(who), 90) or '-'))
    L = ['---', 'id: index-auto-outputs', 'type: index', 'status: generated',
         'summary: workspace/outputs 하위 폴더 자동 목록(make-index.py가 만듦 — 손으로 고치지 않음)', '---', '',
         '# workspace/outputs 자동 목록', '',
         f'- 폴더 {len(rows)}개 · README 있음 {sum(1 for r in rows if r[3] == "O")}개 · 예약 작업 지시문에 나오는 폴더 {sum(1 for r in rows if r[4] != "-")}개',
         '- "쓰는 예약 작업"은 scheduled-prompts의 지시문·스크립트에 그 폴더 경로가 나오는지만 본 것(실제로 쓰는지는 확인 필요). "-"면 지시문에 없음 = 수동·과거 작업 결과일 가능성.', '',
         '| 폴더 | 파일 수 | 마지막 수정 | README | 지시문에 나오는 곳 |', '|---|---|---|---|---|']
    L += [f'| {a}/ | {b} | {c} | {d} | {e} |' for a, b, c, d, e in rows]
    return '\n'.join(L) + '\n'


def write(path, text):
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)


if __name__ == '__main__':
    a, b = docs_index(), outputs_index()
    write(os.path.join(DOCS, 'INDEX-auto.md'), a)
    write(os.path.join(DOCS, 'INDEX-outputs-auto.md'), b)
    print('INDEX OK docs_lines', a.count('\n'), 'outputs_lines', b.count('\n'))
    sys.exit(0)
