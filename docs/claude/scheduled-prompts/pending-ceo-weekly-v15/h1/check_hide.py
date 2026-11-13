import re,json
B='/sessions/rcw-01kumgkivae5ucwboovezgjf/work/t/'
def blocks(path,w):
    t=open(path,encoding='utf-8').read();t=t[t.index('## 주간 경영보고 '+w):]
    out={};cur=None
    for l in t.split('\n'):
        m=re.match(r'^- 받음 \[[^\]]+\] (S-[A-Z]+-\w+) (.*)$',l)
        if m:cur=m.group(1);out[cur]={'head':m.group(2),'items':[]};continue
        if cur and l.startswith('  - '):out[cur]['items'].append(l[4:]);continue
        cur=None
    return out
bad=0
for m in ('real','chain'):
  for w in ['2026-10-19','2026-10-25','2026-11-01','2026-11-08']:
    a=blocks(f'{B}v141-{m}/{w}/report-after.md',w);b=blocks(f'{B}v15-{m}/{w}/report-after.md',w)
    # S-OPS-1: every non-'제때' item kept
    A1=[x for x in a['S-OPS-1']['items'] if not x.startswith('제때:')];B1=b['S-OPS-1']['items']
    A3=[x for x in a['S-OPS-3']['items'] if ('기록 없음' in x or '점검 상태 정상' not in x or '공시 수집 OK' not in x or '(낡음)' in x or '미수집' in x)];B3=b['S-OPS-3']['items']
    ok1=A1==B1;ok3=A3==B3
    # all other S blocks identical except S-OPS-4 and new S-OPS-8
    oth=[k for k in a if k not in('S-OPS-1','S-OPS-3','S-OPS-4') and (a[k]!=b.get(k))]
    print(m,w,'S-OPS-1 abnormal kept',ok1,len(A1),'| S-OPS-3 abnormal kept',ok3,len(A3),'of',len(a['S-OPS-3']['items']),'| 1 head:',b['S-OPS-1']['head'][:70],'| 3 head:',b['S-OPS-3']['head'][:90].split('|')[1] if '|' in b['S-OPS-3']['head'] else '', '| other blocks changed:',oth,'| new:',[k for k in b if k not in a])
    bad+=(not ok1)+(not ok3)+len(oth)
print('BAD',bad)
