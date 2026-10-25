#!/usr/bin/env python3
"""Generate an UNTESTED Tableau Desktop workbook draft and portable TWBX.

Standard-library XML construction, informed by saved Tableau workbook examples.
XML/reference validation is not Tableau calculation compilation or interaction testing.
"""
from copy import deepcopy
import csv
import hashlib
import json
from pathlib import Path
import uuid
import xml.etree.ElementTree as ET
import zipfile

from prepare_tableau import prepare

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'tableau'
USER = 'http://www.tableausoftware.com/xml/user'
ET.register_namespace('user', USER)
TABLES = {'Totals':'state_totals','Vehicles':'vehicle_categories','Causes':'causes','Roads':'road_types'}
DASHBOARDS = ['1 National Overview','2 Two-Wheeler Safety','3 Causes and Risk Factors']
PARAMETERS = {
 'Year': ('string','2023',['All','2020','2021','2022','2023']),
 'State': ('string','All',[]),
 'Metric': ('string','Fatalities',['Accidents','Fatalities','Severity']),
 'Top N': ('integer',10,[5,10,15]),
 'High Severity Threshold': ('real',50,None),
 'Compare A': ('string','Kerala',[]),
 'Compare B': ('string','Tamil Nadu',[]),
}
FIELDS = {'Year':('integer','dimension','ordinal'),'State':('string','dimension','nominal'),
 'Category':('string','dimension','nominal'),'Accidents':('integer','measure','quantitative'),
 'Fatalities':('integer','measure','quantitative'),'Source ID':('string','dimension','nominal'),
 'Country':('string','dimension','nominal'),'Record Status':('string','dimension','nominal')}
# name -> (formula, datatype, aggregate, role)
CALCS = {
 'Year Filter': ("[Parameters].[Year] = 'All' OR STR([Year]) = [Parameters].[Year]",'boolean',False,'dimension'),
 'State Filter': ("[Parameters].[State] = 'All' OR [State] = [Parameters].[State]",'boolean',False,'dimension'),
 'Comparison Filter': ('[State] = [Parameters].[Compare A] OR [State] = [Parameters].[Compare B]','boolean',False,'dimension'),
 'Paired Accidents': ('IF NOT ISNULL([Accidents]) AND NOT ISNULL([Fatalities]) THEN [Accidents] END','integer',False,'measure'),
 'Paired Fatalities': ('IF NOT ISNULL([Accidents]) AND NOT ISNULL([Fatalities]) THEN [Fatalities] END','integer',False,'measure'),
 'Severity': ('IF SUM([Paired Accidents]) > 0 THEN 100.0 * SUM([Paired Fatalities]) / SUM([Paired Accidents]) END','real',True,'measure'),
 'Selected Measure': ("CASE [Parameters].[Metric] WHEN 'Accidents' THEN SUM([Accidents]) WHEN 'Fatalities' THEN SUM([Fatalities]) WHEN 'Severity' THEN [Severity] END",'real',True,'measure'),
 'Accidents Label': ("IF COUNT([Accidents]) = 0 THEN 'Unavailable' ELSE STR(SUM([Accidents])) END",'string',True,'measure'),
 'Fatalities Label': ("IF COUNT([Fatalities]) = 0 THEN 'Unavailable' ELSE STR(SUM([Fatalities])) END",'string',True,'measure'),
 'Severity Label': ("IF ISNULL([Severity]) THEN 'Unavailable: no compatible denominator' ELSE STR(ROUND([Severity],1)) + ' deaths / 100 accidents' END",'string',True,'measure'),
 'Reporting Status': ("IF ISNULL([Selected Measure]) THEN 'Unavailable: not reported for selected year/state/category, or denominator unavailable' ELSEIF ([Parameters].[Metric] = 'Accidents' AND COUNT([Accidents]) < COUNT([State])) OR ([Parameters].[Metric] = 'Fatalities' AND COUNT([Fatalities]) < COUNT([State])) OR ([Parameters].[Metric] = 'Severity' AND COUNT([Paired Accidents]) < COUNT([State])) THEN 'Partial coverage: reported/paired observations only' ELSE 'Reported observations in supplied extract' END",'string',True,'measure'),
 'Coverage Summary': ("'Accident observations: ' + STR(COUNT([Accidents])) + '/' + STR(COUNT([State])) + ' | Fatality observations: ' + STR(COUNT([Fatalities])) + '/' + STR(COUNT([State])) + ' | Severity uses paired counts only'",'string',True,'measure'),
 'Dynamic Title': ("[Parameters].[Year] + ' | ' + [Parameters].[State] + ' | ' + [Parameters].[Metric]",'string',False,'dimension'),
 'State Rank': ("RANK_UNIQUE([Selected Measure], 'desc')",'integer',True,'measure'),
 'Risk Class': ("IF COUNT([Paired Accidents]) < COUNT([State]) OR ISNULL([Severity]) THEN 'Unclassified: incomplete data' ELSEIF MIN(IIF([High Accidents AND High Severity],1,0))=1 THEN 'High accidents + high severity' ELSEIF MIN(IIF([High Accidents],1,0))=1 THEN 'High accidents' ELSEIF MIN(IIF([High Severity],1,0))=1 THEN 'High severity' ELSE 'Other reported' END",'string',True,'measure'),
 'Reset Label': ("'Reset filters'",'string',False,'dimension'),
 'Nav Overview': ("'National overview'",'string',False,'dimension'),
 'Nav Vehicles': ("'Two-wheeler safety'",'string',False,'dimension'),
 'Nav Risks': ("'Causes and risk factors'",'string',False,'dimension'),
}
RESET = {'Year':('2023','string'),'State':('All','string'),'Metric':('Fatalities','string'),
         'Top N':(10,'integer'),'High Severity Threshold':(50,'real'),
         'Compare A':('Kerala','string'),'Compare B':('Tamil Nadu','string')}
