# Next 샌디스크 연결 L4 — JAY 어닝콜 원문에서 공급 제약 발언 키워드 추출(2026-10-05).
# 입력: ~/mnt/chatgpt_종목분석결과/JAY_Earnings_Archive_2026-09-25/03_원문, 출력: ~/jay_constraints_raw.tsv(저장소 밖). 결과 정리는 jay-earnings-constraint-map-2026-10-05.md.
import os, re, sys, collections
ROOT = os.path.expanduser('~/mnt/chatgpt_종목분석결과/JAY_Earnings_Archive_2026-09-25/03_원문')
CATS = [
 ('공급제약', re.compile(r"supply[- ]constrain\w*|capacity[- ]constrain\w*|constrained (?:by|on|in) (?:supply|capacity)|tight(?:er|ness)? (?:in )?supply|supply (?:is |remains |was )?(?:very )?tight|shortage\w*|short supply|demand (?:continues to )?(?:exceed\w*|outstrip\w*|outpac\w*) (?:our )?supply|supply[- ]demand (?:gap|imbalance)", re.I)),
 ('할당', re.compile(r"\bon allocation\b|\ballocation\b", re.I)),
 ('리드타임', re.compile(r"lead[- ]?times?", re.I)),
 ('가격인상', re.compile(r"price increases?|pricing actions?|price hikes?|raised? (?:our )?prices?|increas\w+ (?:our )?prices?|higher pricing", re.I)),
 ('매진', re.compile(r"sold[- ]out|fully booked|booked out|fully (?:sold|allocated)", re.I)),
]
NEG = re.compile(r"capital allocation|allocation of capital|allocat\w+ capital|asset allocation|purchase price allocation|resource allocation|allocation of (?:resources|investment)", re.I)
COMP = re.compile(r"CoWoS|HBM|DRAM|NAND|HDD|SSD|memory|wafer|substrate|ABF|laser|optic|transceiver|InP|power|transformer|turbine|switchgear|GPU|CPU|accelerator|packag|capacity|fab|EUV|lithograph|copper|cable|fiber|chip|silicon|component|data ?cent", re.I)
rows = []; per = collections.Counter()
for dp, dn, fn in os.walk(ROOT):
    for f in sorted(fn):
        if not f.lower().endswith(('.md', '.txt')): continue
        p = os.path.join(dp, f)
        try: t = open(p, encoding='utf-8', errors='ignore').read()
        except Exception: continue
        comp = f.split('_')[0]; period = os.path.splitext(f)[0][len(comp)+1:]
        sents = re.split(r'(?<=[.!?])\s+|\n+', t)
        seen = set(); hits = []
        for s in sents:
            s2 = ' '.join(s.split())
            if len(s2) < 25 or NEG.search(s2): continue
            for cat, rx in CATS:
                m = rx.search(s2)
                if m:
                    if cat == '할당' and not COMP.search(s2): break
                    key = s2[:80]
                    if key in seen: break
                    seen.add(key)
                    a = max(0, m.start()-150); b = min(len(s2), m.end()+150)
                    snip = ('…' if a > 0 else '') + s2[a:b] + ('…' if b < len(s2) else '')
                    hits.append((0 if COMP.search(s2) else 1, cat, snip))
                    break
        hits.sort(key=lambda x: x[0])
        for h in hits[:6]:
            rows.append((comp, period, h[1], h[2])); per[comp] += 1
print('FILES_WITH_HITS', len(per), 'ROWS', len(rows))
cc = collections.Counter(r[2] for r in rows); print('BY_CAT', dict(cc))
out = os.path.expanduser('~/jay_constraints_raw.tsv')
with open(out, 'w', encoding='utf-8') as w:
    for r in rows: w.write('\t'.join(r) + '\n')
print('WROTE', out)
