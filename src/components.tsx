import { useEffect, useId, useRef, type ReactNode, type ButtonHTMLAttributes } from 'react';
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Menu, X } from 'lucide-react';
import { useState } from 'react';
import { createDraft, type Draft } from './model';
import { domains } from './domains';
import { useWorkspace } from './state';
export function Button({children,primary=false,className='',...props}:ButtonHTMLAttributes<HTMLButtonElement>&{primary?:boolean}){return <button type="button" className={`button ${primary?'primary':''} ${className}`} {...props}>{children}</button>;}
export function ButtonLink({to,children,primary=false,className=''}:{to:string;children:ReactNode;primary?:boolean;className?:string}){return <Link className={`button ${primary?'primary':''} ${className}`} to={to}>{children}</Link>;}
export function Card({children,className=''}:{children:ReactNode;className?:string}){return <section className={`card ${className}`}>{children}</section>;}
export function Heading({eyebrow,title,description}:{eyebrow?:string;title:string;description?:string}){return <div className="page-heading">{eyebrow&&<p className="eyebrow">{eyebrow}</p>}<h1>{title}</h1>{description&&<p className="muted">{description}</p>}</div>;}
export function QuestionCard({draft}:{draft:Draft}){return <Card className="question-card"><p className="eyebrow">RESEARCH QUESTION</p><h3>{draft.question}</h3></Card>;}
export function DepthPicker(){const {draft,setDraft}=useWorkspace();return <div className="stack small-gap"><p className="muted small">Output depth</p><p className="gold">{draft.depth}</p><div className="actions" role="group" aria-label="Output depth">{['Concise','Detailed','Comprehensive'].map(depth=><Button key={depth} aria-pressed={draft.depth===depth} className={draft.depth===depth?'selected':''} onClick={()=>setDraft(d=>({...d,depth}))}>{depth}</Button>)}</div></div>;}
export function Modal({title,children,onClose}:{title:string;children:ReactNode;onClose:()=>void}){const ref=useRef<HTMLDialogElement>(null),heading=useId();useEffect(()=>{const dialog=ref.current;dialog?.showModal();return()=>{dialog?.close();};},[]);return <dialog ref={ref} className="modal" aria-labelledby={heading} onCancel={e=>{e.preventDefault();onClose();}} onClick={e=>{if(e.target===ref.current)onClose();}}><div className="modal-inner"><div className="modal-heading"><h2 id={heading}>{title}</h2><button className="icon-button" aria-label="Close dialog" onClick={onClose}><X size={20}/></button></div>{children}</div></dialog>;}
export function Footer(){return <footer className="workspace-footer">Chanakya Sabha · Research and decision support · Sources, assumptions and limitations remain visible.</footer>;}
export { WorkspaceShell as Shell } from './experience-shell';
export function DomainContext({draft}:{draft:Draft}){const d=domains[draft.domain];return <div className="context-list"><p className="small muted">Selected context</p><p>{d.name} · {d.english}</p></div>;}
