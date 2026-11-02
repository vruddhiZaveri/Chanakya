import test from 'node:test';
import assert from 'node:assert/strict';
import { toBrief, fromSession, uploadType, answerMarkdown } from '../.test-build/server-model.js';
import { api, request, ApiError } from '../.test-build/local-api.js';
import { createDraft } from '../.test-build/model.js';
import { getDecision } from '../.test-build/decision-model.js';

test('maps the actual question and context without silently trimming limits',()=>{
 const d=createDraft('artha','Is full deployment approved?');
 d.decision={...getDecision(d),objective:'Review policy',constraints:'Budget cap\n  Four weeks ',success:'Approval documented'};
 const b=toBrief(d);assert.equal(b.query,d.question);assert.deepEqual(b.constraints,['Budget cap','Four weeks']);assert.deepEqual(b.selected_domains,[]);assert.equal(b.objective,'Review policy');
 d.question='a'.repeat(2001);assert.throws(()=>toBrief(d),/2,000/);
});
test('rejects oversized structured context before creating a decision',()=>{
 const d=createDraft();d.decision={...getDecision(d),constraints:'x'.repeat(401)};assert.throws(()=>toBrief(d),/400/);
 d.decision.constraints=Array(11).fill('constraint').join('\n');assert.throws(()=>toBrief(d),/10 lines/);
 d.decision.constraints='';d.decision.objective='x'.repeat(1001);assert.throws(()=>toBrief(d),/1,000/);
});
test('only mult-domain setup submits explicitly chosen domain combination',()=>{
 const d=createDraft('multi');d.selectedDomains=['arogya','nyaya'];assert.deepEqual(toBrief(d).selected_domains,['arogya','nyaya']);
});
test('restores server context and preserves unknown domains as a custom subject',()=>{
 const b=toBrief(createDraft('grantha','What does this policy permit?'));
 const restored=fromSession({session_id:'s',revision:1,brief:b});assert.equal(restored.question,b.query);assert.equal(restored.domain,'grantha');assert.equal(restored.specs[0],Object.values(b.specifications)[0]);
 const custom=fromSession({session_id:'s',revision:1,brief:{...b,domain_key:'education'}});assert.equal(custom.domain,'custom');assert.equal(custom.specs[0],'education');
});
test('upload MIME comes from supported extension and enforces actual byte bounds',()=>{
 assert.equal(uploadType({name:'policy.PDF',size:1024*1024}),'application/pdf');
 assert.equal(uploadType({name:'policy.md',size:1}),'text/markdown');
 for(const file of [{name:'a.txt',size:0},{name:'a.txt',size:1024*1024+1},{name:'a.csv',size:3},{name:'../a.txt',size:3},{name:'a:b.txt',size:3}])assert.throws(()=>uploadType(file));
});
test('export includes only cited passages with provenance and advisory notice',()=>{
 const a={answer_id:'a',brief_revision:1,brief:{query:'Question'},evidence:{snapshot_id:'s',passages:[{source_id:'P1',filename:'policy.txt',page:1,excerpt:'Full deployment is not approved.',document_sha256:'hash',start_char:0,end_char:32},{source_id:'P2',excerpt:'UNCITED'}]},response:{model:'qwen2.5:3b',model_digest:'digest',assessment:{answer:'Not approved',limitations:['Policy only'],source_ids:['P1']}},notice:'Advisory only'};
 const text=answerMarkdown(a);assert.match(text,/Not approved/);assert.match(text,/SHA-256: hash/);assert.match(text,/Advisory only/);assert.doesNotMatch(text,/UNCITED/);
});
test('API surfaces sanitized backend error and request reference',async()=>{
 const old=globalThis.fetch;globalThis.fetch=async()=>new Response(JSON.stringify({error:{code:'model_busy',message:'Model busy'},request_id:'req-1'}),{status:429});
 try{await assert.rejects(()=>api.health(),e=>e instanceof ApiError&&e.status===429&&e.code==='model_busy'&&e.requestId==='req-1');}finally{globalThis.fetch=old;}
});
test('API distinguishes connection failures and cancellation',async()=>{
 const old=globalThis.fetch;
 try{globalThis.fetch=async()=>{throw new TypeError('failed');};await assert.rejects(()=>api.health(),e=>e.code==='connection_failed');globalThis.fetch=async()=>{throw new DOMException('Cancelled','AbortError');};await assert.rejects(()=>api.health(),e=>e.name==='AbortError');}finally{globalThis.fetch=old;}
});
test('upload sends original bytes with encoded filename and server revision',async()=>{
 const old=globalThis.fetch;const blob=new Blob(['policy']);let seen;
 globalThis.fetch=async(url,options)=>{seen={url,options};return new Response('{}');};
 try{await api.upload('session',2,blob,'policy #1.txt','text/plain');assert.equal(seen.options.body,blob);assert.equal(seen.options.headers['Content-Type'],'text/plain');assert.match(seen.url,/filename=policy%20%231.txt&expected_session_revision=2/);}finally{globalThis.fetch=old;}
});
test('answer retries can reuse the same exact idempotency payload',async()=>{
 const old=globalThis.fetch;const bodies=[];globalThis.fetch=async(_,options)=>{bodies.push(options.body);return new Response('{}');};
 try{await api.answer('s',1,'snapshot','key');await api.answer('s',1,'snapshot','key');assert.equal(bodies[0],bodies[1]);assert.deepEqual(JSON.parse(bodies[0]),{snapshot_id:'snapshot',expected_session_revision:1,idempotency_key:'key'});}finally{globalThis.fetch=old;}
});
test('rejects non-JSON frontend fallback rather than treating it as API success',async()=>{
 const old=globalThis.fetch;globalThis.fetch=async()=>new Response('<html>fallback</html>');try{await assert.rejects(()=>request('/health'),e=>e.code==='invalid_response');}finally{globalThis.fetch=old;}
});

test('request keys remain valid UUIDv4 on HTTP previews without randomUUID',async()=>{
 const {newRequestKey}=await import('../.test-build/server-model.js');
 const fake={getRandomValues(bytes){bytes.fill(170);return bytes;}};
 assert.match(newRequestKey(fake),/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/);
});
