import sys
src,dst=sys.argv[1:3]
s=open(src,encoding='utf-8',newline='').read()
def rep(old,new,cnt=1):
    global s
    n=s.count(old)
    assert n==cnt,(n,old[:80])
    s=s.replace(old,new)
# P1 secretary file picker + plan
rep("def PRE(ns,a,b):return sorted(n for n in (ns or []) if re.match(r'^\\d{4}-\\d{2}-\\d{2}-.+\\.md$',str(n)) and a.isoformat()<=n[:10]<=b.isoformat())\n",
    "def PRE(ns,a,b):return sorted(n for n in (ns or []) if re.match(r'^\\d{4}-\\d{2}-\\d{2}-.+\\.md$',str(n)) and a.isoformat()<=n[:10]<=b.isoformat())\n"
    "def SECW(ns,a,b):return sorted(n for n in (ns or []) if re.match(r'^\\d{4}-\\d{2}-\\d{2}\\.md$',str(n)) and a.isoformat()<=n[:10]<=b.isoformat())\n")
rep("    P+=['workspace/outputs/pre-open/'+n for n in PRE(I.get('preopen'),sun,sat)][:10]\n",
    "    P+=['workspace/outputs/pre-open/'+n for n in PRE(I.get('preopen'),sun,sat)][:10]\n    P+=['workspace/outputs/secretary/'+n for n in SECW(I.get('secretary'),sun,sat)][:7]\n")
# P3 board counts: R4/R5/R6 are not counted or shown (secretary sees them daily)
rep("    m=re.search(r'RESULT (\\d+)건',B);bn=int(m.group(1)) if m else None\n    if bn is not None and C.get('docs') is False:bn-=len(re.findall(r'^R2 ',B,re.M))\n",
    "    m=re.search(r'RESULT (\\d+)건',B);bn=int(m.group(1)) if m else None;bo=0\n"
    "    if bn is not None:\n"
    "        bo=len(re.findall(r'^R[456] ',B,re.M));bn-=bo\n"
    "        B=re.sub(r'(?m)^R[456] .*\\n?','',B).strip()\n"
    "        B=re.sub(r'RESULT (\\d+)건',lambda z:f'RESULT {int(z.group(1))-bo}건 (R1·R2 — R4·R5·R6 {bo}건은 주간 보고에서 뺌: 비서 제안이 매일 봄)',B,count=1)\n"
    "        if C.get('docs') is False:bn-=len(re.findall(r'^R2 ',B,re.M))\n")
# P4 partial-read note
rep("(['작업 일부만 읽음 — R2·R4·R5·R6 부분 점검'] if C.get('tasks') is False else [])","(['작업 일부만 읽음 — R2 부분 점검'] if C.get('tasks') is False else [])")
# P5 F-OPS-4 info only
rep("    if bn is None:fd('F-OPS-4','운영관리','관제판 점검 불완전')\n    else:\n        if bn>0:fd('F-OPS-4','운영관리',f'관제판 점검 발견 {bn}건(7절 원문)')\n",
    "    if bn is None:fd('F-OPS-4','운영관리','관제판 점검 불완전','🟠')\n    else:\n        if bn>0:fd('F-OPS-4','운영관리',f'관제판·예약 기록 장부 어긋남 {bn}건(R1·R2, 7절 원문 — 회사 상태 색에 안 들어감)','ℹ')\n")
# P10 S-OPS-1 collapse
rep("+(' (목록 끝까지 못 읽음 — 확인 필요)' if C.get('trig') is False else ''),late+fail+unk+(['제때: '+', '.join(okn)] if okn else []))",
    "+(' (목록 끝까지 못 읽음 — 확인 필요)' if C.get('trig') is False else (' — 이상 없음' if not(late or fail or unk) else '')),late+fail+unk)")
# P11 S-OPS-3 abnormal rows only
rep("CH=[];cbad=[];nfo=0;","CH=[];CHb=[];cbad=[];nfo=0;")
rep("        if not x:CH.append(f'{MDd(d)} 기록 없음');cbad.append(MDd(d)+' 기록 없음');continue\n",
    "        if not x:CH.append(f'{MDd(d)} 기록 없음');CHb.append(f'{MDd(d)} 기록 없음');cbad.append(MDd(d)+' 기록 없음');continue\n")
rep("        CH.append(f\"{MDd(d)} {str(x.get('runAt') or '')[11:16]} · 점검 상태 {v_ or '확인 필요'} · 공시 수집 {fl.get('status') or '확인 필요'}(새 {fl.get('newCount','?')}) · SAVE 메모 {mk.get('reportDate') or '없음'}{'(낡음)' if stl else ''} · saveticker {'수집' if sv else '미수집'}\")\n",
    "        l_=f\"{MDd(d)} {str(x.get('runAt') or '')[11:16]} · 점검 상태 {v_ or '확인 필요'} · 공시 수집 {fl.get('status') or '확인 필요'}(새 {fl.get('newCount','?')}) · SAVE 메모 {mk.get('reportDate') or '없음'}{'(낡음)' if stl else ''} · saveticker {'수집' if sv else '미수집'}\";CH.append(l_)\n"
    "        if tn!='ok' or fl.get('status')!='OK' or stl or not sv:CHb.append(l_)\n")
rep("saveticker 수집 {nsv}/{len(RN)}일\") if rok else '통합점검 기록(대시보드 runs)을 읽지 못함 — 확인 필요',CH if rok else [])",
    "saveticker 수집 {nsv}/{len(RN)}일\"+('' if CHb else ' — 이상 없음')) if rok else '통합점검 기록(대시보드 runs)을 읽지 못함 — 확인 필요',CHb if rok else [])")
