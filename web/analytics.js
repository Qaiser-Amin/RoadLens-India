export const DEFAULTS = {year:'2023',states:[],metric:'fatalities',topN:10,threshold:50,tab:'overview'};
export function filterRows(rows, s, category=null) {
 return rows.filter(r=>(s.year==='all'||r.year===Number(s.year))&&(!s.states.length||s.states.includes(r.state))&&(!category||r.category===category));
}
export function aggregate(rows) {
 const sum=k=>{const v=rows.filter(r=>r[k]!==null);return v.length?v.reduce((a,r)=>a+r[k],0):null};
 const pairs=rows.filter(r=>r.accidents!==null&&r.fatalities!==null);
 const denominator=pairs.reduce((a,r)=>a+r.accidents,0);
 return {accidents:sum('accidents'),fatalities:sum('fatalities'),severity:denominator>0?100*pairs.reduce((a,r)=>a+r.fatalities,0)/denominator:null,
  accidentsCount:rows.filter(r=>r.accidents!==null).length,fatalitiesCount:rows.filter(r=>r.fatalities!==null).length,
  pairs:pairs.length,rows:rows.length};
}
export function group(rows,key,metric) {
 const groups=new Map();for(const row of rows){if(!groups.has(row[key]))groups.set(row[key],[]);groups.get(row[key]).push(row)}
 return [...groups].map(([name,rows])=>({name,value:aggregate(rows)[metric],stats:aggregate(rows)})).sort((a,b)=>(b.value??-Infinity)-(a.value??-Infinity)||String(a.name).localeCompare(String(b.name)));
}
export function riskStates(rows,s) {
 const accidents=group(rows,'state','accidents').filter(r=>r.value!==null).slice(0,s.topN);
 const highAccidents=new Set(accidents.map(r=>r.name));
 return group(rows,'state',s.metric).map(r=>{
 const complete=r.stats.pairs===r.stats.rows&&r.stats.severity!==null;
 const highSeverity=complete&&r.stats.severity>=s.threshold;
 return {...r,highAccidents:highAccidents.has(r.name),highSeverity,
  risk:!complete?'Unclassified':highAccidents.has(r.name)&&highSeverity?'Combined high risk':highSeverity?'High severity':highAccidents.has(r.name)?'High accidents':'Other reported'};
 });
}
