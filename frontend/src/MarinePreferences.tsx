import React,{useEffect,useState} from 'react';
import {Sun,Moon,Eye,Clock3} from 'lucide-react';
export type Theme='day'|'dark'|'night';
export function useTheme(){
 const [theme,setTheme]=useState<Theme>(()=>{try{const t=localStorage.getItem('neela.theme');return ['day','dark','night'].includes(t??'')?t as Theme:'day'}catch{return 'day'}});
 useEffect(()=>{document.documentElement.dataset.theme=theme;localStorage.setItem('neela.theme',theme)},[theme]);
 return {theme,setTheme};
}
export function ThemeSwitch({theme,onChange}:{theme:Theme;onChange:(t:Theme)=>void}){return <div className="theme-switch" role="group" aria-label="Display theme">{([['day',Sun,'Day'],['dark',Moon,'Dark ocean'],['night',Eye,'Night watch']] as const).map(([id,Icon,label])=><button key={id} title={label} aria-label={label+' theme'} aria-pressed={theme===id} className={theme===id?'chosen':''} onClick={()=>onChange(id)}><Icon size={14}/><span>{label}</span></button>)}</div>}
export function useMarineClock(){
 const [clock,setClock]=useState(Date.now()),[offset,setOffset]=useState(0),[sync,setSync]=useState(false);
 useEffect(()=>{let active=true;async function update(){try{const start=Date.now();const r=await fetch('/api/time');if(!r.ok)throw Error('Time API unavailable');const body=await r.json();const end=Date.now();if(active){setOffset(body.unix_ms-(start+end)/2);setSync(true)}}catch{if(active)setSync(false)}}update();const timer=setInterval(update,60000);return()=>{active=false;clearInterval(timer)}},[]);
 useEffect(()=>{setClock(Date.now()+offset);const timer=setInterval(()=>setClock(Date.now()+offset),250);return()=>clearInterval(timer)},[offset]);
 return {clock,offset,sync};
}
export function MarineClock({clock,sync,offset}:{clock:number;sync:boolean;offset:number}){
 const [zone,setZone]=useState(()=>{try{return localStorage.getItem('neela.clockzone')??'UTC'}catch{return 'UTC'}});
 const local=Intl.DateTimeFormat().resolvedOptions().timeZone;
 const zones=[...new Set(['UTC','Asia/Kolkata',local])];
 return <div className="marine-clock" title={`Clock source: ${sync?'backend UTC, network-delay compensated':'browser clock; server time unavailable'}. Host NTP/GNSS synchronization is required. Browser/server difference: ${Math.round(offset/1000)} s. All stored telemetry uses UTC.`}><Clock3 size={15}/><div><strong>{new Date(clock).toLocaleTimeString('en-GB',{timeZone:zone,hour12:false})}</strong><span>{new Date(clock).toLocaleDateString('en-GB',{timeZone:zone,day:'2-digit',month:'short',year:'numeric'})} · {sync?'SERVER CLOCK':'LOCAL FALLBACK'}</span></div><select aria-label="Clock timezone" value={zone} onChange={e=>{setZone(e.target.value);localStorage.setItem('neela.clockzone',e.target.value)}}>{zones.map(z=><option key={z} value={z}>{z==='Asia/Kolkata'?'IST (UTC+05:30)':z}</option>)}</select></div>
}
