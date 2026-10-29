import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { createDraft, validDraft, type Draft, type Investigation } from './model';
const STORAGE='chanakya-workspace-v1';
type Profile={name:string;email:string};
type State={draft:Draft;library:Investigation[];profile:Profile|null};
function initial():State{try{const s=JSON.parse(localStorage.getItem(STORAGE)||'null');return {draft:validDraft(s?.draft)?s.draft:createDraft(),library:Array.isArray(s?.library)?s.library.filter((r:Investigation)=>typeof r.id==='string'&&typeof r.createdAt==='string'&&validDraft(r.draft)):[],profile:s?.profile&&typeof s.profile.name==='string'&&typeof s.profile.email==='string'?s.profile:null};}catch{return {draft:createDraft(),library:[],profile:null};}}
type Context=State&{setDraft:React.Dispatch<React.SetStateAction<Draft>>;setLibrary:React.Dispatch<React.SetStateAction<Investigation[]>>;setProfile:React.Dispatch<React.SetStateAction<Profile|null>>;toast:(s:string)=>void;storageError:string};
const AppContext=createContext<Context|null>(null);
export function WorkspaceProvider({children}:{children:ReactNode}){const [start]=useState(initial);const [draft,setDraft]=useState(start.draft),[library,setLibrary]=useState(start.library),[profile,setProfile]=useState(start.profile),[message,setMessage]=useState(''),[storageError,setStorageError]=useState('');
useEffect(()=>{try{localStorage.setItem(STORAGE,JSON.stringify({draft,library,profile}));setStorageError('');}catch{setStorageError('Browser storage is full or unavailable. Changes are kept for this session; export important reports.');}},[draft,library,profile]);
useEffect(()=>{if(!message)return;const t=setTimeout(()=>setMessage(''),4500);return()=>clearTimeout(t);},[message]);
return <AppContext.Provider value={{draft,setDraft,library,setLibrary,profile,setProfile,toast:setMessage,storageError}}>{children}{message&&<div className="toast" role="status">{message}<button aria-label="Dismiss notification" onClick={()=>setMessage('')}>×</button></div>}</AppContext.Provider>;}
export function useWorkspace(){const c=useContext(AppContext);if(!c)throw new Error('Workspace provider required');return c;}
