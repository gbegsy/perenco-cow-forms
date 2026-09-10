
import streamlit as st
import json, sqlite3, uuid, base64
from pathlib import Path
from datetime import date, datetime
import pandas as pd

BASE=Path(__file__).parent
DATA=json.loads((BASE/"questions.json").read_text(encoding="utf-8"))
DB=BASE/"assurance_uat.db"
ICON=base64.b64encode((BASE/"cow_icon.png").read_bytes()).decode()

st.set_page_config(page_title="PUK CoW Assurance Forms", page_icon="🔒", layout="wide")
st.markdown('''
<style>
.block-container{max-width:1250px;padding-top:1rem;padding-bottom:3rem}
div[data-testid="stSidebar"]{background:#f4f5f7}
.puk-banner{background:#000;border:1px solid #000;color:#fff;display:grid;grid-template-columns:95px 1fr;align-items:center;margin-bottom:0;min-height:76px;overflow:visible}
.puk-banner .icon{padding:10px 12px}.puk-banner .icon img{width:62px}
.puk-banner .title{text-align:center;font-weight:800;font-size:23px;line-height:1.35;padding:12px 12px;display:flex;flex-direction:column;justify-content:center;min-height:76px;box-sizing:border-box}
.puk-banner .subtitle{text-align:center;font-weight:800;font-size:23px;margin-top:6px}
.purpose{border:1px solid #222;padding:8px 10px;font-size:13px;line-height:1.35;margin:0 0 8px;background:#fff}
.blackbar{background:#000;color:#fff;font-weight:800;padding:7px 10px;border:1px solid #000;margin-top:8px}
.section-title{font-weight:800;font-size:18px;margin:16px 0 6px}
.qrow{padding:8px 0 2px;background:#fff;margin-top:4px;font-size:15px}
[data-testid="stTextInput"] label,[data-testid="stSelectbox"] label,[data-testid="stDateInput"] label,[data-testid="stTextArea"] label,[data-testid="stRadio"] label{font-weight:700}
</style>
''',unsafe_allow_html=True)

def conn():
    c=sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS audits (audit_id TEXT PRIMARY KEY, submitted_at TEXT, form_name TEXT, audit_date TEXT, site TEXT, auditor TEXT, reference TEXT, metadata TEXT, responses TEXT, summary TEXT)")
    c.commit(); return c

def save(form_name,meta,responses,summary=""):
    aid="PUK-"+datetime.now().strftime("%Y%m%d")+"-"+uuid.uuid4().hex[:6].upper()
    c=conn()
    c.execute("INSERT INTO audits VALUES (?,?,?,?,?,?,?,?,?,?)",(aid,datetime.now().isoformat(timespec="seconds"),form_name,meta.get("audit_date",""),meta.get("site",""),meta.get("auditor",""),meta.get("reference",""),json.dumps(meta,ensure_ascii=False),json.dumps(responses,ensure_ascii=False),summary))
    c.commit(); c.close(); return aid

def banner(title,subtitle=None):
    sub=f'<div class="subtitle">{subtitle}</div>' if subtitle else ''
    html=f'<div class="puk-banner"><div class="icon"><img src="data:image/png;base64,{ICON}"></div><div class="title">{title}{sub}</div></div>'
    st.markdown(html,unsafe_allow_html=True)

def purpose(text):
    st.markdown(f'<div class="purpose"><b>PURPOSE:</b> {text}</div>',unsafe_allow_html=True)

def render_monitoring_sections(prefix,sections):
    responses=[]
    for si,(section,qs) in enumerate(sections):
        st.markdown(f'<div class="section-title">{section}</div>',unsafe_allow_html=True)
        for qi,(letter,q) in enumerate(qs):
            st.markdown(f'<div class="qrow"><b>{letter})</b> {q}</div>',unsafe_allow_html=True)
            c1,c2=st.columns([1,2])
            ans=c1.selectbox("Response",["Select","Yes","No","N/A"],key=f"{prefix}-{si}-{qi}-a",label_visibility="collapsed")
            act=c2.text_input("SMART ACTION",placeholder="Add Action",key=f"{prefix}-{si}-{qi}-s")
            responses.append({"section":section,"item":letter,"question":q,"response":None if ans=="Select" else ans,"smart_action":act})
    return responses

def header_ptw():
    c1,c2,c3,c4=st.columns([1.5,1.2,1.2,1])
    site=c1.text_input("SITE / INSTALLATION:")
    team=c2.text_input("TEAM:")
    ad=c3.date_input("DATE OF AUDIT:",date.today())
    nw=c4.checkbox("New WCC")
    c1,c2,c3,c4=st.columns([1.5,1.2,1.2,1])
    auditor=c1.text_input("AUDITOR:")
    sc=c2.text_input("SITE CONTROLLER:")
    ref=c3.text_input("WCC NUMBER:")
    routine=c4.checkbox("Routine")
    desc=st.text_input("WCC DESCRIPTION:")
    return {"site":site,"team":team,"audit_date":str(ad),"auditor":auditor,"site_controller":sc,"reference":ref,"wcc_description":desc,"new_wcc":nw,"routine":routine}

