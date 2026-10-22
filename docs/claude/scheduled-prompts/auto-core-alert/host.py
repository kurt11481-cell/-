import json,sys,datetime as T
K=T.timezone(T.timedelta(hours=9));today=sys.argv[1];hp=sys.argv[2]
EXP=['task_logon_type','auto_logon','power_sleep','update_active_hours','pending_reboot','uptime','session','backup_recent']
STANDING={'auto_logon'}
BACKUP={'backup_recent'}
try:h=json.load(open(hp,encoding='utf-8')) if hp!='-' else None
except Exception:print('H FAIL');sys.exit(0)
if not isinstance(h,dict) or h.get('schema')!='host-status/v1':print('H NO_FILE');sys.exit(0)
g=h.get('generated_at') or ''
try:t=T.datetime.fromisoformat(g.replace('Z','+00:00')).astimezone(K)
except Exception:t=None
print('H','FRESH' if t and t.date().isoformat()==today else 'STALE',t.isoformat() if t else g)
cs={c.get('id'):c for c in h.get('checks') or [] if isinstance(c,dict)}
A=[]
for i in EXP:
    c=cs.get(i)
    if i in BACKUP:continue
    if c is None:A.append(i+'(누락)');continue
    s=c.get('state')
    if s=='OK':continue
    if i in STANDING and s=='WARN':continue
    A.append('%s(%s: %s)'%(i,s,str(c.get('note') or '')[:80]))
print('H STATUS',h.get('status'),'WARN',h.get('warn_count'),'UNKNOWN',h.get('unknown_count'))
print('H STANDING',','.join(i for i in sorted(STANDING) if (cs.get(i) or {}).get('state')=='WARN') or '-')
print('H ALERT',' | '.join(A) if A else '-')
b=cs.get('backup_recent')
print('H BACKUP','누락' if b is None else ('-' if b.get('state')=='OK' else '%s(%s)'%(b.get('state'),str(b.get('note') or '')[:80])))
