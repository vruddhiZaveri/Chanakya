import type { Brief, Session, SessionPage, DocumentRecord, Snapshot, SavedAnswer, AnswerPage } from './server-model.js';
export class ApiError extends Error {constructor(message:string,public status:number,public code:string,public requestId?:string){super(message);}}
export async function request<T>(path:string,init:RequestInit={}):Promise<T>{
 let response:Response;
 try {response=await fetch('/api/v1'+path,{...init,headers:{...(init.body instanceof Blob?{}:init.body?{'Content-Type':'application/json'}:{}),...init.headers}});}
 catch(e){if(e instanceof DOMException&&e.name==='AbortError')throw e;throw new ApiError('The local backend could not be reached. Keep the Python server running on port 8000.',0,'connection_failed');}
 const data=await response.json().catch(()=>null);
 if(!response.ok)throw new ApiError(data?.error?.message||`The backend returned HTTP ${response.status}.`,response.status,data?.error?.code||'http_error',data?.request_id);
 if(data===null||typeof data!=='object')throw new ApiError('The API returned an unexpected response. Start this app through the configured Vite server.',response.status,'invalid_response');
 return data as T;
}
const post=(payload:unknown)=>({method:'POST',body:JSON.stringify(payload)});
export const api={
 health:(signal?:AbortSignal)=>request<{status:string;increment:number;storage_ready:boolean}>('/health',{signal}),
 create:(brief:Brief)=>request<Session>('/sessions',post(brief)),
 sessions:(offset=0,limit=20,signal?:AbortSignal)=>request<SessionPage>(`/sessions?limit=${limit}&offset=${offset}`,{signal}),
 session:(id:string,signal?:AbortSignal)=>request<Session>(`/sessions/${id}`,{signal}),
 documents:(id:string,signal?:AbortSignal)=>request<DocumentRecord[]>(`/sessions/${id}/documents`,{signal}),
 upload:(id:string,revision:number,file:Blob,name:string,type:string)=>request<DocumentRecord>(`/sessions/${id}/documents?filename=${encodeURIComponent(name)}&expected_session_revision=${revision}`,{method:'POST',body:file,headers:{'Content-Type':type}}),
 search:(id:string,revision:number,query:string,documentIds:string[])=>request<Snapshot>(`/sessions/${id}/evidence/search`,post({query,expected_session_revision:revision,limit:3,document_ids:documentIds})),
 answer:(id:string,revision:number,snapshot:string,key:string)=>request<SavedAnswer>(`/sessions/${id}/answers`,post({snapshot_id:snapshot,expected_session_revision:revision,idempotency_key:key})),
 answers:(id:string,offset=0,signal?:AbortSignal)=>request<AnswerPage>(`/sessions/${id}/answers?limit=10&offset=${offset}`,{signal}),
 getAnswer:(id:string,answer:string,signal?:AbortSignal)=>request<SavedAnswer>(`/sessions/${id}/answers/${answer}`,{signal}),
 page:(id:string,document:string,page:number,signal?:AbortSignal)=>request<{text:string;offset_basis:string}>(`/sessions/${id}/documents/${document}/pages/${page}`,{signal}),
 content:(id:string,document:string)=>`/api/v1/sessions/${id}/documents/${document}/content`,
};
export function errorText(error:unknown):string{return error instanceof ApiError?`${error.message}${error.requestId?' Reference: '+error.requestId:''}`:error instanceof Error?error.message:'The operation could not be completed.';}
