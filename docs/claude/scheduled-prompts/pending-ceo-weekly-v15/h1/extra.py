import json,os,re,subprocess,shutil
W='/sessions/rcw-01kumgkivae5ucwboovezgjf/work';B=W+'/t/v15-chain'
def run(tag,date,prevfile,mod_in=None,board=None):
    d=f'{W}/t/x-{tag}';shutil.rmtree(d,ignore_errors=True);shutil.copytree(f'{B}/{date}',d,symlinks=True,ignore=shutil.ignore_patterns('report-after.md'))
    os.remove(d+'/root/docs/claude/ceo-weekly-report.md') if os.path.lexists(d+'/root/docs/claude/ceo-weekly-report.md') else None
    shutil.copy(prevfile,d+'/root/docs/claude/ceo-weekly-report.md')
    I=json.load(open(d+'/in.json',encoding='utf-8'))
    if mod_in:mod_in(I)
    json.dump(I,open(d+'/in.json','w',encoding='utf-8'),ensure_ascii=False)
    if board is not None:open(d+'/board.txt','w',encoding='utf-8').write(board)
    env=dict(os.environ,CEO_NOW=date+'T09:55:00+09:00')
    r=subprocess.run(['python3','-I',B+'/ceo_test.py','run',date,d+'/root',d+'/in.json',d+'/board.txt',d+'/tasks'],capture_output=True,text=True,env=env)
    return r.returncode,(json.loads(r.stdout.split('\n')[0]) if r.returncode==0 else r.stderr[-400:]),d
# T-ans: answer line under ceo-2026-11-01 D1
p=open(f'{B}/2026-11-01/report-after.md',encoding='utf-8').read()
k=p.index('<!-- id: ceo-2026-11-01 -->');m=re.compile(r'^- (?:⚠ )?D1 .*$',re.M).search(p,k)
q=p[:m.end()]+'\n  - 답: a) 예(2026-11-02 10:07 KST, 사장실 카드)'+p[m.end():]
open(W+'/t/ans-prev.md','w',encoding='utf-8').write(q)
rc,o,d=run('ans','2026-11-08',W+'/t/ans-prev.md');print('T-ans',rc,o['prev'] if rc==0 else o)
# T-fail: secretary None, docs incomplete, board incomplete
def mi(I):I['secretary']=None;I['complete']['docs']=False
rc,o,d=run('fail','2026-11-08',f'{B}/2026-11-01/report-after.md',mi,'점검 불완전(스크립트)')
print('T-fail',rc,o['color'] if rc==0 else o,[ (f['id'],f['sev'],f['text'][:50]) for f in o['findings'] if f['id'].startswith('F-OPS-4')] if rc==0 else '')
print([l for l in open(d+'/section.md',encoding='utf-8').read().split('\n') if 'S-OPS-8' in l or 'S-OPS-4' in l])
# T-docsFalse with real board
def mi2(I):I['complete']['docs']=False
rc,o,d=run('docs','2026-11-08',f'{B}/2026-11-01/report-after.md',mi2)
sec=open(d+'/section.md',encoding='utf-8').read()
print('T-docs',rc,[f['text'][:80] for f in o['findings'] if f['id'] in('F-OPS-4','F-OPS-5')],[l for l in sec.split('\n') if l.startswith('RESULT') or 'S-OPS-4' in l])