def header_tbt():
    c1,c2,c3,c4=st.columns([1.5,1.2,1.2,1])
    site=c1.text_input("SITE / INSTALLATION:")
    team=c2.text_input("TEAM:")
    ad=c3.date_input("DATE OF AUDIT:",date.today())
    activity=c4.radio("TYPE",["New WCC","Routine","POP"],index=None,key="activity")
    c1,c2,c3=st.columns([1.5,1.2,1.2])
    auditor=c1.text_input("AUDITOR:")
    sc=c2.text_input("SITE CONTROLLER:")
    ref=c3.text_input("WCC / POP No:")
    desc=st.text_input("DESCRIPTION:")
    return {"site":site,"team":team,"audit_date":str(ad),"auditor":auditor,"site_controller":sc,"reference":ref,"description":desc,"activity_type":activity}

page=st.sidebar.radio("Select form",["Permit Quality","Toolbox Talk / Permit / POP","Leadership Engagement","Submitted Audits","Dashboard Export"])

if page=="Permit Quality":
    banner("SELF VERIFICATION - LEVEL 4 MONITORING","Control of Work:  Permit Quality")
    meta=header_ptw()
    purpose("This monitoring activity is intended to verify day-to-day compliance with Permit-to-Work requirements, ensuring that permits and supporting risk assessments are suitable and sufficient for the task, safe working practices are consistently applied, and gaps in knowledge or understanding that could lead to hazardous errors are identified and addressed. The activity is designed for leadership roles (AA, Site Controller, Asset Superintendent) to strengthen oversight, promote engagement, and provide leadership assurance of Permit-to-Work effectiveness.")
    st.markdown('<div class="blackbar">QUESTION</div>',unsafe_allow_html=True)
    rs=render_monitoring_sections("ptw",DATA["ptw"])
    st.markdown('<div class="blackbar">ENTER THIS AUDIT INTO PTRAC, LOG FINDINGS IN THE AUDIT PLAN & ENSURE EACH NON-COMPLIANCE GENERATES A RECORDED SMART ACTION</div>',unsafe_allow_html=True)
    if st.button("Submit Permit Quality Audit",type="primary",use_container_width=True):
        blanks=[r for r in rs if r["response"] is None]
        if not meta["site"] or not meta["auditor"]: st.error("Complete SITE / INSTALLATION and AUDITOR.")
        elif blanks: st.error(f"Please confirm every question. {len(blanks)} response(s) remain as Select.")
        else: st.success("Submitted: "+save("Control of Work: Permit Quality",meta,rs))

elif page=="Toolbox Talk / Permit / POP":
    banner("SELF VERIFICATION - LEVEL 4 MONITORING","Control of Work:  Toolbox Talk, Permit Compliance & Operating Procedures")
    meta=header_tbt()
    purpose("This monitoring activity is intended to be used to self-verify the day-to-day compliance of TBT & Permits Compliance. Ensuring the TBT is suitable for the tasks outlined in the permit and operating procedure, reinforcing safe working practices and identify gaps in team knowledge that could lead to hazardous mistakes. This assurance activity is designed for leadership roles (HSEA, OTL, W2W OOE & Site Controller) to strengthen oversight, promote engagement, and provide leadership assurance of Permit-to-Work effectiveness,")
    st.markdown('<div class="blackbar">QUESTION <span style="margin-left:18%">Site Visit is Required – Sequential Review: TBT followed by Permit Compliance or POP</span></div>',unsafe_allow_html=True)
    activity=meta.get("activity_type")
    rs=render_monitoring_sections("tbt",DATA["tbt"][:2])
    st.markdown('<div class="blackbar">AUDITING A POP? MOVE TO QUESTION 8</div>',unsafe_allow_html=True)
    if activity=="POP":
        rs += render_monitoring_sections("pop",[DATA["pop"]])
    else:
        rs += render_monitoring_sections("tbt",DATA["tbt"][2:])
    st.markdown('<div class="blackbar">ENTER THIS AUDIT INTO PTRAC, LOG FINDINGS IN THE AUDIT PLAN & ENSURE EACH NON-COMPLIANCE GENERATES A RECORDED SMART ACTION</div>',unsafe_allow_html=True)
    if st.button("Submit TBT / Permit / POP Audit",type="primary",use_container_width=True):
        blanks=[r for r in rs if r["response"] is None]
        if not meta["site"] or not meta["auditor"] or not activity: st.error("Complete SITE / INSTALLATION, AUDITOR and select New WCC, Routine or POP.")
        elif blanks: st.error(f"Please confirm every displayed question. {len(blanks)} response(s) remain as Select.")
        else: st.success("Submitted: "+save("Control of Work: Toolbox Talk, Permit Compliance & Operating Procedures",meta,rs))

