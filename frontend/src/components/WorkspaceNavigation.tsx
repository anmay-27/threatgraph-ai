import { api } from '../api';
import { client } from './shared';
import { useEffect, useRef, useState } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import { Boxes, History, Network, ScanLine, MoreHorizontal, X, LayoutDashboard, Mail, BookOpen, ShieldCheck } from 'lucide-react';
import CommandMenu from './CommandMenu';
import ThemeToggle from './ThemeToggle';

export default function WorkspaceNavigation({role,connected,offline,privacy,email,authRequired}:{role?:string;connected:boolean;offline:boolean;privacy?:boolean;email?:string;authRequired?:boolean}){
 const dialog=useRef<HTMLDialogElement>(null);
 const location=useLocation();
 const analyst=!!role;
 const [logoutError,setLogoutError]=useState(''),[loggingOut,setLoggingOut]=useState(false);
 useEffect(()=>{dialog.current?.close();},[location.pathname]);
 const primary=[{to:'/analyze',label:'Investigate',icon:ScanLine},...(analyst?[{to:'/cases',label:'Cases',icon:Boxes}]:[]),{to:'/history',label:'History',icon:History},...(analyst?[{to:'/intelligence',label:'Graph',icon:Network}]:[])];
 const groups=[{title:'Workspace',links:[{to:'/dashboard',label:'Overview',icon:LayoutDashboard},...(analyst?[{to:'/intelligence',label:'Intelligence graph',icon:Network}]:[])]},{title:'Tools',links:[{to:'/messages',label:'Message / email',icon:Mail},{to:'/research/models',label:'Model registry',icon:Boxes}]},{title:'Help & settings',links:[{to:'/demo',label:'Demo guide',icon:ShieldCheck},{to:'/about/methodology',label:'Methodology',icon:BookOpen}]}];
 const moreActive=groups.some(g=>g.links.some(l=>l.to===location.pathname));
 const moreButton=(mobile=false)=><button type="button" className={moreActive?'nav-more current':'nav-more'} aria-label={mobile?'More navigation':'More pages'} aria-haspopup="dialog" onClick={()=>dialog.current?.showModal()}><MoreHorizontal size={20}/><span>More</span></button>;
 const link=(item:typeof primary[number])=><NavLink key={item.to} to={item.to} className={({isActive})=>isActive||(item.to==='/analyze'&&location.pathname==='/')?'current':''}><item.icon size={18}/><span>{item.label}</span></NavLink>;
 return <>
  <header className="workspace-header"><Link className="workspace-brand" to="/analyze" aria-label="ThreatGraph home"><span><Network size={22}/></span><strong>ThreatGraph <b>AI</b></strong></Link><nav className="desktop-navigation" aria-label="Main navigation">{primary.map(link)}{moreButton()}</nav><div className="header-tools"><span className={'connection-chip '+(offline?'offline':'')} title={privacy===false?'External services configurable':'Privacy mode'}><i/>{offline?'Offline':connected?'Connected':'Connecting'}</span><CommandMenu/><ThemeToggle/></div></header>
  <nav className="mobile-navigation" aria-label="Mobile navigation">{primary.filter(l=>l.to!=='/intelligence').map(link)}{moreButton(true)}</nav>
  <dialog ref={dialog} className="navigation-dialog" aria-label="More navigation" onClick={e=>{if(e.target===dialog.current)dialog.current.close();}}><div className="navigation-dialog-heading"><div><span className="eyebrow">YOUR WORKSPACE</span><h2>Explore ThreatGraph</h2></div><button aria-label="Close navigation" onClick={()=>dialog.current?.close()}><X size={19}/></button></div><div className="navigation-groups">{groups.map(group=><section key={group.title}><h3>{group.title}</h3>{group.links.map(item=><NavLink key={item.to} to={item.to} onClick={()=>dialog.current?.close()}><item.icon size={18}/><span>{item.label}</span></NavLink>)}</section>)}</div>{authRequired&&<div className="navigation-account"><span>{email}</span><button disabled={loggingOut} onClick={async()=>{setLoggingOut(true);setLogoutError('');try{await api('/auth/logout',{method:'POST'});client.clear();window.location.assign('/');}catch(e){setLogoutError((e as Error).message);setLoggingOut(false);}}}>{loggingOut?'Logging out...':'Log out'}</button>{logoutError&&<p role="alert">{logoutError}</p>}</div>}<p className="navigation-status">{offline?'API offline':connected?'API connected':'Connecting to API'} · {privacy===false?'External services configurable':'Privacy mode'}</p></dialog>
 </>;
}