for key,(value,datatype) in RESET.items():
    CALCS['Reset '+key] = (repr(value) if datatype=='string' else str(value),datatype,False,'dimension')


def sub(parent, tag, text=None, **attrs):
    e = ET.SubElement(parent,tag,{k.replace('_','-'):str(v) for k,v in attrs.items()})
    if text is not None: e.text = str(text)
    return e


def q(value):
    return '"'+value.replace('"','""')+'"' if isinstance(value,str) else str(value)


def uid(parent):
    sub(parent,'simple-id',uuid='{'+str(uuid.uuid4()).upper()+'}')


def prepare_data():
    raw={}
    for caption,table in TABLES.items():
        with (ROOT/'data/input'/f'{table}.csv').open(newline='') as stream:
            raw[caption]=list(csv.DictReader(stream))
    states=sorted({r['state'] for r in raw['Totals']})
    for p in ('State','Compare A','Compare B'):
        dtype,default,_=PARAMETERS[p]
        PARAMETERS[p]=(dtype,default,(['All'] if p=='State' else [])+states)
    for caption,rows in raw.items():
        lookup={(r['year'],r['state'],r['category']):r for r in rows}
        if len(lookup)!=len(rows): raise ValueError('Duplicate reporting grain')
        categories=sorted({r['category'] for r in rows})
        path=OUT/'Data'/f'{caption}.csv'
        with path.open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=FIELDS,lineterminator='\n');writer.writeheader()
            for year in ('2020','2021','2022','2023'):
                for state in states:
                    for category in categories:
                        r=lookup.get((year,state,category))
                        writer.writerow({'Year':year,'State':state,'Category':category,
                         'Accidents':r['accidents'] if r else '', 'Fatalities':r['fatalities'] if r else '',
                         'Source ID':r['source_id'] if r else '', 'Country':'India',
                         'Record Status':'Source observation' if r else 'Not reported / not applicable'})
    return raw


