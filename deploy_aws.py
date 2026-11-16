import boto3, json, os, time, zipfile, pathlib
R='ap-south-1'; ACCOUNT='573705805509'; P='campuscare-pbl'
s=boto3.Session(region_name=R); iam=s.client('iam'); db=s.client('dynamodb'); sq=s.client('sqs'); lm=s.client('lambda'); logs=s.client('logs')
assert s.client('sts').get_caller_identity()['Account']==ACCOUNT
T=P+'-complaints'; Q=P+'-queue'; ROLE=P+'-lambda-role'
settings=lm.get_account_settings(); assert settings['AccountLimit']['ConcurrentExecutions']<=10, 'Account limit changed; review cost guard'
assert len(os.environ.get('CAMPUS_ADMIN_TOKEN',''))>=20,'Secure admin token missing'
try: db.describe_table(TableName=T)
except db.exceptions.ResourceNotFoundException:
 db.create_table(TableName=T,KeySchema=[{'AttributeName':'id','KeyType':'HASH'}],AttributeDefinitions=[{'AttributeName':'id','AttributeType':'S'}],ProvisionedThroughput={'ReadCapacityUnits':1,'WriteCapacityUnits':1},TableClass='STANDARD',Tags=[{'Key':'Project','Value':P}])
 db.get_waiter('table_exists').wait(TableName=T)
