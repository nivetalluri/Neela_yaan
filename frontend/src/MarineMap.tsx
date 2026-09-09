import React,{useState,useEffect,useMemo} from 'react';
import {MapContainer,TileLayer,Polyline,CircleMarker,Circle,Tooltip,ScaleControl,GeoJSON,Pane,useMap,useMapEvents} from 'react-leaflet';
import {Compass,Crosshair,Globe2,Layers,LocateFixed,MapPin,Maximize2,Navigation,ShieldCheck,X} from 'lucide-react';
import type {Telemetry} from './types';
import worldLand from './assets/world-land.json';
import type {GeoJsonObject} from 'geojson';
import type {LatLngTuple,LeafletMouseEvent} from 'leaflet';

export function coordinate(n:number|null|undefined,lat:boolean){
 if(n==null||!Number.isFinite(n))return 'No valid fix';
 return `${Math.abs(n).toFixed(6)}° ${lat?(n<0?'S':'N'):(n<0?'W':'E')}`;
}
export function dms(n:number|null|undefined,lat:boolean){
 if(n==null)return '—';
 const total=Math.round(Math.abs(n)*3600*100)/100,deg=Math.floor(total/3600),min=Math.floor(total%3600/60),sec=total%60;
 return `${deg}° ${String(min).padStart(2,'0')}′ ${sec.toFixed(2)}″ ${lat?(n<0?'S':'N'):(n<0?'W':'E')}`;
}
function valid(d:Telemetry){const n=d.navigation;return n.gps_fix&&n.latitude!=null&&n.longitude!=null&&Math.abs(n.latitude)<=90&&Math.abs(n.longitude)<=180;}
export function haversine(a:LatLngTuple,b:LatLngTuple){const r=Math.PI/180;const q=Math.sin((b[0]-a[0])*r/2)**2+Math.cos(a[0]*r)*Math.cos(b[0]*r)*Math.sin((b[1]-a[1])*r/2)**2;return 6371008.8*2*Math.atan2(Math.sqrt(Math.min(1,q)),Math.sqrt(Math.max(0,1-q)));}
function MapController({command,position,follow,large,onCursor}:{command:{action:string;id:number};position:LatLngTuple|null;follow:boolean;large:boolean;onCursor:(x:LatLngTuple)=>void}){
 const map=useMap();
 useMapEvents({mousemove:(e:LeafletMouseEvent)=>onCursor([e.latlng.lat,((e.latlng.lng+180)%360+360)%360-180])});
 useEffect(()=>{if(large)map.fitBounds([[-78,-175],[78,175]],{padding:[20,20]});},[]);
 useEffect(()=>{setTimeout(()=>map.invalidateSize(),100)},[command]);
 useEffect(()=>{if(position&&follow&&Math.abs(position[0])<=85.0511)map.panTo(position,{animate:false})},[position?.[0],position?.[1],follow]);
 useEffect(()=>{
  if(command.action==='world')map.fitBounds([[-78,-175],[78,175]],{padding:[20,20]});
  if(command.action==='platform'&&position)map.setView(position,7,{animate:false});
 },[command.id]);
 return null;
}
export function MarineMap({history,d,large=false}:{history:Telemetry[];d:Telemetry|null;large?:boolean}){
 const [follow,setFollow]=useState(!large),[expanded,setExpanded]=useState(false),[grid,setGrid]=useState(true),[layer,setLayer]=useState('world'),[tileError,setTileError]=useState(false),[cursor,setCursor]=useState<LatLngTuple|null>(null),[command,setCommand]=useState({action:'',id:0});
 const fixes=useMemo(()=>history.filter(x=>x.source===d?.source&&valid(x)),[history,d?.source]);
 const last=fixes.at(-1);const position:LatLngTuple|null=last?[last.navigation.latitude!,last.navigation.longitude!]:null;
 const current=!!d&&valid(d);const polar=position!=null&&Math.abs(position[0])>85.0511;
 const track=useMemo(()=>{const chunks:LatLngTuple[][]=[];let part:LatLngTuple[]=[];for(const f of fixes){let p:LatLngTuple=[f.navigation.latitude!,f.navigation.longitude!];if(Math.abs(p[0])>85.0511){if(part.length)chunks.push(part);part=[];continue;}if(part.length&&Math.abs(p[1]-part.at(-1)![1])>180){chunks.push(part);part=[];}part.push(p);}if(part.length)chunks.push(part);return chunks;},[fixes]);
 const go=(action:string)=>{setFollow(action==='platform');setCommand(c=>({action,id:c.id+1}))};
 return <section className={'panel marine-map-panel '+(expanded?'marine-expanded':'')}>
 <div className="marine-map-toolbar"><div className="map-heading"><Globe2 size={17}/><div><strong>{large?'Global navigation':'Platform position'}</strong><small>WGS 84 · GEOGRAPHIC COORDINATES</small></div></div><div className="map-tool-actions"><button title="Show the whole world" onClick={()=>go('world')}><Globe2 size={14}/><span>World</span></button><button title="Locate platform from telemetry" disabled={!position||polar} onClick={()=>go('platform')}><LocateFixed size={14}/><span>Locate NY–01</span></button><button className={grid?'selected-control':''} aria-pressed={grid} title="Toggle latitude/longitude grid" onClick={()=>setGrid(!grid)}><Layers size={14}/></button><button title={expanded?'Close expanded map':'Expand navigation map'} onClick={()=>{setExpanded(!expanded);setCommand(c=>({...c,id:c.id+1}))}}>{expanded?<X size={14}/>:<Maximize2 size={14}/>}</button></div></div>
 <div className={'marine-map-canvas '+(large?'large':'')}>
 <MapContainer center={position&&!polar?position:[-30,30]} zoom={large?2:3} minZoom={1} maxZoom={18} zoomSnap={.5} maxBounds={[[-85.0511,-180],[85.0511,180]]} maxBoundsViscosity={1} zoomControl={true}>
 <Pane name="reference-coastline" style={{zIndex:190}}><GeoJSON data={worldLand as unknown as GeoJsonObject} interactive={false} style={{fillColor:'#f3efe5',fillOpacity:1,color:'#88aeba',weight:.5}}/></Pane>
 <TileLayer key={layer} noWrap maxNativeZoom={layer==='ocean'?10:19} url={layer==='ocean'?'https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}':'https://tile.openstreetmap.org/{z}/{x}/{y}.png'} attribution={layer==='ocean'?'Tiles © Esri · GEBCO · NOAA · Natural Earth':'© OpenStreetMap contributors · Natural Earth'} eventHandlers={{tileerror:()=>setTileError(true)}}/>
 <MapController command={command} position={position} follow={follow} large={large} onCursor={setCursor}/>
 {grid&&<>{[-60,-30,0,30,60].map(lat=><Polyline key={'lat'+lat} positions={[[lat,-180],[lat,180]]} interactive={false} pathOptions={{color:'#547d93',weight:.7,opacity:.35,dashArray:lat===0?undefined:'4 8'}}/>)}{[-150,-120,-90,-60,-30,0,30,60,90,120,150].map(lon=><Polyline key={'lon'+lon} positions={[[-85,lon],[85,lon]]} interactive={false} pathOptions={{color:'#547d93',weight:.7,opacity:.35,dashArray:lon===0?undefined:'4 8'}}/>)}</>}
 {track.map((part,i)=><Polyline key={i} positions={part} pathOptions={{color:'#eaaa62',weight:2.5,opacity:.9}}/>)}
 {position&&!polar&&<><Circle center={position} radius={Math.max(0,last?.navigation.accuracy??0)} pathOptions={{color:'#39baac',weight:1,fillOpacity:.12}}/><CircleMarker center={position} radius={7} pathOptions={{color:'#fff4df',fillColor:current?'#e6a45b':'#99a5ad',fillOpacity:1,weight:2.5}}><Tooltip permanent direction="top" offset={[0,-10]}><b>NY–01</b> · {current?'POSITION FIX':'LAST VALID FIX'}<br/>{coordinate(position[0],true)}<br/>{coordinate(position[1],false)}</Tooltip></CircleMarker></>}
 <ScaleControl position="bottomleft" imperial={false}/>
 </MapContainer>
 <div className="marine-map-label"><span className="signal-dot"/>{d?.source==='DEMO'?'SIMULATED GNSS TRACK':'EXTERNAL GNSS TELEMETRY'}</div>
 <div className="map-layer-select"><label><Layers size={13}/><select aria-label="Map basemap" value={layer} onChange={e=>{setLayer(e.target.value);setTileError(false)}}><option value="world">World map</option><option value="ocean">Ocean bathymetry</option></select></label></div>
 <div className="cursor-coordinates"><Crosshair size={13}/>{cursor?`${coordinate(cursor[0],true)}  /  ${coordinate(cursor[1],false)}`:'Move over map to inspect coordinates'}</div>
 {tileError&&<div className="map-reference-note">Some map tiles are unavailable · Natural Earth reference coastline retained</div>}
 {polar&&<div className="map-warning">Position is outside Web Mercator’s ±85.0511° limit. Exact coordinates are retained below; no misleading clamped marker is shown.</div>}
 </div>
 <div className="marine-map-footer"><span><i className="orange-dot"/> NY–01 · {fixes.length.toLocaleString()} valid fixes</span><span>{follow?'Following telemetry':'World inspection mode'} · no independent marker animation</span><button onClick={()=>setFollow(!follow)} aria-pressed={follow}><Navigation size={12}/>{follow?'Follow on':'Follow off'}</button></div>
 {!large&&<div className="marine-position-strip"><div><span>LATITUDE</span><b>{coordinate(d?.navigation.latitude,true)}</b></div><div><span>LONGITUDE</span><b>{coordinate(d?.navigation.longitude,false)}</b></div><div><span>FIX STATUS</span><b>{current?'GNSS ACTIVE':'GPS UNAVAILABLE'}</b></div></div>}
 </section>
}
export function NavigationView({history,d}:{history:Telemetry[];d:Telemetry|null}){
 const fixes=history.filter(x=>x.source===d?.source&&valid(x));let distance=0,segments=0;
 for(let i=1;i<fixes.length;i++){const a=fixes[i-1],b=fixes[i];const dt=(Date.parse(b.timestamp)-Date.parse(a.timestamp))/1000;const meters=haversine([a.navigation.latitude!,a.navigation.longitude!],[b.navigation.latitude!,b.navigation.longitude!]);if(dt>0&&dt<=60&&meters/dt<=30){distance+=meters;segments++;}}
 const n=d?.navigation;
 return <><div className="navigation-intro"><div><span className="eyebrow">POSITION & GEOSPATIAL MONITORING</span><h2>One platform. A global perspective.</h2><p>Telemetry-driven positioning on a referenced world map. Inspect coordinates, follow the mission, or explore ocean bathymetry.</p></div><div className={'navigation-fix '+(n?.gps_fix?'':'lost')}><ShieldCheck size={21}/><span>{n?.gps_fix?'POSITION FIX ACQUIRED':'AWAITING VALID FIX'}<small>{d?.source==='DEMO'?'Sensor model · not a surveyed position':'WGS84 receiver output'}</small></span></div></div>
 <div className="navigation-stats"><div className="nav-coordinate"><span><MapPin size={14}/> LATITUDE</span><strong>{coordinate(n?.latitude,true)}</strong><small>{dms(n?.latitude,true)} <i>Signed: {n?.latitude?.toFixed(6)??'—'}</i></small></div><div className="nav-coordinate"><span><Globe2 size={14}/> LONGITUDE</span><strong>{coordinate(n?.longitude,false)}</strong><small>{dms(n?.longitude,false)} <i>Signed: {n?.longitude?.toFixed(6)??'—'}</i></small></div><div className="nav-coordinate"><span><Compass size={14}/> COURSE OVER GROUND</span><strong>{n?.heading?.toFixed(1)??'—'}<em>° TRUE</em></strong><small>{n?.speed?.toFixed(2)??'—'} m/s · {n?.speed!=null?(n.speed*1.943844).toFixed(2):'—'} knots</small></div><div className="nav-coordinate"><span><LocateFixed size={14}/> FIX METADATA</span><strong>{n?.satellites??'—'}<em>SATELLITES</em></strong><small>Reported accuracy ±{n?.accuracy?.toFixed(1)??'—'} m · {n?.gps_status??'LOST'}</small></div></div>
 <MarineMap history={history} d={d} large/>
 <div className="navigation-details"><section className="panel"><div className="panel-head"><h3>Position integrity</h3><span className="badge">WGS 84</span></div><div className="integrity-grid"><div><span>Coordinate reference</span><b>EPSG:4326 · decimal degrees</b></div><div><span>Basemap projection</span><b>EPSG:3857 · Web Mercator</b></div><div><span>Distance in loaded valid segments</span><b>{(distance/1000).toFixed(3)} km / {(distance/1852).toFixed(3)} nm</b></div><div><span>Position timestamp · UTC</span><b>{d?new Date(d.timestamp).toISOString().replace('T',' ').replace('Z',' UTC'):'No telemetry'}</b></div></div><p className="panel-note">Six decimal places preserve display precision; they do not imply centimetre-level GNSS accuracy. Track distance excludes gaps over 60 seconds and implausible jumps over 30 m/s. Antimeridian crossings are split for display.</p></section><section className="panel"><div className="panel-head"><h3>Recent position fixes</h3><span className="small muted">{segments} validated track segments</span></div><table className="position-table"><thead><tr><th>UTC TIME</th><th>LATITUDE</th><th>LONGITUDE</th></tr></thead><tbody>{fixes.slice(-5).reverse().map(f=><tr key={f.id}><td>{new Date(f.timestamp).toISOString().slice(11,19)}</td><td>{coordinate(f.navigation.latitude,true)}</td><td>{coordinate(f.navigation.longitude,false)}</td></tr>)}</tbody></table>{!fixes.length&&<p className="panel-note">No valid positions have been received.</p>}</section></div>
 <div className="notice"><Globe2 size={17}/> {d?.source==='DEMO'?'Demo coordinates are generated by a geodesic sensor model, not your browser location or real platform GPS.':'External coordinates are plotted as received; hardware authenticity and calibration must be verified.'} A lost fix preserves the last-known marker, not a fabricated new location.</div></>
}
