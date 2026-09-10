import streamlit as st
import pandas as pd
import json, sqlite3, uuid
from pathlib import Path
from datetime import date, datetime

st.set_page_config(page_title='Perenco UK CoW Assurance', page_icon='✓', layout='wide')
BASE=Path(__file__).parent
QUESTIONS=json.loads((BASE/'questions.json').read_text(encoding='utf-8'))
DB=BASE/'assurance_uat.db'

def connect():
    c=sqlite3.connect(DB)
    c.execute('CREATE TABLE IF NOT EXISTS audits (audit_id TEXT PRIMARY KEY, submitted_at TEXT, form_name TEXT, audit_date TEXT, site TEXT, auditor TEXT, reference TEXT, metadata TEXT, responses TEXT, summary TEXT)')
    c.commit(); return c

def save(form_name, meta, responses, summary=''):
    aid='PUK-'+datetime.now().strftime('%Y%m%d')+'-'+uuid.uuid4().hex[:6].upper()
    c=connect(); c.execute('INSERT INTO audits VALUES (?,?,?,?,?,?,?,?,?,?)',(aid,datetime.now().isoformat(timespec='seconds'),form_name,meta.get('audit_date',''),meta.get('site',''),meta.get('auditor',''),meta.get('reference',''),json.dumps(meta),json.dumps(responses),summary)); c.commit(); c.close(); return aid

def questions(form_key, options):
    out=[]; section=None
    for q in QUESTIONS[form_key]:
        if q['section'] != section:
            section=q['section']; st.subheader(section)
        st.markdown('**'+q['question']+'**')
        answer=st.radio('Response',options,index=None,horizontal=True,key='r-'+form_key+q['id'],label_visibility='collapsed')
        comment=st.text_area('Comments / Evidence',key='c-'+form_key+q['id'],height=65)
        out.append({'question_id':q['id'],'section':q['section'],'question':q['question'],'response':answer,'comments_evidence':comment})
    return out

def missing(rs): return [x for x in rs if x['response'] is None]

st.title('PERENCO UK')
st.caption('Control of Work Assurance — UAT')
page=st.sidebar.radio('Select form',['Permit Quality','Toolbox Talk / Permit / POP','Leadership Engagement','Submitted Audits','Dashboard Export'])

if page=='Permit Quality':
    st.header('SELF VERIFICATION – LEVEL 4 MONITORING — PTW')
    a,b,c=st.columns(3); site=a.text_input('SITE/INSTALLATION'); ad=b.date_input('DATE OF AUDIT:',date.today()); auditor=c.text_input('OOE NAME:')
    a,b,c=st.columns(3); ref=a.text_input('WCC NUMBER:'); nw=b.selectbox('NEW WCC:',['','Yes','No','N/A']); nr=c.selectbox('NEW ROUTINE:',['','Yes','No','N/A'])
    rs=questions('Level 4 Monitoring – PTW',['Yes','No','N/A'])
    if st.button('Submit PTW Monitoring',type='primary',use_container_width=True):
        if not site or not auditor: st.error('Complete SITE/INSTALLATION and OOE NAME.')
        elif missing(rs): st.error(f'Please answer all questions. {len(missing(rs))} blank response(s).')
        else: st.success('Submitted: '+save('Level 4 Monitoring – PTW',{'site':site,'audit_date':str(ad),'auditor':auditor,'reference':ref,'NEW WCC':nw,'NEW ROUTINE':nr},rs))

elif page=='Toolbox Talk / Permit / POP':
    st.header('SELF VERIFICATION – LEVEL 4 MONITORING — TOOLBOX TALK')
    a,b,c=st.columns(3); site=a.text_input('SITE/INSTALLATION'); ad=b.date_input('DATE OF AUDIT:',date.today()); auditor=c.text_input('HSEA / OTL:')
    a,b,c=st.columns(3); ref=a.text_input('WCC / POPS NUMBER:'); nw=b.selectbox('NEW WCC:',['','Yes','No','N/A']); nr=c.selectbox('NEW ROUTINE:',['','Yes','No','N/A'])
    rs=questions('Level 4 Monitoring – Toolbox Talk',['Yes','No','N/A'])
    if st.button('Submit Toolbox Talk Monitoring',type='primary',use_container_width=True):
        if not site or not auditor: st.error('Complete SITE/INSTALLATION and HSEA / OTL.')
        elif missing(rs): st.error(f'Please answer all questions. {len(missing(rs))} blank response(s).')
        else: st.success('Submitted: '+save('Level 4 Monitoring – Toolbox Talk',{'site':site,'audit_date':str(ad),'auditor':auditor,'reference':ref,'NEW WCC':nw,'NEW ROUTINE':nr},rs))

