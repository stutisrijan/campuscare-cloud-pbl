"""CampusCare PBL: stdlib local server + AWS Lambda HTTP adapter."""
import base64, datetime as dt, hashlib, hmac, json, os, re, secrets, sqlite3, threading, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = os.getenv('DB_PATH', str(ROOT / 'demo.sqlite3'))
STATUSES = ['Submitted', 'Assigned', 'In Progress', 'Resolved']
CATEGORIES = ['Hostel', 'Classroom', 'Lab', 'Network', 'Other']
ADMIN_TOKEN = os.getenv('ADMIN_TOKEN', '')

def now(): return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
def conn():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
    c.execute('CREATE TABLE IF NOT EXISTS complaints(id TEXT PRIMARY KEY, data TEXT NOT NULL)')
    return c
class LocalStore:
    def put(self, item):
        with conn() as c: c.execute('INSERT OR REPLACE INTO complaints VALUES (?,?)', (item['id'], json.dumps(item)))
    def get(self, key):
        with conn() as c: row = c.execute('SELECT data FROM complaints WHERE id=?',(key,)).fetchone()
        return json.loads(row['data']) if row else None
    def all(self):
        with conn() as c: rows = c.execute('SELECT data FROM complaints').fetchall()
        return [json.loads(r['data']) for r in rows]
class AWSStore:
    def __init__(self):
        import boto3
        self.table = boto3.resource('dynamodb').Table(os.environ['TABLE_NAME'])
    def put(self,item): self.table.put_item(Item=item)
    def get(self,key): return self.table.get_item(Key={'id':key},ConsistentRead=True).get('Item')
    def all(self):
        # Deliberately capped for a small teaching demo, not production analytics.
        return self.table.scan(Limit=200).get('Items',[])
def store(): return AWSStore() if os.getenv('TABLE_NAME') else LocalStore()
def admin(headers):
    value = headers.get('authorization','')
    return bool(ADMIN_TOKEN) and hmac.compare_digest(value, 'Bearer '+ADMIN_TOKEN)
def public(item):
    return {k:v for k,v in item.items() if k not in ['tracking_hash','name']}
def tracking_valid(item, token):
    return bool(token) and hmac.compare_digest(item['tracking_hash'],hashlib.sha256(token.encode()).hexdigest())
def process(key):
    s=store(); item=s.get(key)
    if not item or item['status']!='Submitted': return
    item['assigned_to']={'Hostel':'Hostel Office','Classroom':'Facilities','Lab':'Lab Support','Network':'IT Helpdesk'}.get(item['category'],'Campus Office')
    item['status']='Assigned'; item['updated_at']=now()
    item['history'].append({'status':'Assigned','at':item['updated_at'],'note':'Automatically routed to '+item['assigned_to']})
    s.put(item)
def enqueue(key):
    if os.getenv('QUEUE_URL'):
        import boto3
        boto3.client('sqs').send_message(QueueUrl=os.environ['QUEUE_URL'],MessageBody=json.dumps({'id':key}))
    else: threading.Timer(.6,process,args=(key,)).start()
