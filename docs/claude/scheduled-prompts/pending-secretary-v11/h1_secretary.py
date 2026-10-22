import json, glob, os, datetime as dt
TODAY = dt.date(2026,10,22)
def load_board():
    out=[]
    for f in glob.glob('board/tasks/*.json'):
        j=json.load(open(f,encoding='utf-8'))
        d=j.get('data',j); d=dict(d); d['id']=os.path.basename(f)[:-5]; out.append(d)
    return [t for t in out if t.get('status')!='planned']   # 비서는 planned를 읽지 않음
def pdate(s):
    if not s: return None
    try: return dt.datetime.fromisoformat(str(s).replace('Z','+00:00')).astimezone(dt.timezone(dt.timedelta(hours=9))).date()
    except Exception:
        try: return dt.date.fromisoformat(str(s)[:10])
        except Exception: return None
def fake():
    u=lambda days: (dt.datetime(2026,10,22,9,0)-dt.timedelta(days=days)).isoformat()+'+09:00'
    return [
     dict(id='X1',status='waiting',resume=dict(type='event',date='2026-10-22',text='x'),updatedAt=u(1)),
     dict(id='X2',status='waiting',resume=dict(type='event',date='2026-10-23',text='x'),updatedAt=u(30)),
     dict(id='X3',status='waiting',resume=dict(type='manual',text='x'),updatedAt=u(8)),
     dict(id='X4',status='waiting',resume=dict(type='manual',text='x'),updatedAt=u(6)),
     dict(id='X5',status='paused',resume=dict(type='after',after=['gone-task']),updatedAt=u(20)),
     dict(id='X6',status='paused',resume=dict(type='after',after=['X2']),updatedAt=u(20)),
     dict(id='X7',status='paused',resume=dict(type='after',after=[]),updatedAt=u(20)),
     dict(id='X8',status='waiting',resume=dict(type='after',after=['X5']),updatedAt=u(2)),
     dict(id='X9',status='waiting',updatedAt=u(30)),
    ]
def candidates(tasks, version):
    read = ['decision','waiting','blocked','active'] + (['paused'] if version=='new' else [])
    T=[t for t in tasks if t.get('status') in read]
    openids={t['id'] for t in T}
    c={'가':[], '다':[], '라':[], '마':[], '바':[]}
    for t in T:
        st=t.get('status'); r=t.get('resume') or {}
        if st=='decision': c['가'].append(t['id'])
        if st=='waiting':
            if r.get('type')=='date' and pdate(r.get('date')) and pdate(r.get('date'))<=TODAY: c['다'].append(t['id'])
            elif r.get('type')=='after' and all(a not in openids for a in (r.get('after') or [])): c['다'].append(t['id'])
        if st=='blocked': c['라'].append(t['id'])
        if st=='active':
            u=pdate(t.get('updatedAt'))
            if u and (TODAY-u).days>=7: c['마'].append(t['id'])
        if version=='new':
            if st=='waiting' and r.get('type') in ('event','manual'):
                d=pdate(r.get('date')); u=pdate(t.get('updatedAt'))
                if (d and d<=TODAY) or (not d and u and (TODAY-u).days>7): c['바'].append(t['id'])
            if st=='paused':
                af=r.get('after') or []
                if af and all(a not in openids for a in af): c['바'].append(t['id'])
    return {k:sorted(v) for k,v in c.items()}
for label,data in (('실제 관제판',load_board()),('가짜 사례',fake())):
    o=candidates(data,'old'); n=candidates(data,'new')
    print('==',label,'입력',len(data),'건')
    for k in o:
        if o[k]!=n[k] or k=='바': print(f' {k} 옛={o[k]}\n    새={n[k]}')
        else: print(f' {k} 같음 ({len(o[k])}건)')
