import sys
src,dst=sys.argv[1],sys.argv[2]
s=open(src,encoding='utf-8',newline='').read()
def rep(a,b,n=1):
    global s
    c=s.count(a);assert c==n,(c,a[:80]);s=s.replace(a,b)
# R1 SECW: Mon-Sat only (review #6)
rep("def SECW(ns,a,b):return sorted(n for n in (ns or []) if re.match(r'^\\d{4}-\\d{2}-\\d{2}\\.md$',str(n)) and a.isoformat()<=n[:10]<=b.isoformat())",
    "def SECW(ns,a,b):return sorted(n for n in (ns or []) if re.match(r'^\\d{4}-\\d{2}-\\d{2}\\.md$',str(n)) and a.isoformat()<=n[:10]<=b.isoformat() and dt.date.fromisoformat(n[:10]).weekday()<6)")
# R2 RESULT note only when R4-R6 existed (review #13)
rep("lambda z:f'RESULT {int(z.group(1))-bo}건 (R1·R2 — R4·R5·R6 {bo}건은 주간 보고에서 뺌: 비서 제안이 매일 봄)'",
    "lambda z:f'RESULT {int(z.group(1))-bo}건 (R1·R2'+(f' — R4·R5·R6 {bo}건은 주간 보고에서 뺌: 비서 제안이 매일 봄)' if bo else ')')")
# R3 S-OPS-8 robust parse + F-OPS-7-sec arrival finding (review #5, #6)
old=s[s.index("    if I.get('secretary') is None:ib('S-OPS-8'"):]
old=old[:old.index("    STC={};")]
new='''    if I.get('secretary') is None:ib('S-OPS-8','운영관리','비서 제안 주간','비서 제안 폴더 목록을 읽지 못함 — 확인 필요');fd('F-OPS-7-sec','운영관리','비서 제안 폴더 목록을 읽지 못함 — 이번 주 R4·R5·R6(주간 보고에서 뺀 점검)을 비서가 봤는지 확인 못 함')
    else:
        SW=SECW(I.get('secretary'),sun,sat);SS={};SD={};SX=[];SF=[];sdn=0
        for n_ in SW:
            tx_=R('workspace/outputs/secretary/'+n_)
            if tx_ is None:SX.append(n_[5:10]);continue
            tx_=tx_.replace('\\r\\n','\\n')
            if not re.search(r'(?m)^## 오늘 제안',tx_):SF.append(n_[5:10]);continue
            sdn+=1;q_=re.search(r'(?ms)^## 멈춤 의심[^\\n]*\\n(.*?)(?=^## |\\Z)',tx_)
            for l_ in (q_.group(1).split('\\n') if q_ else []):
                z_=re.match(r'^\\s*[-*] +[*`]*([\\w][\\w.-]*)[*`]* · ',l_)
                if z_ and z_.group(1) not in ('없음','해당','none'):SS.setdefault(z_.group(1),[]).append(n_[5:10])
            for l_ in tx_.split('\\n'):
                z_=re.match(r'^\\d+\\. \\[[^\\]]*\\] (.*)$',l_);k_=re.search(r'계속 (\\d+)일째',l_)
                if z_ and k_ and int(k_.group(1))>=5:
                    h_=z_.group(1);g_=re.search(r'\\(([A-Za-z0-9][\\w.]*-[\\w.-]+)\\)',re.split(r' — ',h_)[0])
                    t_=g_.group(1) if g_ else re.split(r' — | · ',h_)[0];SD[t_]=max(SD.get(t_,0),int(k_.group(1)))
        exp_=[(sun+dt.timedelta(days=i)).isoformat() for i in range(1,7)];got_={n[:10] for n in SW}
        nf_=[d[5:] for d in exp_ if d not in got_]
        if nf_ or SX or SF:fd('F-OPS-7-sec','운영관리','비서 제안 기록 빠짐 — '+' · '.join(x for x in [('파일 없음 '+', '.join(nf_)) if nf_ else '',('받지 못함 '+', '.join(SX)) if SX else '',('형식 다름 '+', '.join(SF)) if SF else ''] if x)+' (주간 보고에서 뺀 R4·R5·R6을 그날 아무도 안 봤을 수 있음)')
        ib('S-OPS-8','운영관리','비서 제안 주간',f"비서 제안 기록 {sdn}/6일(월~토) · 멈춤 의심 {len(SS)}건 · 계속 5일 이상 {len(SD)}건"+(f" · 파일 없음 {len(nf_)}일" if nf_ else '')+(f" · 받지 못함 {len(SX)}개({', '.join(SX)})" if SX else '')+(f" · 형식 다름 {len(SF)}개({', '.join(SF)})" if SF else ''),[f"멈춤 의심: {k}({len(v)}일 표시, 마지막 {v[-1]})" for k,v in sorted(SS.items())][:8]+[f'계속 {v}일째: {k}' for k,v in sorted(SD.items(),key=lambda z:(-z[1],z[0]))][:8])
'''
assert s.count(old)==1;s=s.replace(old,new)
open(dst,'w',encoding='utf-8',newline='').write(s)
print('ok',len(s.encode()))