def dispatch(method,path,headers,body,query):
    s=store()
    if path=='/api/health': return 200,{'ok':True,'mode':'AWS' if os.getenv('TABLE_NAME') else 'Local demo'}
    if path=='/api/complaints' and method=='POST':
        name=str(body.get('name','')).strip(); title=str(body.get('title','')).strip(); description=str(body.get('description','')).strip(); category=body.get('category')
        if not 2<=len(name)<=60 or not 5<=len(title)<=100 or not 10<=len(description)<=1000 or category not in CATEGORIES: return 400,{'error':'Enter a name (2-60), title (5-100), description (10-1000) and valid category.'}
        if body.get('priority','Normal') not in ['Normal','High']: return 400,{'error':'Invalid priority'}
        token=secrets.token_urlsafe(24); stamp=now(); key='CC-'+uuid.uuid4().hex[:12].upper()
        item={'id':key,'name':name,'title':title,'description':description,'category':category,'priority':body.get('priority','Normal'),'status':'Submitted','assigned_to':'Awaiting routing','created_at':stamp,'updated_at':stamp,'tracking_hash':hashlib.sha256(token.encode()).hexdigest(),'history':[{'status':'Submitted','at':stamp,'note':'Complaint received'}]}
        s.put(item)
        try: enqueue(key)
        except Exception:
            return 202,{'complaint':public(item),'tracking_token':token,'warning':'Saved, but routing is delayed. Administrator can retry routing.'}
        return 201,{'complaint':public(item),'tracking_token':token}
    if path=='/api/complaints' and method=='GET':
        if not admin(headers): return 401,{'error':'Administrator token required'}
        return 200,{'complaints':sorted([public(i) for i in s.all()],key=lambda x:x['created_at'],reverse=True)}
    match=re.fullmatch(r'/api/complaints/(CC-[A-F0-9]{12})(/route)?',path)
    if match:
        item=s.get(match[1])
        if not item: return 404,{'error':'Complaint not found'}
        if method=='GET':
            if not admin(headers) and not tracking_valid(item,headers.get('x-tracking-token','')): return 403,{'error':'Tracking secret required'}
            return 200,{'complaint':public(item)}
        if not admin(headers): return 401,{'error':'Administrator token required'}
        if method=='POST' and match[2]:
            enqueue(item['id']); return 202,{'ok':True}
        if method=='PATCH':
            status=body.get('status'); note=str(body.get('note','')).strip()
            if status not in STATUSES or not 3<=len(note)<=250: return 400,{'error':'Choose a valid status and enter a note (3-250 characters).'}
            if STATUSES.index(status)<STATUSES.index(item['status']): return 409,{'error':'Status cannot move backwards.'}
            item['status']=status; item['updated_at']=now(); item['history'].append({'status':status,'at':item['updated_at'],'note':note}); s.put(item)
            return 200,{'complaint':public(item)}
    return 404,{'error':'Not found'}
def lambda_handler(event,context):
    if 'Records' in event:
        failures=[]
        for record in event['Records']:
            try: process(json.loads(record['body'])['id'])
            except Exception: failures.append({'itemIdentifier':record['messageId']})
        return {'batchItemFailures':failures}
    method=event.get('requestContext',{}).get('http',{}).get('method','GET'); path=event.get('rawPath','/')
    if not path.startswith('/api/'):
        return {'statusCode':200,'headers':{'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'},'body':Path(__file__).with_name('index.html').read_text()}
    try:
        data=event.get('body') or '{}'
        if event.get('isBase64Encoded'): data=base64.b64decode(data).decode()
        code,result=dispatch(method,path,{k.lower():v for k,v in event.get('headers',{}).items()},json.loads(data),event.get('queryStringParameters') or {})
    except (ValueError,TypeError): code,result=400,{'error':'Invalid JSON request'}
    except Exception: code,result=500,{'error':'The server could not complete this request.'}
    return {'statusCode':code,'headers':{'Content-Type':'application/json','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'},'body':json.dumps(result,default=str)}
class Handler(BaseHTTPRequestHandler):
    def run_request(self):
        from urllib.parse import urlsplit,parse_qs
        path=urlsplit(self.path).path
        if not path.startswith('/api/'):
            data=(ROOT/'frontend/index.html').read_bytes(); self.send_response(200); self.send_header('Content-Type','text/html'); self.end_headers(); self.wfile.write(data); return
        try:
            length=int(self.headers.get('Content-Length',0))
            if length>16384: raise ValueError()
            body=json.loads(self.rfile.read(length) or '{}'); code,result=dispatch(self.command,path,{k.lower():v for k,v in self.headers.items()},body,parse_qs(urlsplit(self.path).query))
        except (ValueError,TypeError): code,result=400,{'error':'Invalid request'}
        except Exception: code,result=500,{'error':'The server could not complete this request.'}
        data=json.dumps(result).encode(); self.send_response(code); self.send_header('Content-Type','application/json'); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(data)
    do_GET=do_POST=do_PATCH=run_request
if __name__=='__main__':
    print('CampusCare local demo: http://127.0.0.1:8000 (binds localhost only)')
    print('Admin mode enabled' if ADMIN_TOKEN else 'Admin mode disabled: set ADMIN_TOKEN to enable')
    ThreadingHTTPServer(('127.0.0.1',8000),Handler).serve_forever()