# P7 S-OPS-4 one line
old4=s[s.index("    ib('S-OPS-4'"):s.index("    ib('S-OPS-5'")]
new4=("    ib('S-OPS-4','운영관리','개발 관제판 점검(R1·R2 장부 어긋남)',(f'장부 어긋남 {bn}건' if bn is not None else '관제판 점검 끝내지 못함')+(' · '+' · '.join(f'{k} {v}' for k,v in sorted({r_:len(re.findall(\"^\"+r_+\" (?!제외)\",B,re.M)) for r_ in ('R1','R2')}.items()) if v) if bn else '')+(f' · R4·R5·R6 {bo}건은 주간 보고에서 뺌(비서 제안이 매일 봄)' if bo else ''),[l for l in B.split('\\n') if l.startswith('미점검 ')][:8])\n")
s=s.replace(old4,new4)
# P12 S-OPS-8 secretary week
rep("    ib('S-OPS-5','운영관리','PC 상태 점검',f'PC 상태 {host}',A[:5])\n",
    "    ib('S-OPS-5','운영관리','PC 상태 점검',f'PC 상태 {host}',A[:5])\n"
    "    if I.get('secretary') is None:ib('S-OPS-8','운영관리','비서 제안 주간','비서 제안 폴더 목록을 읽지 못함 — 확인 필요')\n"
    "    else:\n"
    "        SW=SECW(I.get('secretary'),sun,sat);SS={};SD={};SX=[];sdn=0\n"
    "        for n_ in SW:\n"
    "            tx_=R('workspace/outputs/secretary/'+n_)\n"
    "            if tx_ is None:SX.append(n_[5:10]);continue\n"
    "            sdn+=1;tx_=tx_.replace('\\r\\n','\\n');q_=re.search(r'(?ms)^## 멈춤 의심[^\\n]*\\n(.*?)(?=^## |\\Z)',tx_)\n"
    "            for l_ in (q_.group(1).split('\\n') if q_ else []):\n"
    "                z_=re.match(r'^- ([\\w][\\w.-]*) · ',l_)\n"
    "                if z_:SS.setdefault(z_.group(1),[]).append(n_[5:10])\n"
    "            for l_ in tx_.split('\\n'):\n"
    "                z_=re.match(r'^\\d+\\. \\[[^\\]]*\\] (.*)$',l_);k_=re.search(r'계속 (\\d+)일째',l_)\n"
    "                if z_ and k_ and int(k_.group(1))>=5:\n"
    "                    t_=re.split(r' — | · ',z_.group(1))[0];SD[t_]=max(SD.get(t_,0),int(k_.group(1)))\n"
    "        ib('S-OPS-8','운영관리','비서 제안 주간',f\"비서 제안 기록 {sdn}/6일(월~토) · 멈춤 의심 {len(SS)}건 · 계속 5일 이상 {len(SD)}건\"+(f\" · 받지 못함 {len(SX)}개({', '.join(SX)})\" if SX else ''),[f\"멈춤 의심: {k}({len(v)}일 표시, 마지막 {v[-1]})\" for k,v in sorted(SS.items())][:8]+[f'계속 {v}일째: {k}' for k,v in sorted(SD.items(),key=lambda z:(-z[1],z[0]))][:8])\n")
# P8 team line label
rep("관제판 점검 발견 {bn if bn is not None else '불완전'}\"","장부 어긋남(R1·R2) {bn if bn is not None else '불완전'}\"")
# P13 answer by decision card
rep("· 기한 (\\d{4}-\\d{2}-\\d{2}) · 답 양식',ln)","· 기한 (\\d{4}-\\d{2}-\\d{2}) · 답 (?:양식|방법)',ln)")
rep("— 답 양식 `결정 {x['sec']}: {x['d']} <선택>`\"","— 답 방법 `사장실 결정 카드`\"")
rep("· 기한 {dd.isoformat()} · 답 양식 `결정 {U['id']}: D{n} <선택>`\")","· 기한 {dd.isoformat()} · 답 방법 `사장실 결정 카드(일 10:05 결과 모음이 올림)`\")")
rep("— 답 양식 `(.*)`$',ln)\n                    if mw:","— 답 (?:양식|방법) `(.*)`$',ln)\n                    if mw:")
rep("· 기한 (\\d{4}-\\d{2}-\\d{2}) · 답 양식 `(.*)`$',ln)\n                    if md:","· 기한 (\\d{4}-\\d{2}-\\d{2}) · 답 (?:양식|방법) `(.*)`$',ln)\n                    if md:")
# P14 header (new file only)
rep("Cowork(결정 ceo-<날짜> 처리)","사장실 결과 모음(결정 카드, 일 10:05) · Cowork(답 줄 처리)")
rep("(<YYYY-MM-DD HH:MM KST>, Cowork)","(<YYYY-MM-DD HH:MM KST>, 사장실 카드 또는 Cowork)")
rep("답 줄 형식 = 그 결정 줄 바로 아래 \"  - 답: <원문>","답 줄 형식 = 그 결정 줄 바로 아래 \"  - 답: <선택>")
# P9 push label
rep("관제판 점검 {(f'새로 {bw}건(전체 {bn}건)' if bw is not None else str(bn)+'건') if bn is not None else '불완전'}","장부 어긋남 {(f'새로 {bw}건(전체 {bn}건)' if bw is not None else str(bn)+'건') if bn is not None else '불완전'}")
# P6 'R1 제외:' line was counted as a new R1 finding in the push/new count
rep("BK=[k for k in re.findall(r'^(R\\d \\S+)',B,re.M) if k!='R1 제외' and","BK=[k for k in re.findall(r'^(R\\d \\S+)',B,re.M) if not k.startswith('R1 제외') and")
open(dst,'w',encoding='utf-8',newline='').write(s)
print('ok',len(s))
