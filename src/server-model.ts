import { createDraft, type Draft } from './model.js';
import { domains, domainKeys, type DomainKey } from './domains.js';
import { getDecision } from './decision-model.js';
export type Brief = {query:string;domain_key:string;selected_domains:string[];specifications:Record<string,string>;objective:string|null;constraints:string[];success_criteria:string[]};
export type Session = {session_id:string;revision:number;brief:Brief;created_at:string;updated_at:string;hypothesis_count:number};
export type SessionPage = {items:Session[];total:number;limit:number;offset:number};
export type DocumentRecord = {document_id:string;version_id:string;filename:string;sha256:string;byte_size:number;page_count:number;empty_pages:number[];passage_count:number};
export type Passage = {source_id:string;document_id:string;document_version_id:string;filename:string;document_sha256:string;page:number;start_char:number;end_char:number;excerpt:string;score:number};
export type Snapshot = {snapshot_id:string;session_id:string;brief_revision:number;query:string;passages:Passage[];created_at:string;retrieval_method:string};
export type SavedAnswer = {answer_id:string;session_id:string;brief_revision:number;created_at:string;brief:Brief;evidence:Snapshot;model_input_sha256:string;notice:string;response:{request_id:string;model:string;model_digest:string;model_attempts:number;elapsed_seconds:number;configuration:{context_tokens:number;output_tokens:number;prompt_version:string};assessment:{answer:string;source_ids:string[];limitations:string[];insufficient_evidence:boolean};validation:{schema_valid:boolean;citation_ids_valid:boolean;semantic_support_verified:false;source_authenticity_verified:false};usage:{input_tokens:number|null;output_tokens:number|null;total_model_seconds:number|null}}};
export type AnswerPage = {items:SavedAnswer[];total:number;limit:number;offset:number};
function lines(value:string,label:string){const result=value.split(/\r?\n/).map(s=>s.trim()).filter(Boolean);if(result.length>10||result.some(s=>s.length>400))throw new Error(`${label}: use up to 10 lines, each at most 400 characters.`);return result;}
export function toBrief(draft:Draft):Brief {
 const decision=getDecision(draft),query=draft.question.trim();
 if(query.length<10||query.length>2000)throw new Error('Use a question between 10 and 2,000 characters for local research.');
 if(decision.objective.trim().length>1000)throw new Error('Keep the objective within 1,000 characters.');
 const specifications=Object.fromEntries(domains[draft.domain].fields.map((f,i)=>[f.label,draft.specs[i]||'']));
 if(Object.values(specifications).some(v=>v.length>400))throw new Error('Keep each domain specification within 400 characters.');
 return {query,domain_key:draft.domain,selected_domains:draft.domain==='multi'?[...draft.selectedDomains]:[],specifications,objective:decision.objective.trim()||null,constraints:lines(decision.constraints,'Constraints'),success_criteria:lines(decision.success,'Success criteria')};
}
export function fromSession(s:Session):Draft {
 const key=domainKeys.includes(s.brief.domain_key as DomainKey)?s.brief.domain_key as DomainKey:'custom';
 const draft=createDraft(key,s.brief.query);
 draft.specs=domains[key].fields.map((f,i)=>s.brief.specifications[f.label]??draft.specs[i]);
 if(key==='custom'&&s.brief.domain_key!=='custom')draft.specs[0]=s.brief.domain_key;
 draft.selectedDomains=s.brief.selected_domains.filter((k):k is DomainKey=>domainKeys.includes(k as DomainKey));
 draft.decision={...getDecision(draft),objective:s.brief.objective||'',constraints:s.brief.constraints.join('\n'),success:s.brief.success_criteria.join('\n'),lastStage:1};
 return draft;
}
export function uploadType(file:{name:string;size:number}):string {
 const ext=file.name.split('.').pop()?.toLowerCase();
 const type=ext==='pdf'?'application/pdf':ext==='md'?'text/markdown':ext==='txt'?'text/plain':null;
 if(!type)throw new Error('Local research accepts PDF, TXT or Markdown. Other browser attachments remain in the manual workspace.');
 if(file.size<1||file.size>1024*1024)throw new Error('Upload a nonempty document up to 1 MiB.');
 if(file.name.length>120||/[\\/:\x00-\x1f\x7f]/.test(file.name))throw new Error('Use a simple filename up to 120 characters, without slashes, colons or control characters.');
 return type;
}
export function answerMarkdown(a:SavedAnswer):string {
 return ['# Chanakya — Single-agent evidence brief','',a.brief.query,'',a.response.assessment.answer,'','## Limitations',...a.response.assessment.limitations.map(s=>'- '+s),'','## Cited passages',...a.evidence.passages.filter(p=>a.response.assessment.source_ids.includes(p.source_id)).map(p=>`### ${p.source_id} — ${p.filename}, page ${p.page}\n${p.excerpt}\n\nDocument SHA-256: ${p.document_sha256}\nOffsets: ${p.start_char}–${p.end_char}`),'','## Provenance',`Answer: ${a.answer_id}`,`Brief revision: ${a.brief_revision}`,`Snapshot: ${a.evidence.snapshot_id}`,`Model: ${a.response.model}`,`Registry digest: ${a.response.model_digest}`,'',a.notice].join('\n');
}
// UUIDv4 keys also work on HTTP development previews without randomUUID support.
export function newRequestKey(runtime:Pick<Crypto,'getRandomValues'> & Partial<Pick<Crypto,'randomUUID'>>=globalThis.crypto):string {
 if(runtime?.randomUUID)return runtime.randomUUID();
 if(!runtime?.getRandomValues)throw new Error('Open this local workspace through http://localhost:5174 to create a request key.');
 const bytes=runtime.getRandomValues(new Uint8Array(16));bytes[6]=(bytes[6]&15)|64;bytes[8]=(bytes[8]&63)|128;
 const hex=Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');return `${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`;
}
