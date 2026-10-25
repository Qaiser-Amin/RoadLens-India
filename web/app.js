import {DEFAULTS,filterRows,aggregate,group,riskTable} from './analytics.js';
const $=id=>document.getElementById(id);
const fmt=(n,metric='')=>n===null||n===undefined?'Unavailable':new Intl.NumberFormat('en-IN',{maximumFractionDigits:metric==='severity'?1:0}).format(n);
const names={accidents:'Accidents',fatalities:'Fatalities',severity:'Severity'};
const unit=metric=>metric==='severity'?'Deaths per 100 accidents':'Reported '+metric;
const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let state=structuredClone(DEFAULTS),data,geography;
const palette=['#087e75','#d07b48','#5671aa','#a0709c','#9a903e','#6b9793'];
function period(){return state.year==='all'?'2020–2023':state.year}
function selectedLabel(){return state.states.length?state.states.join(', '):'All states & UTs'}
function mainRows(){return state.tab==='twowheelers'?filterRows(data.vehicle_categories,state,'Two-wheelers'):filterRows(data.state_totals,state)}
function panel(title,subtitle,body,wide=false,tag=''){return `<section class="panel ${wide?'wide':''}"><div class="panelhead"><div><h2>${title}</h2><p>${subtitle}</p></div>${tag?`<span class="tag">${tag}</span>`:''}</div>${body}</section>`}
function coverage(stats,metric){
 if(stats[metric]===null)return metric==='severity'?'Unavailable: no compatible accident denominator':'Unavailable: not reported for this selection';
 const count=metric==='severity'?stats.pairs:stats[metric+'Count'];
 return count<stats.rows?`Partial coverage · ${count}/${stats.rows} reported observations`:`${stats.rows} reported observations${metric==='severity'?' · paired counts':''}`;
}
function kpis(rows){const stats=aggregate(rows);$('kpis').innerHTML=['accidents','fatalities','severity'].map((m,i)=>`<article class="kpi" data-kpi="${m}"><span class="kpi-icon">${['↗','◎','△'][i]}</span><span class="label">${m==='severity'?'ACCIDENT SEVERITY':state.tab==='twowheelers'?'TWO-WHEELER '+names[m].toUpperCase():'REPORTED '+names[m].toUpperCase()}</span><strong>${fmt(stats[m],m)}</strong><small class="${stats[m]===null?'warning':''}">${escape(coverage(stats,m))}</small>${m==='severity'?'<div class="hint muted">Deaths per 100 reported accidents</div>':''}</article>`).join('')}
function bars(rows,key='state',metric=state.metric,limit=state.topN){const groups=group(rows,key,metric).filter(r=>r.value!==null).slice(0,limit);if(!groups.length)return '<div class="empty">This measure is unavailable for the selected year, state or category.<br>No values have been substituted.</div>';const max=Math.max(...groups.map(r=>r.value),1);return `<div class="bars">${groups.map((r,i)=>`<div class="barrow" title="${escape(r.name)}: ${fmt(r.value,metric)} · ${escape(coverage(r.stats,metric))}"><button ${key==='state'?`data-select-state="${escape(r.name)}"`:''}>${key==='state'?`${String(i+1).padStart(2,'0')} · `:''}${escape(r.name)}</button><div class="track"><div class="fill" style="width:${100*r.value/max}%"></div></div><span class="value">${fmt(r.value,metric)}</span></div>`).join('')}</div>`}
function trend(rows,compare=false){
 const years=(state.year==='all'?[2020,2021,2022,2023]:[Number(state.year)]);
 const selected=compare&&state.states.length?state.states:['Reported total'];
 const series=selected.map((name,i)=>({name,color:palette[i%palette.length],values:years.map(y=>({year:y,...aggregate(rows.filter(r=>r.year===y&&(name==='Reported total'||r.state===name)))}))}));
 const values=series.flatMap(s=>s.values.map(v=>v[state.metric])).filter(v=>v!==null);
 if(!values.length)return '<div class="empty">Historical values for this measure are unavailable in the selected reporting window.</div>';
 const width=window.innerWidth<600?360:840;
 const max=Math.max(...values,1)*1.15,x=i=>years.length===1?width/2:65+i*(width-110)/(years.length-1),y=v=>170-140*v/max;
 let lines='';for(let t=0;t<=3;t++){const v=t*max/3;lines+=`<line x1="65" x2="${width-45}" y1="${y(v)}" y2="${y(v)}" stroke="#e5eeea"/><text x="52" y="${y(v)+4}" text-anchor="end">${fmt(v,state.metric)}</text>`}
 for(const s of series){let previous=null;s.values.forEach((v,i)=>{const val=v[state.metric];if(val===null){previous=null;return}if(previous!==null)lines+=`<line x1="${x(previous.i)}" y1="${y(previous.val)}" x2="${x(i)}" y2="${y(val)}" stroke="${s.color}" stroke-width="2.5"/>`;lines+=`<circle cx="${x(i)}" cy="${y(val)}" r="4" fill="${s.color}" tabindex="0"><title>${escape(s.name)} · ${v.year}: ${fmt(val,state.metric)}</title></circle>`;previous={i,val}})}
 return `<div class="trend-legend">${series.map(s=>`<span><i class="dot" style="background:${s.color}"></i>${escape(s.name)}</span>`).join('')}</div><svg class="trend" viewBox="0 0 ${width} 210" role="img" aria-label="${names[state.metric]} trend for ${period()}">${lines}${years.map((v,i)=>`<text x="${x(i)}" y="200" text-anchor="middle">${v}</text>`).join('')}</svg><p class="hint">${years.length===1?'A single reporting year is selected. Choose “All years” to explore the historical trend.':'Gaps indicate unreported data. Severity uses paired observations, not an average of state rates.'}</p>`;
}
function mapMarkup(rows){
 const groups=group(rows,'state',state.metric),max=Math.max(...groups.map(r=>r.value??0),1),lookup=new Map(groups.map(r=>[r.name,r]));
 const point=([lon,lat])=>[30+(lon-67)*11.5,405-(lat-6)*12.4];
 const ring=coords=>coords.map((p,i)=>`${i?'L':'M'}${point(p).map(v=>v.toFixed(2)).join(',')}`).join('')+'Z';
 const paths=geography.features.map(f=>{const name=f.properties.name,entry=lookup.get(name),v=entry?.value;const t=v===undefined||v===null?null:v/max;const color=t===null?'#e5e9e7':`rgb(${Math.round(228-220*t)},${Math.round(241-115*t)},${Math.round(237-120*t)})`;const polygons=f.geometry.type==='Polygon'?[f.geometry.coordinates]:f.geometry.coordinates;return `<path d="${polygons.map(p=>p.map(ring).join('')).join('')}" fill="${color}" fill-rule="evenodd" data-map-state="${escape(name)}" class="${state.states.includes(name)?'selected':''}" tabindex="0" role="button" aria-label="Select ${escape(name)}"><title>${escape(name)} · ${names[state.metric]}: ${fmt(v,state.metric)}</title></path>`}).join('');
 return `<svg viewBox="0 0 450 430" class="map" aria-label="Interactive India state map">${paths}</svg><div class="legend"><span>Lower</span><span class="gradient"></span><span>Higher ${names[state.metric].toLowerCase()}</span><span>· Gray: unavailable</span></div><p class="map-footnote">Click or focus a state and press Enter to filter all dashboards. Illustrative current boundaries; not a historical or official boundary map.</p>`;
}
function render(){
 const titles={overview:['National overview','Every journey deserves a safer road.','Explore the patterns behind India’s reported road accidents.'],twowheelers:['Two-wheeler safety','A closer look at life on two wheels.','Compare reported two-wheeler fatalities across states and years.'],risks:['Causes & risk factors','Understand where risk concentrates.','Explore reported violations, road types and intersecting risk indicators.']};
 const [section,title,subtitle]=titles[state.tab];$('heading').textContent=title;$('subtitle').textContent=subtitle;$('sectionlabel').textContent=section.toUpperCase();$('selection').textContent=`${period()} / ${selectedLabel()} / ${names[state.metric]}`;
 document.querySelectorAll('nav button').forEach(b=>{b.classList.toggle('active',b.dataset.tab===state.tab);b.setAttribute('aria-current',b.dataset.tab===state.tab?'page':'false')});
 $('stateSummary').textContent=state.states.length===1?state.states[0]:state.states.length?`${state.states.length} states selected`:'All states & UTs';
 document.querySelectorAll('[data-state-check]').forEach(c=>c.checked=state.states.includes(c.value));
 const rows=mainRows();kpis(rows);
 if(state.tab==='overview'){$('dashboard').innerHTML=`<div class="grid">${panel('The geography of road safety',`${names[state.metric]} · ${period()} · ${selectedLabel()}`,mapMarkup(rows),false,'STATE MAP')}${panel(`Top ${state.topN} states & UTs`,`${unit(state.metric)} · ${period()} · current selection`,bars(rows))}${panel('How the pattern changes',`${names[state.metric]} · ${period()} · ${selectedLabel()}`,trend(rows),true)}</div>`}
 if(state.tab==='twowheelers'){$('dashboard').innerHTML=`<div class="grid">${panel(`Top ${state.topN} two-wheeler states`,`${names[state.metric]} · ${period()} · ${selectedLabel()}`,bars(rows),false,'ROAD USERS')}${panel('Compare road-user categories',`${unit(state.metric)} · ${period()} · includes pedestrians`,bars(filterRows(data.vehicle_categories,state),'category',state.metric,20)+`<p class="hint">Official road-user categories, not impacting-vehicle types. Some Kerala “Other” figures are included in Pedestrians in 2023.</p>`)}${panel('Two-wheeler trends & state comparison',`${names[state.metric]} · ${period()} · select multiple states in the global state control`,trend(rows,true),true)}</div>`}
 if(state.tab==='risks'){
 const ranked=riskTable(rows,state);
 $('dashboard').innerHTML=`<div class="grid">${panel('Reported traffic-rule violations',`${names[state.metric]} · ${period()} · ${selectedLabel()}`,bars(filterRows(data.causes,state),'category',state.metric,20))}${panel('Compare road types',`${names[state.metric]} · ${period()} · ${selectedLabel()}`,bars(filterRows(data.road_types,state),'category',state.metric,20))}${panel('Where high accidents meet high severity',`Top ${state.topN} accident states ∩ severity ≥ ${state.threshold} · ${period()} · ${selectedLabel()}`,`<label class="threshold">Severity threshold <input id="threshold" type="number" min="0" max="1000" step="1" value="${state.threshold}"> deaths / 100 accidents</label><p class="hint">All states in either set are listed, with the intersection first. Context: selected year(s) and states. Complete paired observations required. Multi-year classification uses pooled counts. This is an exploratory rule.</p><div class="risk-table"><table><thead><tr><th>STATE / UT</th><th>ACCIDENTS</th><th>SEVERITY</th><th>HIGH ACCIDENTS</th><th>HIGH SEVERITY</th><th>INTERSECTION</th></tr></thead><tbody>${ranked.map(r=>`<tr><td><button class="textbutton" data-select-state="${escape(r.name)}">${escape(r.name)}</button></td><td>${fmt(r.stats.accidents)}</td><td>${fmt(r.stats.severity,'severity')}</td><td>${r.highAccidents?'In set':'—'}</td><td>${r.highSeverity?'In set':'—'}</td><td><span class="risk-pill ${r.risk==='Combined high risk'?'risk-high':''}">${r.risk}</span></td></tr>`).join('')}</tbody></table></div>`,true)}</div>`;
 $('threshold').onchange=e=>{const n=Number(e.target.value);if(Number.isFinite(n)&&n>=0&&n<=1000){state.threshold=n;render()}};
 }
 document.querySelectorAll('[data-select-state]').forEach(b=>b.onclick=()=>selectState(b.dataset.selectState));
 document.querySelectorAll('[data-map-state]').forEach(p=>{p.onclick=()=>selectState(p.dataset.mapState);p.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();selectState(p.dataset.mapState)}};p.onpointermove=e=>{const name=p.dataset.mapState,stats=aggregate(rows.filter(r=>r.state===name));$('tooltip').innerHTML=`<b>${escape(name)}</b><br>${period()} · ${names[state.metric]}: ${fmt(stats[state.metric],state.metric)}<br>Accidents: ${fmt(stats.accidents)}<br>Fatalities: ${fmt(stats.fatalities)}<br>Severity: ${fmt(stats.severity,'severity')}<br>${escape(coverage(stats,state.metric))}`;$('tooltip').hidden=false;$('tooltip').style.left=Math.min(e.clientX+14,window.innerWidth-300)+'px';$('tooltip').style.top=Math.min(e.clientY+14,window.innerHeight-190)+'px'};p.onpointerleave=()=>{$('tooltip').hidden=true}});
}
function selectState(name){state.states=state.states.length===1&&state.states[0]===name?[]:[name];$('tooltip').hidden=true;render()}
async function init(){
 try{
 const [response,map]=await Promise.all([fetch('/api/data'),fetch('/assets/india-states.geojson')]);if(!response.ok||!map.ok)throw new Error('Source loading failed');data=await response.json();geography=await map.json();
 const states=[...new Set(data.state_totals.map(r=>r.state))].sort();$('stateChecks').innerHTML=states.map(s=>`<label><input type="checkbox" data-state-check value="${escape(s)}">${escape(s)}</label>`).join('');
 document.querySelectorAll('[data-state-check]').forEach(c=>c.onchange=()=>{state.states=[...document.querySelectorAll('[data-state-check]:checked')].map(e=>e.value);render()});
 $('stateSearch').oninput=e=>{document.querySelectorAll('#stateChecks label').forEach(l=>l.hidden=!l.textContent.toLowerCase().includes(e.target.value.toLowerCase()))};
 $('allStates').onclick=()=>{state.states=[];render()};
 ['year','metric','topN'].forEach(id=>$(id).onchange=e=>{state[id]=id==='topN'?Number(e.target.value):e.target.value;render()});
 document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{state.tab=b.dataset.tab;render()});
 $('reset').onclick=()=>{state=structuredClone(DEFAULTS);['year','metric','topN'].forEach(k=>$(k).value=state[k]);$('stateSearch').value='';document.querySelectorAll('#stateChecks label').forEach(l=>l.hidden=false);$('statePicker').open=false;render()};
 $('download').onclick=()=>{location.href='/api/download?table='+({overview:'state_totals',twowheelers:'vehicle_categories',risks:'causes'}[state.tab])};
 $('sourcesBtn').onclick=()=>$('sourceDialog').showModal();$('sourceBadgeBtn').onclick=()=>$('sourceDialog').showModal();$('closeSources').onclick=()=>$('sourceDialog').close();
 $('sourceLinks').innerHTML='<h3>Official source reports</h3>'+[...new Map(data.sources.map(s=>[s.url,s])).values()].map(s=>`<p><a target="_blank" rel="noopener" href="${escape(s.url)}">${escape(s.title)} ↗</a></p>`).join('');
 window.addEventListener('resize',()=>{clearTimeout(window.roadlensResize);window.roadlensResize=setTimeout(render,100)});
 render();
 }catch(e){$('dashboard').innerHTML='<div class="empty">The verified data could not be loaded. Start this app with python server.py and reload.</div>';console.error(e)}
}
init();