elif page=="Leadership Engagement":
    banner("Control of Work Leadership Engagement Checklist")
    c1,c2,c3,c4=st.columns([1,2,1.4,1.7])
    ad=c1.date_input("Date",date.today())
    site=c2.text_input("Location / Team (add W2W N/S or Flying N/S)")
    sc=c3.text_input("Site Controller")
    leader=c4.text_input("Leadership Representative")
    st.markdown('<div class="purpose"><b>Purpose:</b> This checklist provides a predefined set of Control of Work questions for leadership engagement visits. It supports visible leadership, workforce engagement and assurance discussions covering permit quality, hazard awareness, implementation of controls, supervision, Stop the Job culture and learning opportunities.</div>',unsafe_allow_html=True)
    rs=[]
    for si,(section,qs) in enumerate(DATA["lead"]):
        st.markdown(f'<div class="section-title">{section}</div>',unsafe_allow_html=True)
        st.markdown('<div class="blackbar">QUESTION</div>',unsafe_allow_html=True)
        for qi,q in enumerate(qs):
            st.markdown(f'<div class="qrow">{q}</div>',unsafe_allow_html=True)
            if section=="Learning & Continuous Improvement" and q.startswith("Can personnel suggest"):
                comment=st.text_area("Comments / Evidence",key=f"lead-{si}-{qi}-c",height=70)
                ans="Comment"
            else:
                ans=st.radio("Response",["Yes","No"],index=None,horizontal=True,key=f"lead-{si}-{qi}-a",label_visibility="collapsed")
                comment=st.text_input("COMMENTS / EVIDENCE",key=f"lead-{si}-{qi}-c",placeholder="Enter comments / evidence")
            rs.append({"section":section,"question":q,"response":ans,"comments_evidence":comment})
    st.markdown('<div class="section-title">Leadership Summary</div>',unsafe_allow_html=True)
    positive=st.text_area("Positive Observations")
    improvement=st.text_area("Opportunities for Improvement")
    actions=st.text_area("Actions Agreed")
    indicator=st.radio("Overall Control of Work Indicator",["Meets CoW Standard","Does not meet CoW Standard"],index=None)
    notes=st.text_area("Auditor Notes")
    st.markdown('<div class="purpose"><b>Note - If one question is deemed “no or non conformance” - mark as <i>Does not meet CoW Standard</i> – Required for CoW KPI 3 reporting</b><br><br><b>Where N/A is appropriate, mark in Comments / Evidence section</b></div>',unsafe_allow_html=True)
    if st.button("Submit Leadership Engagement",type="primary",use_container_width=True):
        required=[r for r in rs if r["response"]!="Comment"]
        blanks=[r for r in required if r["response"] is None]
        if not site or not leader: st.error("Complete Location / Team and Leadership Representative.")
        elif blanks or indicator is None: st.error("Answer all Yes/No questions and select the Overall Control of Work Indicator.")
        else:
            meta={"site":site,"audit_date":str(ad),"auditor":leader,"site_controller":sc,"reference":"","positive_observations":positive,"opportunities_for_improvement":improvement,"actions_agreed":actions,"auditor_notes":notes,"overall_indicator":indicator}
            st.success("Submitted: "+save("Control of Work Leadership Engagement Checklist",meta,rs,indicator))

elif page=="Submitted Audits":
    st.header("Submitted Audits")
    c=conn()
    df=pd.read_sql_query('SELECT audit_id AS "Audit ID", submitted_at AS "Submitted", form_name AS "Form", audit_date AS "Audit Date", site AS "Site", auditor AS "Auditor", reference AS "Reference", summary AS "Summary" FROM audits ORDER BY submitted_at DESC',c)
    c.close()
    if len(df): st.dataframe(df,use_container_width=True,hide_index=True)
    else: st.info("No UAT submissions yet.")

else:
    st.header("Dashboard Export")
    c=conn(); recs=c.execute("SELECT audit_id,submitted_at,form_name,audit_date,site,auditor,reference,responses,summary FROM audits ORDER BY submitted_at").fetchall(); c.close()
    flat=[]
    for aid,submitted,form_name,ad,site,auditor,ref,responses,summary in recs:
        for r in json.loads(responses):
            flat.append({"Audit ID":aid,"Submitted At":submitted,"Form":form_name,"Audit Date":ad,"Site / Installation":site,"Auditor":auditor,"Reference":ref,"Section":r.get("section",""),"Question":r.get("question",""),"Response":r.get("response",""),"Comments / Evidence":r.get("comments_evidence",""),"SMART Action":r.get("smart_action",""),"Overall Indicator":summary})
    if flat:
        df=pd.DataFrame(flat)
        st.dataframe(df.head(100),use_container_width=True,hide_index=True)
        st.download_button("Download dashboard-ready CSV",df.to_csv(index=False).encode("utf-8-sig"),"Perenco_CoW_Assurance_Export.csv","text/csv",use_container_width=True)
    else: st.info("Submit a test audit first.")
