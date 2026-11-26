"""Restore a verified existing master and deliver it as a single release asset."""
import os,json,pathlib,sys,time,base64,hashlib,urllib.request,urllib.parse,urllib.error
from cryptography.hazmat.primitives import serialization,hashes
from cryptography.hazmat.primitives.asymmetric import rsa,padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
R=pathlib.Path('private-transfer');R.mkdir(exist_ok=True,mode=0o700)
OAEP=padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),algorithm=hashes.SHA256(),label=None)
REPO=os.environ['GITHUB_REPOSITORY'];API='https://api.github.com/repos/'+REPO
def api(path,data=None,method=None):
 req=urllib.request.Request(API+path,data=json.dumps(data).encode() if data is not None else None,method=method,headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Accept':'application/vnd.github+json','Content-Type':'application/json','Cache-Control':'no-cache'})
 with urllib.request.urlopen(req,timeout=60) as f:return json.load(f)
def setup():
 k=rsa.generate_private_key(public_exponent=65537,key_size=2048);(R/'request_private.pem').write_bytes(k.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()));pathlib.Path('media_request_public.pem').write_bytes(k.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo))
def run():
 rid=json.loads(pathlib.Path(os.environ['GITHUB_EVENT_PATH']).read_text())['inputs']['request_id'];assert len(rid)==24 and all(c in '0123456789abcdef' for c in rid)
 env=None
 for _ in range(300):
  try:
   meta=api('/contents/.media_delivery_requests/'+rid+'.json?ref=main');env=json.loads(base64.b64decode(meta['content']));break
  except urllib.error.HTTPError as e:
   if e.code!=404:raise
  time.sleep(2)
 assert env is not None,'No encrypted transfer request received'
 k=serialization.load_pem_private_key((R/'request_private.pem').read_bytes(),password=None);aes=k.decrypt(base64.b64decode(env['wrapped_key']),OAEP);plan=json.loads(AESGCM(aes).decrypt(base64.b64decode(env['nonce']),base64.b64decode(env['ciphertext']),rid.encode()))
 assert plan['sha256']=='347aaeba07ec14ea86ba1a6d288b9335b3fe59f5a85c684376ba2cfbf11e23c4' and plan['bytes']==512369561
 assert len(plan['pieces'])==6
 master=R/plan['file_name'];whole=hashlib.sha256();size=0
 with master.open('wb') as dest:
  for index,part in enumerate(plan['pieces'],1):
   parsed=urllib.parse.urlparse(part['download_url']);assert parsed.scheme=='https' and parsed.hostname.endswith('.oaiusercontent.com')
   h=hashlib.sha256();n=0
   with urllib.request.urlopen(part['download_url'],timeout=240) as f:
    while True:
     block=f.read(1024*1024)
     if not block:break
     dest.write(block);h.update(block);whole.update(block);n+=len(block);size+=len(block)
   assert n==part['bytes'] and h.hexdigest()==part['sha256'],f'Transfer part {index} mismatch'
   print(f'Verified original master part {index}/6',flush=True)
 assert size==plan['bytes'] and whole.hexdigest()==plan['sha256']
 tag='zero-document-part1-master-v02-20261127';releases=api('/releases?per_page=50');release=next((x for x in releases if x['tag_name']==tag),None)
 if release is None:release=api('/releases',{'tag_name':tag,'name':'FRAME TALES — The Zero Document — Part 1 v02 — Original 1080p','draft':True,'body':'Original 1920×1080 master. Duration33:04. Original197 voice cues plus30 Nox bridge cues; no music. Byte-for-byte verified master; not the compressed Drive review. SHA256: '+plan['sha256']})
 asset=next((x for x in release['assets'] if x['name']==master.name and x['size']==size and x['state']=='uploaded'),None)
 if asset is None:
  upload=release['upload_url'].split('{')[0]+'?'+urllib.parse.urlencode({'name':master.name})
  with master.open('rb') as f:
   request=urllib.request.Request(upload,data=f,method='POST',headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Accept':'application/vnd.github+json','Content-Type':'video/mp4','Content-Length':str(size)})
   with urllib.request.urlopen(request,timeout=900) as response:asset=json.load(response)
 assert asset['size']==size and asset['state']=='uploaded'
 if asset.get('digest'):assert asset['digest']=='sha256:'+plan['sha256']
 # User has authorized GitHub storage/delivery of video files.
 release=api('/releases/'+str(release['id']),{'draft':False},'PATCH')
 receipt={'success':True,'file_name':master.name,'bytes':size,'sha256':plan['sha256'],'no_reencode':True,'release_url':release['html_url'],'asset':asset}
 pathlib.Path('Master_Delivery_Receipt.json').write_text(json.dumps(receipt,indent=2));print('Original1080p master delivered and SHA256 verified.',flush=True)
if __name__=='__main__':{'setup':setup,'run':run}[sys.argv[1]]()
