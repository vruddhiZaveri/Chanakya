import { domains, domainKeys, type DomainKey } from './domains.js';
import type { DecisionState } from './decision-model.js';
export type Attachment = {id:string;name:string;size:number;type:string;text?:string};
export type Draft = {domain:DomainKey;question:string;specs:string[];depth:string;documents:Attachment[];selectedDomains:DomainKey[];followups:{question:string;time:string}[];decision?:DecisionState};
export type Investigation = {id:string;createdAt:string;draft:Draft};
// Workspace record identifiers are not authentication tokens. The fallback also supports HTTP development previews.
export function createId():string {return globalThis.crypto?.randomUUID?.() ?? `research-${Date.now().toString(36)}-${Math.random().toString(36).slice(2,12)}`;}
export function createDraft(domain:DomainKey='artha', question?:string):Draft {
 return {domain,question:question ?? domains[domain].question,specs:domains[domain].fields.map(f=>f.default),depth:'Detailed',documents:[],selectedDomains:['arogya','nyaya','artha'],followups:[]};
}
export function changeDomain(previous:Draft, domain:DomainKey, preserveQuestion=false):Draft {
 return {...createDraft(domain,preserveQuestion?previous.question:undefined),depth:previous.depth,documents:previous.documents,decision:preserveQuestion&&previous.decision?{...previous.decision,status:'draft'}:undefined,followups:preserveQuestion?previous.followups:[]};
}
export function validateQuestion(question:string):string {if(!question.trim())return 'Enter a research question.';if(question.trim().length<10)return 'Please add a little more detail (at least 10 characters).';if(question.length>4000)return 'Keep the question under 4,000 characters.';return '';}
export function validateDraft(d:Draft):string {return validateQuestion(d.question)||(d.domain==='custom'&&!d.specs[0].trim()?'Give your custom subject a name.':'')||(d.domain==='multi'&&d.selectedDomains.length<2?'Select at least two domains.':'');}
export function suggestDomains(question:string):DomainKey[] {
 const q=question.toLowerCase();const rules:[DomainKey,RegExp][]=[['arogya',/medical|health|diabet|hospital|clinical|treatment|diagnos/],['nyaya',/legal|law|court|privacy|legislation|judgment/],['artha',/loan|bank|credit|financ|lending|econom/],['nivesh',/insurance|investment|policy coverage|mutual fund/],['gati',/logistic|shipment|deliver|supply chain|warehouse/],['grantha',/literature|ramayana|mahabharata|book|poem|literary|text interpretation/]];const matches=rules.filter(([,re])=>re.test(q)).map(([k])=>k);return matches.length>1?['multi',...matches]:matches.length?matches:['custom'];
}
export function saveSnapshot(draft:Draft,id:string,now:string):Investigation {return {id,createdAt:now,draft:structuredClone(draft)};}
export function validDraft(value:unknown):value is Draft {
 if(!value||typeof value!=='object')return false;const d=value as Partial<Draft>;
 return domainKeys.includes(d.domain as DomainKey)&&typeof d.question==='string'&&Array.isArray(d.specs)&&d.specs.length===6&&d.specs.every(s=>typeof s==='string')&&typeof d.depth==='string'&&Array.isArray(d.documents)&&d.documents.every(a=>a&&typeof a.id==='string'&&typeof a.name==='string'&&typeof a.size==='number')&&Array.isArray(d.selectedDomains)&&d.selectedDomains.every(k=>domainKeys.includes(k))&&Array.isArray(d.followups)&&d.followups.every(f=>f&&typeof f.question==='string'&&typeof f.time==='string');
}
export function reportMarkdown(d:Draft):string {
 const domain=domains[d.domain];return ['# Chanakya Sabha — Research report','', '> Demonstration report. No live AI analysis or verified source retrieval has been performed.','',`## ${d.question}`,'',`Context: ${domain.name} (${domain.english})`,`Output depth: ${d.depth}`,'','## Research specifications',...domain.fields.map((f,i)=>`- ${f.label}: ${d.specs[i]}`),'','## Research overview',d.question===domain.question?domain.summary:'This investigation organizes the selected question, scope and evidence requirements. A substantive answer requires verified sources and a connected research service.','','## Scope and assumptions','Interpret the question within the selected domain, audience, region and time period.','','## Evidence and limitations','Illustrative source records are not verified publications. No numerical confidence is calculated.','',...(d.documents.length?['## Attached documents',...d.documents.map(f=>`- ${f.name} (${f.size} bytes)`),'']:[]),...(d.followups.length?['## Follow-up questions',...d.followups.map(f=>`- ${f.question}`)]:[])].join('\n');
}