def param_source(parent):
    ds=sub(parent,'datasource',name='Parameters',hasconnection='false',inline='true',version='18.1')
    sub(ds,'aliases',enabled='yes')
    for name,(dtype,default,members) in PARAMETERS.items():
        col=sub(ds,'column',caption=name,datatype=dtype,name=f'[{name}]',
                param_domain_type='list' if members else 'range',role='measure',
                type='nominal' if dtype=='string' else 'quantitative',value=q(default))
        sub(col,'calculation',formula=q(default),**{'class':'tableau'})
        if members:
            for v in members: sub(col.find('members') if col.find('members') is not None else sub(col,'members'),'member',value=q(v))
        else: sub(col,'range',min='0.0',max='1000.0',granularity='1.0')
    return ds


def make_source(parent,name):
    ds=sub(parent,'datasource',caption=name,inline='true',name=name,version='18.1')
    conn=sub(ds,'connection',directory='Data',filename=name+'.csv',server='',workgroup_auth_mode='as-is',**{'class':'textscan'})
    rel=sub(conn,'relation',name=name,table=f'[{name}#csv]',type='table')
    cols=sub(rel,'columns',character_set='UTF-8',header='yes',locale='en_US',separator=',')
    for i,(field,(dtype,_,_)) in enumerate(FIELDS.items()): sub(cols,'column',datatype=dtype,name=field,ordinal=i)
    sub(ds,'aliases',enabled='yes')
    for field,(dtype,role,typ) in FIELDS.items():
        attrs=dict(datatype=dtype,name=f'[{field}]',role=role,type=typ)
        if field=='State':attrs['semantic_role']='[State].[Name]'
        if field=='Country':attrs['semantic_role']='[Country].[Name]'
        sub(ds,'column',**attrs)
    for field,(formula,dtype,agg,role) in CALCS.items():
        typ='quantitative' if dtype in ('integer','real') else 'nominal'
        col=sub(ds,'column',caption=field,datatype=dtype,name=f'[{field}]',role=role,type=typ)
        sub(col,'calculation',formula=formula,**{'class':'tableau'})
    for name_ in ('High Accidents','High Severity','High Accidents AND High Severity'):
        g=sub(ds,'group',caption=name_,name=f'[{name_}]',name_style='unqualified')
        if name_=='High Accidents':
            gf=sub(g,'groupfilter',count='[Parameters].[Top N]',end='top',function='end',units='records')
            order=sub(gf,'groupfilter',direction='DESC',expression='SUM([Accidents])',function='order')
            sub(order,'groupfilter',function='level-members',level='[State]')
        elif name_=='High Severity':
            gf=sub(g,'groupfilter',expression='SUM([Paired Accidents]) > 0 AND COUNT([Paired Accidents]) = COUNT([State]) AND [Severity] >= [Parameters].[High Severity Threshold]',function='filter')
            sub(gf,'groupfilter',function='level-members',level='[State]')
        else:
            gf=sub(g,'groupfilter',function='intersection')
            for ref in ('High Accidents','High Severity'):sub(gf,'groupfilter',field=f'[{ref}]',function='reference')
    sem=sub(ds,'semantic-values');sub(sem,'semantic-value',key='[Country].[Name]',value='"India"')
    return ds


def instance(field):
    if field in FIELDS:
        dtype,role,typ=FIELDS[field];kind='sum' if role=='measure' else 'none'
    else:
        _,dtype,agg,role=CALCS[field];typ='quantitative' if dtype in ('integer','real') else 'nominal'
        kind='usr' if agg else 'sum' if role=='measure' else 'none'
    suffix='qk' if typ=='quantitative' and (role=='measure' or field not in FIELDS) else 'ok' if typ=='ordinal' else 'nk'
    # Non-aggregate constant dimensions are discrete even when integer-valued.
    if role=='dimension' and field not in FIELDS:suffix='nk'
    return f'[{kind}:{field}:{suffix}]',{'sum':'Sum','none':'None','usr':'User'}[kind],typ


def ref(ds,field):return f'[{ds}].{instance(field)[0]}'


