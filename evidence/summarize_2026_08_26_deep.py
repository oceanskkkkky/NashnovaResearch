from __future__ import annotations
import json
from pathlib import Path
from collections import defaultdict

P=Path('E:/WS/NashnovaResearch/evidence/2026-08-26-stock-deep-raw.json')
d=json.loads(P.read_text(encoding='utf-8'))
codes=['sh601212','sz000603','sz000426','sz300328','sh601020']


def flatten(x):
    out=[]
    if isinstance(x,list):
        for y in x: out.extend(flatten(y))
    elif isinstance(x,dict):
        if isinstance(x.get('sections'),list): out.extend(flatten(x['sections']))
        elif isinstance(x.get('item'),list): out.extend(flatten(x['item']))
        elif isinstance(x.get('data'),list): out.extend(flatten(x['data']))
        elif isinstance(x.get('data'),dict) and isinstance(x['data'].get('item'),list): out.extend(flatten(x['data']['item']))
        else: out.append(x)
    return out


def normalize_code(value):
    raw=str(value or '').strip().lower()
    if not raw:
        return ''
    if raw.startswith(('sh','sz')) and len(raw) >= 8:
        return raw[:8]
    if raw.endswith(('.sh','.sz')):
        ticker, market = raw.split('.', 1)
        return f'{market}{ticker}'
    if raw.isdigit() and len(raw) == 6:
        return ('sh' if raw.startswith(('5','6','9')) else 'sz') + raw
    return raw

res={}
fin=flatten(d['finance']['data'])
risk=flatten(d['risk']['data'])
reports=flatten(d['reports']['data'])
notices=flatten(d['notices']['data'])
val=flatten(d['valuation']['data'].get('data'))
for code in codes:
    related=lambda rows:[r for r in rows if normalize_code(r.get('code') or r.get('symbol') or r.get('SecuCode') or r.get('thscode') or r.get('ticker'))==normalize_code(code)]
    fs=related(fin)
    fs.sort(key=lambda r:str(r.get('date') or r.get('_date') or r.get('EndDate') or ''), reverse=True)
    latest=fs[0] if fs else {}
    keep_fin={k:latest.get(k) for k in ['date','EndDate','InfoPublDate','OperatingRevenue','OperatingRevenueTTM','NPParentCompanyOwners','NPParentCompanyOwnersTTM','BasicEPS','NetCashFlowFromOperating','TotalAssets','TotalLiability'] if k in latest}
    rr=related(risk)
    rp=related(reports)
    nn=related(notices)
    vv=related(val)
    res[code]={
      'finance_latest':keep_fin,
      'finance_rows':len(fs),
      'risks_count':len(rr),
      'risks':rr[:12],
      'reports_count':len(rp),
      'reports':[ {k:r.get(k) for k in r if any(x in k.lower() for x in ['title','date','time','rating','target','id','org','author'])} for r in rp[:5] ],
      'notices_count':len(nn),
      'notices':[ {k:r.get(k) for k in r if any(x in k.lower() for x in ['title','date','time','type','id'])} for r in nn[:10] ],
      'valuation':vv[:3],
    }
Path('E:/WS/NashnovaResearch/evidence/2026-08-26-stock-deep-summary.json').write_text(json.dumps(res,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(res,ensure_ascii=False,indent=2))