print('TABLE_READY',flush=True)
dlq=sq.create_queue(QueueName=Q+'-dlq',Attributes={'MessageRetentionPeriod':'3600','SqsManagedSseEnabled':'true'})['QueueUrl']
dlqarn=sq.get_queue_attributes(QueueUrl=dlq,AttributeNames=['QueueArn'])['Attributes']['QueueArn']
qu=sq.create_queue(QueueName=Q,Attributes={'VisibilityTimeout':'60','MessageRetentionPeriod':'3600','ReceiveMessageWaitTimeSeconds':'20','SqsManagedSseEnabled':'true','RedrivePolicy':json.dumps({'deadLetterTargetArn':dlqarn,'maxReceiveCount':3})})['QueueUrl']
qa=sq.get_queue_attributes(QueueUrl=qu,AttributeNames=['QueueArn'])['Attributes']['QueueArn']
trust={'Version':'2012-10-17','Statement':[{'Effect':'Allow','Principal':{'Service':'lambda.amazonaws.com'},'Action':'sts:AssumeRole'}]}
try: arn=iam.create_role(RoleName=ROLE,AssumeRolePolicyDocument=json.dumps(trust),Description='CampusCare lab Lambda only')['Role']['Arn']
except iam.exceptions.EntityAlreadyExistsException: arn=iam.get_role(RoleName=ROLE)['Role']['Arn']
policy={'Version':'2012-10-17','Statement':[{'Effect':'Allow','Action':['dynamodb:PutItem','dynamodb:GetItem','dynamodb:Scan'],'Resource':f'arn:aws:dynamodb:{R}:{ACCOUNT}:table/{T}'},{'Effect':'Allow','Action':['sqs:SendMessage','sqs:ReceiveMessage','sqs:DeleteMessage','sqs:GetQueueAttributes'],'Resource':qa},{'Effect':'Allow','Action':['logs:CreateLogStream','logs:PutLogEvents'],'Resource':f'arn:aws:logs:{R}:{ACCOUNT}:log-group:/aws/lambda/{P}-*:*'}]}
iam.put_role_policy(RoleName=ROLE,PolicyName=P+'-scoped',PolicyDocument=json.dumps(policy))
with zipfile.ZipFile('campuscare-lambda.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in ['app.py','index.html']: z.write(f)
code=pathlib.Path('campuscare-lambda.zip').read_bytes()
env={'TABLE_NAME':T,'QUEUE_URL':qu,'ADMIN_TOKEN':os.environ['CAMPUS_ADMIN_TOKEN']}
for suffix,cap in [('api',1),('worker',2)]:
 name=P+'-'+suffix
 try: logs.create_log_group(logGroupName='/aws/lambda/'+name)
 except logs.exceptions.ResourceAlreadyExistsException: pass
 logs.put_retention_policy(logGroupName='/aws/lambda/'+name,retentionInDays=1)
 try:
  lm.get_function(FunctionName=name)
  lm.update_function_code(FunctionName=name,ZipFile=code);lm.get_waiter('function_updated_v2').wait(FunctionName=name)
  lm.update_function_configuration(FunctionName=name,Role=arn,Handler='app.lambda_handler',Timeout=5,MemorySize=128,Environment={'Variables':env})
 except lm.exceptions.ResourceNotFoundException:
  for attempt in range(12):
   try:
    lm.create_function(FunctionName=name,Runtime='python3.13',Role=arn,Handler='app.lambda_handler',Code={'ZipFile':code},Timeout=5,MemorySize=128,Environment={'Variables':env},Architectures=['x86_64'],Tags={'Project':P});break
   except lm.exceptions.InvalidParameterValueException:
    if attempt==11: raise
    time.sleep(5)
 lm.get_waiter('function_active_v2').wait(FunctionName=name)
 # Account has a hard10 concurrency ceiling; shutdown at24h is set below.
 print('FUNCTION_READY',name,flush=True)
name=P+'-worker'
if not lm.list_event_source_mappings(FunctionName=name,EventSourceArn=qa)['EventSourceMappings']:
 lm.create_event_source_mapping(EventSourceArn=qa,FunctionName=name,BatchSize=10,MaximumBatchingWindowInSeconds=1,FunctionResponseTypes=['ReportBatchItemFailures'],ScalingConfig={'MaximumConcurrency':2})
# AWS-side safety stop must be accepted BEFORE public exposure.
from datetime import datetime,timezone,timedelta
stoprole=P+'-stop-role'; stopfn=P+'-stop'; scheduler=s.client('scheduler')
try: stoparn=iam.create_role(RoleName=stoprole,AssumeRolePolicyDocument=json.dumps(trust))['Role']['Arn']
except iam.exceptions.EntityAlreadyExistsException: stoparn=iam.get_role(RoleName=stoprole)['Role']['Arn']
iam.put_role_policy(RoleName=stoprole,PolicyName='StopOnlyCampusCare',PolicyDocument=json.dumps({'Version':'2012-10-17','Statement':[{'Effect':'Allow','Action':['lambda:PutFunctionConcurrency'],'Resource':[f'arn:aws:lambda:{R}:{ACCOUNT}:function:{P}-api',f'arn:aws:lambda:{R}:{ACCOUNT}:function:{P}-worker']}]}))
import io
buf=io.BytesIO()
with zipfile.ZipFile(buf,'w') as z:z.writestr('stop.py',"import boto3\ndef handler(event,context):\n c=boto3.client('lambda')\n for n in ['campuscare-pbl-api','campuscare-pbl-worker']: c.put_function_concurrency(FunctionName=n,ReservedConcurrentExecutions=0)\n return {'stopped':True}\n")
time.sleep(10)
try: lm.create_function(FunctionName=stopfn,Runtime='python3.13',Role=stoparn,Handler='stop.handler',Code={'ZipFile':buf.getvalue()},Timeout=15,MemorySize=128)
except lm.exceptions.ResourceConflictException: pass
lm.get_waiter('function_active_v2').wait(FunctionName=stopfn)
schedrole=P+'-scheduler-role';strust={'Version':'2012-10-17','Statement':[{'Effect':'Allow','Principal':{'Service':'scheduler.amazonaws.com'},'Action':'sts:AssumeRole'}]}
try: sa=iam.create_role(RoleName=schedrole,AssumeRolePolicyDocument=json.dumps(strust))['Role']['Arn']
except iam.exceptions.EntityAlreadyExistsException: sa=iam.get_role(RoleName=schedrole)['Role']['Arn']
iam.put_role_policy(RoleName=schedrole,PolicyName='InvokeStopOnly',PolicyDocument=json.dumps({'Version':'2012-10-17','Statement':[{'Effect':'Allow','Action':['lambda:InvokeFunction'],'Resource':f'arn:aws:lambda:{R}:{ACCOUNT}:function:{stopfn}'}]}))
expiry=(datetime.now(timezone.utc)+timedelta(hours=24)).replace(microsecond=0);time.sleep(10)
params=dict(Name=P+'-stop24h',ScheduleExpression='at('+expiry.strftime('%Y-%m-%dT%H:%M:%S')+')',ScheduleExpressionTimezone='UTC',FlexibleTimeWindow={'Mode':'OFF'},ActionAfterCompletion='DELETE',Target={'Arn':f'arn:aws:lambda:{R}:{ACCOUNT}:function:{stopfn}','RoleArn':sa,'Input':'{}','RetryPolicy':{'MaximumRetryAttempts':3,'MaximumEventAgeInSeconds':3600}})
try: scheduler.create_schedule(**params)
except scheduler.exceptions.ConflictException: scheduler.update_schedule(**params)
assert scheduler.get_schedule(Name=P+'-stop24h')['State']=='ENABLED'
print('STOP_ACCEPTED',expiry.isoformat(),flush=True)
name=P+'-api'
try: url=lm.get_function_url_config(FunctionName=name)['FunctionUrl']
except lm.exceptions.ResourceNotFoundException: url=lm.create_function_url_config(FunctionName=name,AuthType='NONE')['FunctionUrl']
for sid,action,extra in [('PublicFunctionURL','lambda:InvokeFunctionUrl',{'FunctionUrlAuthType':'NONE'}),('PublicViaURL','lambda:InvokeFunction',{'InvokedViaFunctionUrl':True})]:
 try: lm.add_permission(FunctionName=name,StatementId=sid,Action=action,Principal='*',**extra)
 except lm.exceptions.ResourceConflictException: pass
out={'expires_utc':expiry.isoformat(),'region':R,'account':ACCOUNT,'url':url,'table':T,'queue':qu,'dlq':dlq,'role':ROLE,'functions':[P+'-api',P+'-worker']}
pathlib.Path('campuscare-deployment.json').write_text(json.dumps(out,indent=2));print('DEPLOYED',json.dumps(out),flush=True)