def build():
    (OUT/'Data').mkdir(parents=True,exist_ok=True)
    prepare(ROOT/'data/input', ROOT/'data/tableau')
    raw=prepare_data()
    root=ET.Element('workbook',{'source-platform':'win','version':'18.1'})
    manifest=sub(root,'document-format-change-manifest')
    for tag in ('NavigationAction','ParameterAction','_.fcp.ParameterActionClearSelection.true...ParameterActionClearSelection'):
        sub(manifest,tag)
    preferences=sub(root,'preferences');sub(preferences,'preference',name='ui.encoding.shelf.height',value=24)
    style=sub(root,'style');rule=sub(style,'style-rule',element='worksheet');sub(rule,'format',attr='font-family',value='Arial');sub(rule,'format',attr='font-size',value=10)
    sources=sub(root,'datasources');params=param_source(sources);defs={k:make_source(sources,k) for k in TABLES}
    actions=sub(root,'actions');worksheets=sub(root,'worksheets');dashboards=sub(root,'dashboards');windows=sub(root,'windows')
    metadata={}

    def sheet(name,ds,kind,field=None,dimension=None,category=None,compare=False,top=False,color=None,controls=False,risk_members=False):
        w=sub(worksheets,'worksheet',name=name)
        title=sub(sub(w,'layout-options'),'title');text=sub(title,'formatted-text');sub(text,'run',text=name)
        if not controls:
            sub(text,'run',text=' | <Parameters.Year> | <Parameters.State> | <Parameters.Metric>',fontcolor='#667a7a',fontsize=9)
        table=sub(w,'table');view=sub(table,'view');dss=sub(view,'datasources')
        sub(dss,'datasource',name=ds,caption=ds);sub(dss,'datasource',name='Parameters')
        if kind=='map':sub(sub(view,'mapsources'),'mapsource',name='Tableau')
        pd=sub(view,'datasource-dependencies',datasource='Parameters')
        for c in params.findall('column'):pd.append(deepcopy(c))
        deps=sub(view,'datasource-dependencies',datasource=ds)
        for c in defs[ds].findall('column'):deps.append(deepcopy(c))
        for g in defs[ds].findall('group'):deps.append(deepcopy(g))
        for f in [*FIELDS,*CALCS]:
            inst,derivation,typ=instance(f)
            sub(deps,'column-instance',column=f'[{f}]',derivation=derivation,name=inst,pivot='key',type=typ)
        def filt(f,value,context=False):
            attributes={'class':'categorical','column':ref(ds,f)}
            if context:attributes['context']='true'
            el=ET.SubElement(view,'filter',attributes)
            sub(el,'groupfilter',function='member',level=instance(f)[0],member=value)
        if not controls:
            filt('Year Filter','true',True);filt('State Filter','true',True)
        if category:filt('Category',q(category),True)
        if compare:filt('Comparison Filter','true',True)
        if top:
            f=ET.SubElement(view,'filter',{'class':'categorical','column':ref(ds,'State')})
            gf=sub(f,'groupfilter',count='[Parameters].[Top N]',end='top',function='end',units='records')
            ordered=sub(gf,'groupfilter',direction='DESC',expression=CALCS['Selected Measure'][0],function='order')
            sub(ordered,'groupfilter',function='level-members',level=instance('State')[0])
        if risk_members:
            # Show every state in High Accidents OR High Severity (not Top-N by the selected measure).
            f=ET.SubElement(view,'filter',{'class':'categorical','column':ref(ds,'State')})
            gf=sub(f,'groupfilter',function='union')
            for set_name in ('High Accidents','High Severity'):sub(gf,'groupfilter',field=f'[{ds}].[{set_name}]',function='reference')
        if kind=='bars':sub(view,'sort',column=ref(ds,dimension),direction='DESC',using=ref(ds,field),**{'class':'computed'})
        sub(view,'aggregation',value='true')
        sub(table,'style')
        pane=sub(sub(table,'panes'),'pane',selection_relaxation_option='selection-relaxation-allow')
        sub(sub(pane,'view'),'breakdown',value='auto')
        sub(pane,'mark',**{'class':{'bars':'Bar','line':'Line','map':'Multipolygon','text':'Text'}[kind]})
        enc=sub(pane,'encodings')
        if kind=='text':sub(enc,'text',column=ref(ds,field))
        if kind=='bars':sub(enc,'text',column=ref(ds,field))
        if color:sub(enc,'color',column=ref(ds,color))
        if kind=='map':
            for f in ('Country','State'):sub(enc,'lod',column=ref(ds,f))
            sub(enc,'color',column=ref(ds,'Selected Measure'))
            sub(enc,'geometry',column=f'[{ds}].[Geometry (generated)]')
        if kind=='line' and compare:sub(enc,'color',column=ref(ds,'State'))
        if controls and name=='Reset':
            for k in RESET:sub(enc,'lod',column=ref(ds,'Reset '+k))
        if not controls:
            for f in ('Accidents','Fatalities','Severity','Reporting Status','Coverage Summary'):sub(enc,'lod',column=ref(ds,f))
            tip=sub(sub(pane,'customized-tooltip'),'formatted-text')
            for label,f in [('Accidents','Accidents'),('Fatalities','Fatalities'),('Severity (deaths / 100 accidents)','Severity'),('Status','Reporting Status'),('Coverage','Coverage Summary')]:
                sub(tip,'run',text=label+': <'+ref(ds,f)+'>\n')
            if kind in ('map','bars') and (dimension=='State' or kind=='map'):
                sub(tip,'run',text='State: <'+ref(ds,'State')+'>\n')
            sub(tip,'run',text='Year: <Parameters.Year> | State filter: <Parameters.State> | Measure: <Parameters.Metric>')
        ps=sub(pane,'style');mr=sub(ps,'style-rule',element='mark')
        sub(mr,'format',attr='mark-color',value='#087e75');sub(mr,'format',attr='mark-labels-show',value='true')
        if kind=='text':
            sub(mr,'format',attr='font-size',value=22 if 'KPI' in name else 10)
        if color=='Risk Class':
            en=sub(mr,'encoding',attr='color',field=ref(ds,color),type='palette',**{'class':'0'})
            for label,hexcolor in [('High accidents + high severity','#c26333'),('High accidents','#d5a267'),('High severity','#9d6f9d'),('Other reported','#087e75'),('Unclassified: incomplete data','#9ca7a2')]:
                m=sub(en,'map',to=hexcolor);sub(m,'bucket',text=q(label))
        rows=ref(ds,dimension) if kind=='bars' else ref(ds,field) if kind=='line' else f'[{ds}].[Latitude (generated)]' if kind=='map' else ''
        cols=ref(ds,field) if kind=='bars' else ref(ds,'Year') if kind=='line' else f'[{ds}].[Longitude (generated)]' if kind=='map' else ''
        sub(table,'rows',text=rows);sub(table,'cols',text=cols);uid(w)
        win=sub(windows,'window',name=name,maximized='true',**{'class':'worksheet'})
        cards=sub(win,'cards');edge=sub(cards,'edge',name='right');strip=sub(edge,'strip',size=190)
        for p in PARAMETERS:sub(strip,'card',type='parameter',mode='compact',param=f'[Parameters].[{p}]')
        uid(win)
        metadata[name]={'source':ds,'kind':kind,'top_n':top,'category':category,'controls':controls,'risk_members':risk_members}
        return name

    for name,label in [('Nav Overview','Nav Overview'),('Nav Vehicles','Nav Vehicles'),('Nav Risks','Nav Risks'),('Reset','Reset Label')]:
        sheet(name,'Totals','text',field=label,controls=True)
    for ds,prefix in [('Totals','National'),('Vehicles','Two-Wheeler')]:
        cat='Two-wheelers' if ds=='Vehicles' else None
        for measure in ('Accidents','Fatalities','Severity'):
            sheet(f'{prefix} {measure} KPI',ds,'text',field=measure+' Label',category=cat)
        sheet(prefix+' Coverage',ds,'text',field='Coverage Summary',category=cat)
        sheet(prefix+' Availability',ds,'text',field='Reporting Status',category=cat)
        sheet(prefix+' State Ranking',ds,'bars',field='Selected Measure',dimension='State',category=cat,top=True)
        sheet(prefix+' Trend',ds,'line',field='Selected Measure',category=cat)
    sheet('India State Map','Totals','map')
    sheet('Road-User Category Comparison','Vehicles','bars',field='Selected Measure',dimension='Category')
    sheet('Two-State Historical Comparison','Vehicles','line',field='Selected Measure',category='Two-wheelers',compare=True)
    sheet('Reported Traffic Violations','Causes','bars',field='Selected Measure',dimension='Category')
    sheet('Traffic Violation Availability','Causes','text',field='Reporting Status')
    sheet('Road-Type Comparison','Roads','bars',field='Selected Measure',dimension='Category')
    sheet('Road-Type Availability','Roads','text',field='Reporting Status')
    sheet('Combined Risk Ranking','Totals','bars',field='Selected Measure',dimension='State',color='Risk Class',risk_members=True)

    def action_parameter(caption,source,field,target,clear=False):
        a=sub(actions,'edit-parameter-action',caption=caption,name='[Action_'+str(uuid.uuid4()).replace('-','')+']')
        sub(a,'activation',type='on-select');sub(a,'source',type='sheet',worksheet=source)
        sub(a,'agg-type',type='none')
        if clear:sub(a,'_.fcp.ParameterActionClearSelection.true...clear-option',type='assign-fixed-value',value='s:3:All')
        pr=sub(a,'params');sub(pr,'param',name='source-field',value=ref(metadata[source]['source'],field));sub(pr,'param',name='target-parameter',value=f'[Parameters].[{target}]')
    for source in ('India State Map','National State Ranking','Two-Wheeler State Ranking','Combined Risk Ranking'):
        action_parameter('Select state globally — '+source,source,'State','State',True)
    for target in RESET:action_parameter('Reset '+target,'Reset','Reset '+target,target)
    for source,target in zip(('Nav Overview','Nav Vehicles','Nav Risks'),DASHBOARDS):
        a=sub(actions,'nav-action',caption='Open '+target,name='[Navigation_'+str(uuid.uuid4()).replace('-','')+']')
        sub(a,'activation',type='on-select');sub(a,'source',type='sheet',worksheet=source)
        sub(sub(a,'params'),'param',name='sheet',value=target)
    # Action dependencies are local identifiers, not credentials or server bindings.
    adss=sub(actions,'datasources');sub(adss,'datasource',name='Totals',caption='Totals');sub(adss,'datasource',name='Vehicles',caption='Vehicles')
    for ds in ('Totals','Vehicles'):
        dep=sub(actions,'datasource-dependencies',datasource=ds)
        for field in ('State',*[f'Reset {p}' for p in RESET]):
            dep.append(deepcopy(next(c for c in defs[ds].findall('column') if c.get('name')==f'[{field}]')))

    def dashboard(name,index):
        d=sub(dashboards,'dashboard',name=name);sub(d,'style');sub(d,'size',maxheight=800,maxwidth=1200,minheight=800,minwidth=1200)
        zones=sub(d,'zones');layout=sub(zones,'zone',h=100000,w=100000,x=0,y=0,id=1,type_v2='layout-basic')
        n=1
        def zone(x,y,w,h,sheet_name=None,text=None,param=None):
            nonlocal n;n+=1
            attrs=dict(id=n,x=x,y=y,w=w,h=h)
            if sheet_name:attrs.update(name=sheet_name,show_title='false' if sheet_name.startswith(('Nav ','Reset')) else 'true')
            if text:attrs['type_v2']='text'
            if param:attrs.update(type_v2='paramctrl',param=f'[Parameters].[{param}]',mode='compact')
            z=sub(layout,'zone',**attrs)
            if text:sub(sub(z,'formatted-text'),'run',text=text,fontcolor='#173f3a',fontsize=12)
            zs=sub(z,'zone-style')
            for attr,value in [('border-style','none'),('margin','5'),('background-color','#ffffff')]:sub(zs,'format',attr=attr,value=value)
            return z
        zone(1000,500,98000,6500,text='RoadLens India | '+name+' | DRAFT — verify in Tableau Desktop')
        for i,sn in enumerate(('Nav Overview','Nav Vehicles','Nav Risks','Reset')):zone(1000+i*24500,7000,24500,4500,sn)
        for i,p in enumerate(('Year','State','Metric','Top N','High Severity Threshold')):zone(1000+i*19600,12000,19600,6500,param=p)
        prefix='Two-Wheeler' if index==1 else 'National'
        for i,m in enumerate(('Accidents','Fatalities','Severity')):zone(1000+i*32666,19500,32666,10500,f'{prefix} {m} KPI')
        zone(1000,30000,98000,4500,prefix+' Coverage')
        if index==0:
            zone(1000,34500,49000,37000,'India State Map');zone(50500,34500,48500,37000,'National State Ranking')
            zone(1000,72000,98000,18000,'National Trend');zone(1000,90000,98000,4500,'National Availability')
        elif index==1:
            zone(1000,34500,49000,27500,'Two-Wheeler State Ranking');zone(50500,34500,48500,27500,'Road-User Category Comparison')
            zone(1000,62500,24000,6500,param='Compare A');zone(26000,62500,24000,6500,param='Compare B')
            zone(1000,69500,98000,20000,'Two-State Historical Comparison');zone(1000,90000,98000,4500,'Two-Wheeler Availability')
        else:
            zone(1000,34500,49000,25500,'Reported Traffic Violations');zone(50500,34500,48500,25500,'Road-Type Comparison')
            zone(1000,60000,49000,5000,'Traffic Violation Availability');zone(50500,60000,48500,5000,'Road-Type Availability')
            zone(1000,65500,98000,28500,'Combined Risk Ranking')
        zone(1000,95000,98000,4500,text='MoRTH 2022/2023 reports | Severity = deaths / 100 paired accidents | All years aggregates counts | Missing data is unavailable | Select All years for trends')
        uid(d)
        win=sub(windows,'window',name=name,maximized='true',**{'class':'dashboard'});vp=sub(win,'viewpoints')
        for z in layout.findall('zone'):
            if z.get('name'):sub(vp,'viewpoint',name=z.get('name'))
        sub(win,'active',id='2');uid(win)
    for i,name in enumerate(DASHBOARDS):dashboard(name,i)
    ET.indent(root,space='  ')
    path=OUT/'RoadLens-India-DRAFT.twb';ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)
    report={'status':'DRAFT — NOT OPENED OR TESTED IN TABLEAU','workbook':path.name,
            'tableau_version_target':'Modern Tableau Desktop/Public; XML version 18.1 (compatibility unverified)',
            'dashboards':DASHBOARDS,'worksheets':metadata,'parameters':list(PARAMETERS),
            'sources':list(TABLES),'validation_scope':'XML syntax, internal references, packaged CSV paths and counts only',
            'input_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'data/input').glob('*')) if p.is_file()},
            'manual_verification':['Open/save in Tableau; repair any version-specific XML validation errors','Compile every calculation and resolve geographic roles/locations','Verify dashboard controls, parameter actions, Top-N tie behavior, context filters and sets','Verify map/tooltip/nav/reset/state comparison and device readability','Confirm source sums and missing slices; publish and test published workbook']}
    (OUT/'build-manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    package=OUT/'RoadLens-India-DRAFT.twbx'
    with zipfile.ZipFile(package,'w',compression=zipfile.ZIP_DEFLATED) as z:
        z.write(path,path.name)
        for p in sorted((OUT/'Data').glob('*.csv')):z.write(p,p.relative_to(OUT).as_posix())
    print(f'Generated {len(metadata)} worksheets, {len(DASHBOARDS)} dashboards, {len(PARAMETERS)} parameters; Tableau testing NOT RUN')
    print(package)
    return root

if __name__=='__main__':build()