elif page=='Leadership Engagement':
    st.header('Control of Work Leadership Engagement Checklist')
    a,b=st.columns(2); ad=a.date_input('Date',date.today()); site=b.text_input('Location / Team (add W2W N/S or Flying N/S)')
    a,b=st.columns(2); sc=a.text_input('Site Controller'); leader=b.text_input('Leadership Representative')
    st.write('Purpose: This checklist provides a predefined set of Control of Work questions for leadership engagement visits. It supports visible leadership, workforce engagement and assurance discussions covering permit quality, hazard awareness, implementation of controls, supervision, Stop the Job culture and learning opportunities.')
    rs=questions('Leadership Engagement',['Yes','No'])
    st.subheader('Summary')
    positive=st.text_area('Positive Observations'); improvement=st.text_area('Opportunities for Improvement'); actions=st.text_area('Actions Agreed'); notes=st.text_area('Auditor Notes')
    indicator=st.radio('Overall Control of Work Indicator',['Meets CoW Standard','Does not meet CoW Standard'],index=None)
    st.caption('Note - If one question is deemed “no or non conformance” - mark as Does not meet CoW Standard – Required for CoW KPI 3 reporting. Where N/A is appropriate, mark in Comments / Evidence section.')
    if st.button('Submit Leadership Engagement',type='primary',use_container_width=True):
        if not site or not leader: st.error('Complete Location / Team and Leadership Representative.')
        elif missing(rs) or indicator is None: st.error('Please answer all questions and select the Overall Control of Work Indicator.')
        else:
            meta={'site':site,'audit_date':str(ad),'auditor':leader,'reference':'','site_controller':sc,'positive_observations':positive,'opportunities_for_improvement':improvement,'actions_agreed':actions,'auditor_notes':notes,'overall_indicator':indicator}
            st.success('Submitted: '+save('Leadership Engagement',meta,rs,indicator))

elif page=='Submitted Audits':
    st.header('Submitted Audits')
    c=connect(); df=pd.read_sql_query('SELECT audit_id AS "Audit ID", submitted_at AS "Submitted", form_name AS "Form", audit_date AS "Audit Date", site AS "Site", auditor AS "Auditor", reference AS "Reference", summary AS "Summary" FROM audits ORDER BY submitted_at DESC',c); c.close()
    if len(df): st.dataframe(df,use_container_width=True,hide_index=True)
    else: st.info('No UAT submissions yet.')

else:
    st.header('Dashboard Export')
    c=connect(); recs=c.execute('SELECT audit_id,submitted_at,form_name,audit_date,site,auditor,reference,responses,summary FROM audits ORDER BY submitted_at').fetchall(); c.close()
    flat=[]
    for aid,submitted,form_name,ad,site,auditor,ref,responses,summary in recs:
        for r in json.loads(responses):
            flat.append({'Audit ID':aid,'Submitted At':submitted,'Form':form_name,'Audit Date':ad,'Site / Installation':site,'Auditor':auditor,'Reference':ref,'Question ID':r['question_id'],'Section':r['section'],'Question':r['question'],'Response':r['response'],'Comments / Evidence':r['comments_evidence'],'Overall Indicator':summary})
    if flat:
        df=pd.DataFrame(flat); st.dataframe(df.head(100),use_container_width=True,hide_index=True)
        st.download_button('Download dashboard-ready CSV',df.to_csv(index=False).encode('utf-8-sig'),'Perenco_CoW_Assurance_Export.csv','text/csv',use_container_width=True)
    else: st.info('Submit a test audit first.')
