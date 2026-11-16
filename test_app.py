import importlib.util,json,os,tempfile,time,unittest
from pathlib import Path
os.environ['DB_PATH']=tempfile.mktemp(suffix='.sqlite3');os.environ['ADMIN_TOKEN']='unit-test-only'
spec=importlib.util.spec_from_file_location('app',Path(__file__).parent/'app.py'); app=importlib.util.module_from_spec(spec);spec.loader.exec_module(app)
class AppTests(unittest.TestCase):
 def create(self):
  code,d=app.dispatch('POST','/api/complaints',{},dict(name='Demo User',title='WiFi unavailable',description='No connection in the network lab.',category='Network'),{})
  self.assertEqual(code,201);return d
 def test_lifecycle(self):
  d=self.create();key=d['complaint']['id'];path='/api/complaints/'+key
  self.assertEqual(app.dispatch('GET',path,{}, {},{})[0],403)
  self.assertEqual(app.dispatch('GET',path,{'x-tracking-token':d['tracking_token']},{},{})[0],200)
  app.process(key);c=app.store().get(key);self.assertEqual(c['status'],'Assigned');self.assertEqual(c['assigned_to'],'IT Helpdesk')
  app.process(key);self.assertEqual(len(app.store().get(key)['history']),2)
  h={'authorization':'Bearer unit-test-only'}
  self.assertEqual(app.dispatch('PATCH',path,h,{'status':'Resolved','note':'Replaced faulty access point'},{})[0],200)
  self.assertEqual(app.dispatch('PATCH',path,h,{'status':'Assigned','note':'backward'},{})[0],409)
  self.assertNotIn('tracking_hash',app.dispatch('GET',path,h,{}, {})[1]['complaint'])
 def test_auth_and_validation(self):
  self.assertEqual(app.dispatch('GET','/api/complaints',{}, {},{})[0],401)
  self.assertEqual(app.dispatch('POST','/api/complaints',{}, {},{})[0],400)
  self.assertEqual(app.dispatch('GET','/api/complaints/CC-000000000000',{}, {},{})[0],404)
 def test_lambda_health(self):
  result=app.lambda_handler({'rawPath':'/api/health','requestContext':{'http':{'method':'GET'}}},None)
  self.assertEqual(result['statusCode'],200)
if __name__=='__main__':unittest.main()
