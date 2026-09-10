
import streamlit as st
import json, sqlite3, uuid, base64
from pathlib import Path
from datetime import date, datetime, timedelta
import calendar
import pandas as pd
import streamlit.components.v1 as components

BASE=Path(__file__).parent
DATA=json.loads((BASE/"questions.json").read_text(encoding="utf-8"))
DB=BASE/"assurance_uat.db"
ICON=base64.b64encode((BASE/"cow_icon.png").read_bytes()).decode()

st.set_page_config(page_title="PUK CoW Assurance Forms", page_icon="🔒", layout="wide")
st.markdown('''
<style>
.block-container{max-width:1420px;padding-top:2rem;padding-bottom:3.5rem}
div[data-testid="stSidebar"]{
    background:linear-gradient(180deg,#f7f9fb 0%,#eef3f6 100%);
    border-right:1px solid #d6e0e7;
}
div[data-testid="stSidebar"] [data-testid="stSidebarContent"]{padding-top:1rem}
div[data-testid="stSidebar"] .stRadio > label{
    font-size:10px;font-weight:800;color:#66788a;text-transform:uppercase;
    letter-spacing:.8px;margin:2px 0 10px 2px
}
div[data-testid="stSidebar"] div[role="radiogroup"]{gap:6px}
div[data-testid="stSidebar"] div[role="radiogroup"] label{
    background:rgba(255,255,255,.9);
    border:1px solid #d7e1e8;
    border-radius:9px;
    padding:9px 11px;
    min-height:40px;
    display:flex;
    align-items:center;
    box-shadow:0 1px 2px rgba(22,50,74,.03);
}
div[data-testid="stSidebar"] div[role="radiogroup"] label:hover{
    border-color:#9eb4c3;background:#fff
}
div[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked){
    background:#e9f2f8;border-color:#8eb3ca;box-shadow:inset 4px 0 0 #1679c4
}
div[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p{
    font-weight:800;color:#16324a
}
div[data-testid="stSidebar"] div[role="radiogroup"] input{display:none!important}
div[data-testid="stSidebar"] div[role="radiogroup"] svg{display:none!important}
.puk-banner{background:#000;border:1px solid #000;color:#fff;display:grid;grid-template-columns:105px 1fr;align-items:center;margin-bottom:8px;min-height:122px;overflow:hidden;box-sizing:border-box}
.puk-banner .icon{padding:14px 16px;display:flex;align-items:center;justify-content:flex-start}.puk-banner .icon img{width:66px;height:auto}
.puk-banner .title{text-align:center;font-weight:800;font-size:22px;line-height:1.35;padding:18px 24px 18px 8px;display:flex;flex-direction:column;justify-content:center;min-height:122px;box-sizing:border-box}
.puk-banner .subtitle{text-align:center;font-weight:800;font-size:22px;line-height:1.3;margin-top:10px}
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
    c.execute("CREATE TABLE IF NOT EXISTS role_mapping (mapping_type TEXT, person_name TEXT, role_name TEXT, PRIMARY KEY(mapping_type, person_name))")
    c.execute("""CREATE TABLE IF NOT EXISTS kpi5_summary (
        record_id TEXT PRIMARY KEY,
        submitted_at TEXT,
        reporting_month TEXT,
        site TEXT,
        rolling_12m_count INTEGER,
        previous_12m_count INTEGER,
        trigger_level TEXT,
        comments TEXT,
        demo INTEGER DEFAULT 0
    )""")
    existing={r[1] for r in c.execute("PRAGMA table_info(kpi5_summary)").fetchall()}
    for col,definition in {
        "hipo_count":"INTEGER DEFAULT 0",
        "significant_injury_count":"INTEGER DEFAULT 0",
        "loc_count":"INTEGER DEFAULT 0",
        "major_loc_count":"INTEGER DEFAULT 0",
        "repeat_event_theme":"TEXT DEFAULT 'No'",
        "recurring_permit_failure":"TEXT DEFAULT 'No'",
        "significant_increase":"TEXT DEFAULT 'No'"
    }.items():
        if col not in existing:
            c.execute(f"ALTER TABLE kpi5_summary ADD COLUMN {col} {definition}")
    c.execute("""CREATE TABLE IF NOT EXISTS kpi_governance (
        reporting_period TEXT,
        site TEXT,
        kpi2_assurance_comparison TEXT DEFAULT 'Not assessed',
        kpi2_independent_conformance INTEGER,
        kpi2_independent_findings INTEGER DEFAULT 0,
        kpi2_self_verification_findings INTEGER DEFAULT 0,
        kpi3_coverage TEXT DEFAULT 'Not assessed',
        kpi4_visit_justification TEXT DEFAULT 'Not required',
        kpi4_field_oim_coverage TEXT DEFAULT 'Not assessed',
        kpi4_finding_profile TEXT DEFAULT 'None',
        kpi4_oim_consecutive_missed INTEGER DEFAULT 0,
        kpi4_oim_missed_12m INTEGER DEFAULT 0,
        PRIMARY KEY(reporting_period,site)
    )""")
    gov_existing={r[1] for r in c.execute("PRAGMA table_info(kpi_governance)").fetchall()}
    for col,definition in {
        "kpi2_independent_conformance":"INTEGER",
        "kpi2_independent_findings":"INTEGER DEFAULT 0",
        "kpi2_self_verification_findings":"INTEGER DEFAULT 0"
    }.items():
        if col not in gov_existing:
            c.execute(f"ALTER TABLE kpi_governance ADD COLUMN {col} {definition}")
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
            anchor=f"q-{prefix}-{si}-{qi}"
            st.markdown(f'<div id="{anchor}" class="qrow"><b>{letter})</b> {q}</div>',unsafe_allow_html=True)
            c1,c2=st.columns([1,2])
            ans=c1.selectbox("Response",["Select","Yes","No","N/A"],key=f"{prefix}-{si}-{qi}-a",label_visibility="collapsed")
            act=c2.text_input("SMART ACTION",placeholder="Add Action",key=f"{prefix}-{si}-{qi}-s")
            responses.append({"section":section,"item":letter,"question":q,"response":None if ans=="Select" else ans,"smart_action":act,"anchor":anchor})
    return responses

def jump_to(anchor):
    components.html(f"""<script>
    const el = parent.document.getElementById('{anchor}');
    if (el) {{ el.scrollIntoView({{behavior:'smooth', block:'center'}}); }}
    </script>""", height=0)


def enable_scroll_to_top():
    components.html("""
    <script>
    const doc = parent.document;

    function goTop() {
        try {
            parent.window.scrollTo({top:0, left:0, behavior:'smooth'});
            const main = doc.querySelector('section.main');
            if (main) main.scrollTo({top:0, left:0, behavior:'smooth'});
            const app = doc.querySelector('[data-testid="stAppViewContainer"]');
            if (app) app.scrollTo({top:0, left:0, behavior:'smooth'});
        } catch(e) {}
    }

    function bind() {
        // Dashboard tabs
        doc.querySelectorAll('button[role="tab"]').forEach(el => {
            if (!el.dataset.pukTopBound) {
                el.dataset.pukTopBound = "1";
                el.addEventListener('click', () => setTimeout(goTop, 60));
            }
        });

        // Sidebar page navigation
        doc.querySelectorAll('[data-testid="stSidebar"] div[role="radiogroup"] label').forEach(el => {
            if (!el.dataset.pukTopBound) {
                el.dataset.pukTopBound = "1";
                el.addEventListener('click', () => setTimeout(goTop, 120));
            }
        });
    }

    bind();
    const observer = new MutationObserver(bind);
    observer.observe(doc.body, {childList:true, subtree:true});
    </script>
    """, height=0)

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


def load_audits():
    c=conn()
    rows=c.execute("SELECT audit_id,submitted_at,form_name,audit_date,site,auditor,reference,metadata,responses,summary FROM audits ORDER BY submitted_at").fetchall()
    c.close()
    out=[]
    for aid,submitted,form_name,ad,site,auditor,ref,meta,responses,summary in rows:
        try: meta_obj=json.loads(meta or "{}")
        except: meta_obj={}
        try: resp_obj=json.loads(responses or "[]")
        except: resp_obj=[]
        out.append({"audit_id":aid,"submitted_at":submitted,"form_name":form_name,"audit_date":ad,"site":site,"auditor":auditor,"reference":ref,"metadata":meta_obj,"responses":resp_obj,"summary":summary})
    return out

def get_role_mapping(mapping_type):
    c=conn()
    rows=c.execute("SELECT person_name, role_name FROM role_mapping WHERE mapping_type=?",(mapping_type,)).fetchall()
    c.close()
    return {n:r for n,r in rows}

def set_role_mapping(mapping_type, person_name, role_name):
    c=conn()
    c.execute("INSERT OR REPLACE INTO role_mapping(mapping_type,person_name,role_name) VALUES (?,?,?)",(mapping_type,person_name,role_name))
    c.commit(); c.close()

def audit_result(a):
    vals=[str(r.get("response","")).strip().lower() for r in a["responses"]]
    vals=[v for v in vals if v in ("yes","no")]
    if not vals: return None
    return "Non-Compliant" if "no" in vals else "Compliant"

def question_conformance(audits):
    vals=[]
    for a in audits:
        for r in a["responses"]:
            v=str(r.get("response","")).strip().lower()
            if v in ("yes","no"): vals.append(v)
    if not vals: return None
    return round(100*sum(v=="yes" for v in vals)/len(vals))

def audit_conformance(audits):
    results=[audit_result(a) for a in audits]
    results=[r for r in results if r]
    if not results: return None
    return round(100*sum(r=="Compliant" for r in results)/len(results))

def permit_sample_type(a):
    """Classify Permit Quality evidence without changing the approved Perenco form wording."""
    m=a.get("metadata",{}) or {}
    routine=bool(m.get("routine"))
    new_wcc=bool(m.get("new_wcc"))
    if routine and not new_wcc:
        return "Routine"
    if new_wcc and not routine:
        return "Non-Routine"
    return "Unclassified"

def tbt_sample_type(a):
    v=str((a.get("metadata",{}) or {}).get("activity_type","")).strip()
    if v=="Routine":
        return "Routine"
    if v=="New WCC":
        return "Non-Routine"
    if v=="POP":
        return "POP"
    return "Unclassified"

def weeks_in_month(year,month):
    cal=calendar.monthcalendar(year,month)
    return sum(1 for wk in cal if wk[calendar.MONDAY] != 0)

def status_both(plan_pct, conf):
    if plan_pct is None or conf is None: return "Not enough data"
    if plan_pct < 70 or conf < 70: return "Red"
    if plan_pct >= 100 and conf >= 90: return "Green"
    return "Amber"

def status_class(s):
    return {"Green":"green","Amber":"amber","Red":"red","Needs review":"amber","In progress":""}.get(s,"")

def kpi_card(title,name,value,status,detail):
    cls=status_class(status)
    st.markdown(f"""
    <div class="kpi {cls}">
      <h3>{title}</h3>
      <div class="name">{name}</div>
      <div class="num">{value}</div>
      <span class="badge">{status.upper()}</span>
      <div class="detail">{detail}</div>
    </div>
    """,unsafe_allow_html=True)





def save_kpi5_summary(data):
    rid="KPI5-"+datetime.now().strftime("%Y%m")+"-"+uuid.uuid4().hex[:6].upper()
    c=conn()
    c.execute("""INSERT INTO kpi5_summary
        (record_id,submitted_at,reporting_month,site,rolling_12m_count,previous_12m_count,
         trigger_level,comments,demo,hipo_count,significant_injury_count,loc_count,major_loc_count,
         repeat_event_theme,recurring_permit_failure,significant_increase)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (rid,datetime.now().isoformat(timespec="seconds"),data["reporting_month"],data["site"],
         int(data["rolling_12m_count"]),int(data["previous_12m_count"]),"",data["comments"],0,
         int(data["hipo_count"]),int(data["significant_injury_count"]),int(data["loc_count"]),
         int(data["major_loc_count"]),data["repeat_event_theme"],data["recurring_permit_failure"],
         data["significant_increase"]))
    c.commit(); c.close()
    return rid

def load_kpi5_summary():
    c=conn()
    rows=c.execute("""SELECT record_id,submitted_at,reporting_month,site,rolling_12m_count,
        previous_12m_count,comments,demo,hipo_count,significant_injury_count,loc_count,
        major_loc_count,repeat_event_theme,recurring_permit_failure,significant_increase
        FROM kpi5_summary ORDER BY reporting_month DESC, submitted_at DESC""").fetchall()
    c.close()
    cols=["record_id","submitted_at","reporting_month","site","rolling_12m_count","previous_12m_count",
          "comments","demo","hipo_count","significant_injury_count","loc_count","major_loc_count",
          "repeat_event_theme","recurring_permit_failure","significant_increase"]
    return [dict(zip(cols,r)) for r in rows]

def get_governance(reporting_period,site):
    c=conn()
    row=c.execute("""SELECT kpi2_assurance_comparison,kpi2_independent_conformance,
        kpi2_independent_findings,kpi2_self_verification_findings,kpi3_coverage,
        kpi4_visit_justification,kpi4_field_oim_coverage,kpi4_finding_profile,
        kpi4_oim_consecutive_missed,kpi4_oim_missed_12m
        FROM kpi_governance WHERE reporting_period=? AND site=?""",(reporting_period,site)).fetchone()
    c.close()
    if not row:
        return {
            "kpi2_assurance_comparison":"Not assessed",
            "kpi2_independent_conformance":None,
            "kpi2_independent_findings":0,
            "kpi2_self_verification_findings":0,
            "kpi3_coverage":"Not assessed",
            "kpi4_visit_justification":"Not required",
            "kpi4_field_oim_coverage":"Not assessed",
            "kpi4_finding_profile":"None",
            "kpi4_oim_consecutive_missed":0,
            "kpi4_oim_missed_12m":0
        }
    keys=["kpi2_assurance_comparison","kpi2_independent_conformance",
          "kpi2_independent_findings","kpi2_self_verification_findings","kpi3_coverage",
          "kpi4_visit_justification","kpi4_field_oim_coverage","kpi4_finding_profile",
          "kpi4_oim_consecutive_missed","kpi4_oim_missed_12m"]
    return dict(zip(keys,row))

def save_governance(reporting_period,site,g):
    c=conn()
    c.execute("""INSERT OR REPLACE INTO kpi_governance
        (reporting_period,site,kpi2_assurance_comparison,kpi2_independent_conformance,
         kpi2_independent_findings,kpi2_self_verification_findings,kpi3_coverage,
         kpi4_visit_justification,kpi4_field_oim_coverage,kpi4_finding_profile,
         kpi4_oim_consecutive_missed,kpi4_oim_missed_12m)
         VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (reporting_period,site,g["kpi2_assurance_comparison"],g["kpi2_independent_conformance"],
         int(g["kpi2_independent_findings"]),int(g["kpi2_self_verification_findings"]),
         g["kpi3_coverage"],g["kpi4_visit_justification"],g["kpi4_field_oim_coverage"],
         g["kpi4_finding_profile"],int(g["kpi4_oim_consecutive_missed"]),
         int(g["kpi4_oim_missed_12m"])))
    c.commit(); c.close()

def kpi5_position(records, report_year, report_month, site_filter="All"):
    period=f"{report_year:04d}-{report_month:02d}"
    matches=[r for r in records if r["reporting_month"]==period and (site_filter=="All" or r["site"] in (site_filter,"All"))]
    if not matches:
        return {"status":"No data","count":None,"previous":None,"trend":"—",
                "reason":"No KPI 5 value entered for the selected reporting period."}
    r=matches[0]
    current=int(r["rolling_12m_count"] or 0)
    previous=int(r["previous_12m_count"] or 0)
    hipo=int(r["hipo_count"] or 0)
    sig=int(r["significant_injury_count"] or 0)
    loc=int(r["loc_count"] or 0)
    major_loc=int(r["major_loc_count"] or 0)
    repeat_theme=str(r["repeat_event_theme"]).lower()=="yes"
    recurring=str(r["recurring_permit_failure"]).lower()=="yes"
    significant_increase=str(r["significant_increase"]).lower()=="yes"
    trend="Increasing" if current>previous else ("Decreasing" if current<previous else "No increase")
    if significant_increase or hipo>=2 or sig>=2 or major_loc>=1 or recurring:
        status="Red"
        reasons=[]
        if significant_increase: reasons.append("significant increase in rolling 12-month trend")
        if hipo>=2: reasons.append("multiple HiPOs")
        if sig>=2: reasons.append("multiple significant injuries")
        if major_loc>=1: reasons.append("major Loss of Containment")
        if recurring: reasons.append("recurring permit-control failures")
    elif current>previous or hipo==1 or sig==1 or loc>=1 or repeat_theme:
        status="Amber"
        reasons=[]
        if current>previous: reasons.append("increasing rolling 12-month trend")
        if hipo==1: reasons.append("single HiPO")
        if sig==1: reasons.append("single significant injury")
        if loc>=1: reasons.append("Loss of Containment")
        if repeat_theme: reasons.append("repeat event theme")
    else:
        status="Green"
        reasons=["no increase and no HiPO, significant injury or repeat Loss of Containment trigger"]
    return {"status":status,"count":current,"previous":previous,"trend":trend,
            "reason":"; ".join(reasons),"record":r}

def render_kpi5_input():
    st.markdown("""
    <div class="dash-shell">
      <div class="dash-kicker">Perenco UK · KPI 5 · Tier 1</div>
      <div class="dash-title">Increased Incidents During Permit Controlled Activity</div>
      <div class="dash-sub">Monthly summary input from MOI reporting · rolling 12-month indicator</div>
    </div>
    """,unsafe_allow_html=True)
    st.info("Enter the monthly summary from Perenco's MOI tracking dataset. This does not replace MOI or duplicate incident records.")
    c1,c2,c3=st.columns(3)
    report_month=c1.date_input("Reporting month",date.today().replace(day=1))
    site=c2.text_input("Site / Asset",value="All")
    current=c3.number_input("Rolling 12-month permit-controlled MOIs",min_value=0,step=1,value=0)
    c1,c2,c3=st.columns(3)
    previous=c1.number_input("Previous rolling 12-month count",min_value=0,step=1,value=0)
    hipo=c2.number_input("HiPOs",min_value=0,step=1,value=0)
    sig=c3.number_input("Significant injuries (MTC or above)",min_value=0,step=1,value=0)
    c1,c2,c3=st.columns(3)
    loc=c1.number_input("Loss of Containment events",min_value=0,step=1,value=0)
    major_loc=c2.number_input("Major Loss of Containment events",min_value=0,step=1,value=0)
    repeat_theme=c3.selectbox("Repeat event theme identified?",["No","Yes"])
    c1,c2=st.columns(2)
    recurring=c1.selectbox("Recurring permit-control failures identified?",["No","Yes"])
    significant_increase=c2.selectbox("Significant increase in rolling 12-month trend?",["No","Yes"],
        help="Perenco uses 'significant increase' but does not define a numerical threshold. Record the agreed management assessment.")
    comments=st.text_area("Optional KPI comment / source note")
    if st.button("Save KPI 5 result",type="primary",use_container_width=True):
        rid=save_kpi5_summary({
            "reporting_month":report_month.strftime("%Y-%m"),"site":site.strip() or "All",
            "rolling_12m_count":current,"previous_12m_count":previous,"hipo_count":hipo,
            "significant_injury_count":sig,"loc_count":loc,"major_loc_count":major_loc,
            "repeat_event_theme":repeat_theme,"recurring_permit_failure":recurring,
            "significant_increase":significant_increase,"comments":comments})
        st.success(f"Saved KPI 5 result: {rid}")
    st.markdown("### Saved KPI 5 results")
    rows=load_kpi5_summary()
    if rows:
        df=pd.DataFrame(rows)
        show=df[["reporting_month","site","rolling_12m_count","previous_12m_count","hipo_count",
                 "significant_injury_count","loc_count","major_loc_count","repeat_event_theme",
                 "recurring_permit_failure","significant_increase","comments"]].copy()
        show.columns=["Reporting month","Site / Asset","Rolling 12m MOIs","Previous 12m","HiPOs",
                      "Significant injuries","LOC","Major LOC","Repeat theme","Recurring permit failure",
                      "Significant increase","Comment"]
        st.dataframe(show,use_container_width=True,hide_index=True)
    else:
        st.info("No KPI 5 results entered yet.")

def seed_demo_data():
    """Insert a complete, clearly-labelled synthetic UAT dataset and KPI role mappings."""
    c=conn()

    # Remove any prior demo records so repeated testing stays tidy.
    c.execute("DELETE FROM audits WHERE audit_id LIKE 'DEMO-%'")
    c.execute("DELETE FROM role_mapping WHERE person_name LIKE 'Demo %'")

    today=date.today()
    audit_date=str(today)
    now=datetime.now().isoformat(timespec="seconds")

    def rec(aid, form_name, site, auditor, reference, responses, summary="", meta_extra=None):
        meta={"site":site,"audit_date":audit_date,"auditor":auditor,"reference":reference,"demo":True}
        if meta_extra: meta.update(meta_extra)
        return (
            aid, now, form_name, audit_date, site, auditor, reference,
            json.dumps(meta,ensure_ascii=False),
            json.dumps(responses,ensure_ascii=False),
            summary
        )

    records=[]

    # KPI 1 - Site Controller Permit Quality
    records.append(rec(
        "DEMO-PQ-SC-001","Control of Work: Permit Quality","Dimlington","Demo Site Controller","DEMO-WCC-SC-001",
        [
            {"section":"1. Planning","item":"a","question":"Is the activity planned to be undertaken outside the next 24 hours?","response":"Yes","smart_action":""},
            {"section":"1. Planning","item":"b","question":"Has the WCC been discussed in the daily permit meeting?","response":"Yes","smart_action":""},
            {"section":"2. Raising a NEW WCC","item":"a","question":"Is there a brief, clear and concise summary of scope?","response":"No","smart_action":"Improve the WCC scope description and verify it before issue."},
        ],
        meta_extra={"new_wcc":True,"routine":False}
    ))
    records.append(rec(
        "DEMO-PQ-SC-002","Control of Work: Permit Quality","Dimlington","Demo Site Controller","DEMO-WCC-SC-002",
        [
            {"section":"1. Planning","item":"a","question":"Is the activity planned to be undertaken outside the next 24 hours?","response":"Yes","smart_action":""},
            {"section":"1. Planning","item":"b","question":"Has the WCC been discussed in the daily permit meeting?","response":"Yes","smart_action":""},
            {"section":"2. Raising a NEW WCC","item":"a","question":"Is there a brief, clear and concise summary of scope?","response":"Yes","smart_action":""},
        ],
        meta_extra={"new_wcc":False,"routine":True}
    ))

    # KPI 2 - Asset Superintendent Permit Quality
    records.append(rec(
        "DEMO-PQ-AS-001","Control of Work: Permit Quality","Ravenspurn North","Demo Asset Superintendent","DEMO-WCC-AS-001",
        [
            {"section":"1. Planning","item":"a","question":"Is the activity planned to be undertaken outside the next 24 hours?","response":"Yes","smart_action":""},
            {"section":"4. Identifying the Correct WCC","item":"a","question":"Has the correct Type of WCC been selected appropriate for the task?","response":"Yes","smart_action":""},
            {"section":"12. Isolation Requirements","item":"a","question":"Have all controls within the ICC been acknowledged and transferred to the WCC?","response":"Yes","smart_action":""},
        ],
        meta_extra={"new_wcc":False,"routine":True}
    ))

    # KPI 4 - W2W OOE and Medic/HSEA visits
    records.append(rec(
        "DEMO-TBT-OOE-001","Control of Work: Toolbox Talk, Permit Compliance & Operating Procedures","Northern W2W","Demo W2W OOE","DEMO-TBT-OOE-001",
        [
            {"section":"1. TBT Hazard Identification","item":"a","question":"TBT Lead discusses the hazards and controls associated to the task/activity","response":"Yes","smart_action":""},
            {"section":"4. Permit Compliance","item":"a","question":"Is there an up-to-date copy of the WCC at the worksite and signed by all members of the work party?","response":"No","smart_action":"Confirm the current WCC is available at the worksite and obtain all required signatures."},
        ],
        meta_extra={"activity_type":"New WCC"}
    ))
    records.append(rec(
        "DEMO-TBT-HSEA-001","Control of Work: Toolbox Talk, Permit Compliance & Operating Procedures","Southern W2W","Demo Medic HSEA","DEMO-TBT-HSEA-001",
        [
            {"section":"1. TBT Hazard Identification","item":"a","question":"TBT Lead discusses the hazards and controls associated to the task/activity","response":"Yes","smart_action":""},
            {"section":"3. Hazards associated to the Worksite and Equipment","item":"c","question":"Are all access and egress points checked and clear?","response":"Yes","smart_action":""},
        ],
        meta_extra={"activity_type":"Routine"}
    ))
    records.append(rec(
        "DEMO-TBT-OIM-001","Control of Work: Toolbox Talk, Permit Compliance & Operating Procedures","Cleeton","Demo Field Hub OIM","DEMO-TBT-OIM-001",
        [
            {"section":"1. TBT Hazard Identification","item":"a","question":"TBT Lead discusses the hazards and controls associated to the task/activity","response":"Yes","smart_action":""},
            {"section":"4. Permit Compliance","item":"a","question":"Is there an up-to-date copy of the WCC at the worksite and signed by all members of the work party?","response":"Yes","smart_action":""},
        ],
        meta_extra={"activity_type":"Routine"}
    ))

    # KPI 3 - two synthetic leadership engagements in the current quarter.
    records.append(rec(
        "DEMO-LEAD-001","Control of Work Leadership Engagement Checklist","Northern W2W","Demo Operations Director","",
        [
            {"section":"Permit to Work (PTW)","question":"Are personnel able to explain the work they are undertaking?","response":"Yes","comments_evidence":"Clear understanding demonstrated."},
            {"section":"Hazard Identification & Risk Assessment","question":"Can personnel explain the key hazards associated with the task?","response":"Yes","comments_evidence":"Key hazards understood."},
            {"section":"Stop the Job Culture","question":"Do personnel understand their authority to stop the job?","response":"Yes","comments_evidence":"Stop-work authority understood."},
        ],
        "Meets CoW Standard",
        {"overall_indicator":"Meets CoW Standard"}
    ))
    records.append(rec(
        "DEMO-LEAD-002","Control of Work Leadership Engagement Checklist","Southern W2W","Demo Operations Director","",
        [
            {"section":"Permit to Work (PTW)","question":"Are personnel able to explain the work they are undertaking?","response":"Yes","comments_evidence":"Work scope understood."},
            {"section":"Worksite Compliance","question":"Are permit controls being implemented at the worksite?","response":"Yes","comments_evidence":"Controls observed in place."},
            {"section":"Stop the Job Culture","question":"Would personnel feel comfortable challenging unsafe conditions?","response":"Yes","comments_evidence":"Positive challenge culture evidenced."},
        ],
        "Meets CoW Standard",
        {"overall_indicator":"Meets CoW Standard"}
    ))

    c.executemany(
        "INSERT OR REPLACE INTO audits (audit_id,submitted_at,form_name,audit_date,site,auditor,reference,metadata,responses,summary) VALUES (?,?,?,?,?,?,?,?,?,?)",
        records
    )

    mappings=[
        ("permit","Demo Site Controller","Site Controller"),
        ("permit","Demo Asset Superintendent","Asset Superintendent"),
        ("tbt","Demo W2W OOE","W2W OOE"),
        ("tbt","Demo Medic HSEA","Medic HSEA"),
        ("tbt","Demo Field Hub OIM","Field Hub OIM"),
        ("lead","Demo Operations Director","Operations Director"),
    ]
    c.executemany(
        "INSERT OR REPLACE INTO role_mapping (mapping_type,person_name,role_name) VALUES (?,?,?)",
        mappings
    )

    c.execute("DELETE FROM kpi5_summary WHERE demo=1")
    c.execute("""INSERT OR REPLACE INTO kpi5_summary
        (record_id,submitted_at,reporting_month,site,rolling_12m_count,previous_12m_count,
         trigger_level,comments,demo,hipo_count,significant_injury_count,loc_count,major_loc_count,
         repeat_event_theme,recurring_permit_failure,significant_increase)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        ("DEMO-KPI5-001",now,audit_date[:7],"All",1,0,"","Synthetic UAT value only",1,
         0,0,1,0,"Yes","No","No"))
    c.commit()
    c.close()

def clear_demo_data():
    c=conn()
    c.execute("DELETE FROM audits WHERE audit_id LIKE 'DEMO-%'")
    c.execute("DELETE FROM role_mapping WHERE person_name LIKE 'Demo %'")
    c.execute("DELETE FROM kpi5_summary WHERE demo=1 OR record_id LIKE 'DEMO-%'")
    c.commit()
    c.close()

def render_dashboard():
    st.markdown("""
    <style>
    .dash-shell{
        background:linear-gradient(135deg,#102b40 0%,#173f5c 68%,#1d5d82 100%);
        color:#fff;border-radius:16px;padding:24px 26px 20px;margin-bottom:16px;
        box-shadow:0 8px 24px rgba(16,43,64,.16);
    }
    .dash-kicker{font-size:10px;font-weight:800;letter-spacing:1.4px;text-transform:uppercase;color:#b9d9ec;margin-bottom:7px}
    .dash-title{font-size:31px;font-weight:800;margin:0 0 5px;color:#fff;letter-spacing:-.4px}
    .dash-sub{color:#d6e5ef;margin-bottom:0;font-size:13px}
    .dash-section-label{font-size:11px;font-weight:800;letter-spacing:.8px;text-transform:uppercase;color:#6f8291;margin:18px 0 8px}
    .kpi{
        background:#fff;border:1px solid #d8e2e8;border-top:5px solid #a8b7c2;
        border-radius:12px;padding:16px 15px;min-height:184px;
        box-shadow:0 4px 15px rgba(16,42,67,.07);
        transition:transform .15s ease,box-shadow .15s ease;
    }
    .kpi:hover{transform:translateY(-2px);box-shadow:0 7px 20px rgba(16,42,67,.10)}
    .kpi.green{border-top-color:#16865b}.kpi.amber{border-top-color:#b97500}.kpi.red{border-top-color:#c43b3b}
    .kpi h3{font-size:10px;margin:0;color:#6b7f90;text-transform:uppercase;letter-spacing:.7px}
    .kpi .name{font-weight:800;margin:8px 0 3px;color:#132b3e;font-size:14px;line-height:1.35;min-height:38px}
    .kpi .num{font-size:31px;font-weight:800;margin:12px 0 7px;color:#10283a;letter-spacing:-.5px}
    .kpi .detail{font-size:11px;color:#6c7d89;line-height:1.45;margin-top:8px}
    .badge{
        display:inline-block;padding:5px 9px;border-radius:999px;font-size:9px;font-weight:800;
        letter-spacing:.35px;background:#edf1f4;color:#62717d
    }
    .green .badge{background:#e8f6ee;color:#16865b}
    .amber .badge{background:#fff3da;color:#9b6300}
    .red .badge{background:#fdeaea;color:#ba3535}
    .dash-note{
        padding:14px 16px;border-radius:10px;background:#edf5fb;border:1px solid #d5e6f2;
        border-left:5px solid #1679c4;line-height:1.5;margin:10px 0 4px;
        box-shadow:0 2px 8px rgba(16,42,67,.04)
    }
    .dash-warn{background:#fff7e7;border-color:#f1dfb7;border-left-color:#b97500}
    .dash-bad{background:#fff0f0;border-color:#f1d1d1;border-left-color:#c43b3b}
    .dash-good{background:#edf8f2;border-color:#d1eadc;border-left-color:#16865b}
    div[data-testid="stMetric"]{
        background:#fff;border:1px solid #e0e7ec;border-radius:10px;padding:12px 14px;
        box-shadow:0 2px 8px rgba(16,42,67,.04)
    }
    div[data-testid="stMetric"] label{font-size:11px;color:#70818e}
    div[data-testid="stMetricValue"]{font-weight:800;color:#16324a}
    div[data-baseweb="tab-list"]{
        gap:5px;border-bottom:1px solid #dfe6eb;margin-top:4px
    }
    button[role="tab"]{
        border-radius:8px 8px 0 0!important;padding:9px 13px!important
    }
    button[role="tab"][aria-selected="true"]{
        background:#eef5fa!important;color:#16324a!important;font-weight:800!important
    }
    </style>
    """,unsafe_allow_html=True)
    st.markdown("""
    <div class="dash-shell">
      <div class="dash-kicker">Perenco UK · Operational Assurance</div>
      <div class="dash-title">Control of Work KPI Dashboard</div>
      <div class="dash-sub">KPI performance, assurance coverage and leadership oversight</div>
    </div>
    """,unsafe_allow_html=True)

    with st.expander("UAT / Demo controls", expanded=False):
        d1,d2,_=st.columns([1.1,1.1,6])
        if d1.button("Load demo data",use_container_width=True):
            seed_demo_data()
            st.success("Synthetic UAT dataset loaded.")
            st.rerun()
        if d2.button("Clear demo data",use_container_width=True):
            clear_demo_data()
            st.success("Synthetic UAT dataset cleared.")
            st.rerun()
        st.caption("Synthetic DEMO-* records only · KPI logic aligned to Perenco CoW KPI Specification July 2026")

    audits=load_audits()
    if not audits:
        st.info("No submitted audits yet. Complete a test audit first.")
        return

    # Filters
    dates=[datetime.fromisoformat(a["audit_date"]) for a in audits if a["audit_date"]]
    latest=max(dates) if dates else datetime.now()
    c1,c2,c3=st.columns([1,1.2,1.5])
    year=c1.selectbox("Reporting year",sorted(set(d.year for d in dates),reverse=True) or [latest.year],index=0)
    month=c2.selectbox("Reporting month",list(range(1,13)),index=latest.month-1,format_func=lambda m:calendar.month_name[m])
    sites=sorted(set(a["site"] for a in audits if a["site"]))
    site=c3.selectbox("Site / Team",["All"]+sites)

    def in_month(a):
        if not a["audit_date"]: return False
        d=datetime.fromisoformat(a["audit_date"])
        return d.year==year and d.month==month and (site=="All" or a["site"]==site)

    month_audits=[a for a in audits if in_month(a)]
    permit=[a for a in month_audits if "Permit Quality" in a["form_name"]]
    tbt=[a for a in month_audits if "Toolbox Talk" in a["form_name"]]

    # Quarterly leadership records
    q=((month-1)//3)+1
    qmonths=list(range((q-1)*3+1,(q-1)*3+4))
    q_start=date(year,qmonths[0],1)
    q_end=date(year,qmonths[-1],calendar.monthrange(year,qmonths[-1])[1])
    today=date.today()
    quarter_complete=today>q_end
    quarter_current=(q_start<=today<=q_end)
    lead=[a for a in audits if "Leadership Engagement" in a["form_name"] and a["audit_date"] and datetime.fromisoformat(a["audit_date"]).year==year and datetime.fromisoformat(a["audit_date"]).month in qmonths and (site=="All" or a["site"]==site)]

    # Role mapping
    permit_names=sorted(set(a["auditor"] for a in audits if "Permit Quality" in a["form_name"] and a["auditor"]))
    tbt_names=sorted(set(a["auditor"] for a in audits if "Toolbox Talk" in a["form_name"] and a["auditor"]))
    lead_names=sorted(set(a["auditor"] for a in audits if "Leadership Engagement" in a["form_name"] and a["auditor"]))

    with st.expander("KPI Role Configuration",expanded=False):
        st.caption("The approved forms capture the person’s name but not the KPI reporting role. Assign each person once so submitted assurance activity is attributed to the correct KPI.")
        pc1,pc2,pc3=st.columns(3)
        pmap=get_role_mapping("permit")
        with pc1:
            st.markdown("**Permit Quality**")
            for i,n in enumerate(permit_names):
                opts=["Unmapped","Site Controller","Asset Superintendent","Other"]
                cur=pmap.get(n,"Unmapped")
                val=st.selectbox(n,opts,index=opts.index(cur) if cur in opts else 0,key=f"map-p-{i}")
                if val!=cur: set_role_mapping("permit",n,val); pmap[n]=val
        tmap=get_role_mapping("tbt")
        with pc2:
            st.markdown("**TBT / Permit / POP**")
            for i,n in enumerate(tbt_names):
                opts=["Unmapped","W2W OOE","Medic HSEA","Field Hub OIM","Other"]
                cur=tmap.get(n,"Unmapped")
                val=st.selectbox(n,opts,index=opts.index(cur) if cur in opts else 0,key=f"map-t-{i}")
                if val!=cur: set_role_mapping("tbt",n,val); tmap[n]=val
        lmap=get_role_mapping("lead")
        with pc3:
            st.markdown("**Leadership Engagement**")
            for i,n in enumerate(lead_names):
                opts=["Unmapped","Operations Director","Deputy Operations Director","Asset Superintendent","Ops Support Manager","Other"]
                cur=lmap.get(n,"Unmapped")
                val=st.selectbox(n,opts,index=opts.index(cur) if cur in opts else 0,key=f"map-l-{i}")
                if val!=cur: set_role_mapping("lead",n,val); lmap[n]=val

    reporting_period=f"{year:04d}-{month:02d}"
    gov=get_governance(reporting_period,site)
    with st.expander("KPI Review Inputs",expanded=False):
        st.caption("Required KPI criteria not captured directly by the approved assurance forms.")
        g1,g2=st.columns(2)
        with g1:
            k2_compare=st.selectbox("KPI 2 · Site self-verification vs independent assurance",
                ["Not assessed","Aligned","Significant difference"],
                index=["Not assessed","Aligned","Significant difference"].index(gov["kpi2_assurance_comparison"]))
            k2_ind_conf=st.number_input("KPI 2 · Independent assurance conformance %",0,100,
                int(gov["kpi2_independent_conformance"] or 0),
                help="Enter the relevant independent-assurance conformance result for the review period. Leave at 0 if not assessed.")
            k2_ind_find=st.number_input("KPI 2 · Independent assurance findings",0,999,int(gov["kpi2_independent_findings"]))
            k2_self_find=st.number_input("KPI 2 · Site self-verification findings",0,999,int(gov["kpi2_self_verification_findings"]))
            k3_cov=st.selectbox("KPI 3 · NUI visitation coverage",
                ["Not assessed","Reasonable","Over / under coverage"],
                index=["Not assessed","Reasonable","Over / under coverage"].index(gov["kpi3_coverage"]),
                help="Perenco requires reasonable coverage but does not define a numerical threshold.")
        with g2:
            k4_just=st.selectbox("KPI 4 · Missed-visit justification",
                ["Not required","Suitable","Outside planned quarter","Not suitable","Not provided"],
                index=["Not required","Suitable","Outside planned quarter","Not suitable","Not provided"].index(gov["kpi4_visit_justification"]))
            k4_cov=st.selectbox("KPI 4 · Field Hub OIM NUI coverage",
                ["Not assessed","Reasonable","Limited"],
                index=["Not assessed","Reasonable","Limited"].index(gov["kpi4_field_oim_coverage"]))
            k4_find=st.selectbox("KPI 4 · Level 4 TBT / Compliance Monitoring finding profile",
                ["None","Isolated / recurring minor","Significant / repeat"],
                index=["None","Isolated / recurring minor","Significant / repeat"].index(gov["kpi4_finding_profile"]))
            q1,q2=st.columns(2)
            k4_consec=q1.number_input("OIM consecutive missed quarters",0,12,int(gov["kpi4_oim_consecutive_missed"]))
            k4_12=q2.number_input("OIM missed quarters in rolling 12m",0,12,int(gov["kpi4_oim_missed_12m"]))
        if st.button("Save KPI review inputs",use_container_width=True):
            save_governance(reporting_period,site,{
                "kpi2_assurance_comparison":k2_compare,
                "kpi2_independent_conformance":None if k2_ind_conf==0 else int(k2_ind_conf),
                "kpi2_independent_findings":k2_ind_find,
                "kpi2_self_verification_findings":k2_self_find,
                "kpi3_coverage":k3_cov,
                "kpi4_visit_justification":k4_just,"kpi4_field_oim_coverage":k4_cov,
                "kpi4_finding_profile":k4_find,"kpi4_oim_consecutive_missed":k4_consec,
                "kpi4_oim_missed_12m":k4_12})
            st.success("KPI review inputs saved.")
            st.rerun()

    # KPI 1 - Site Controller Permit Non-Compliance (Tier 3)
    # Perenco requires routine and non-routine permit samples to be reported separately.
    pmap=get_role_mapping("permit")
    sc=[a for a in permit if pmap.get(a["auditor"])=="Site Controller"]
    asc=[a for a in permit if pmap.get(a["auditor"])=="Asset Superintendent"]
    wks=weeks_in_month(year,month)

    # Weekly target table from the KPI document: (routine, non-routine).
    k1_targets={
        "Dimlington":(1,1),"Cleeton":(1,1),"Ravenspurn North":(1,1),
        "Northern NUI's":(2,1),"Northern NUIs":(2,1),
        "Bacton":(1,1),"Leman 27BC":(1,1),"Leman 27B":(1,1),
        "Southern NUI's":(2,1),"Southern NUIs":(2,1)
    }
    if site!="All" and site in k1_targets:
        rt,nrt=k1_targets[site]
        k1_routine_plan=rt*wks
        k1_nonroutine_plan=nrt*wks
    elif site=="All":
        k1_routine_plan=9*wks
        k1_nonroutine_plan=7*wks
    else:
        k1_routine_plan=None
        k1_nonroutine_plan=None
    k1_plan=(k1_routine_plan+k1_nonroutine_plan) if (k1_routine_plan is not None and k1_nonroutine_plan is not None) else None

    k1_routine=[a for a in sc if permit_sample_type(a)=="Routine"]
    k1_nonroutine=[a for a in sc if permit_sample_type(a)=="Non-Routine"]
    k1_unclassified=[a for a in sc if permit_sample_type(a)=="Unclassified"]
    k1_conf=audit_conformance(sc)
    k1_pct=round(100*len(sc)/k1_plan) if (sc and k1_plan) else None
    k1_status=status_both(k1_pct,k1_conf) if (sc and k1_plan) else "Not enough data"

    # KPI 2 - Asset Superintendent Permit Non-Compliance (Tier 2)
    # One audit per week, rotationally across the nine defined asset groups.
    k2_asset_groups=[
        "Ravenspurn North","Cleeton","Northern Flying Team","Northern W2W","Dimlington",
        "27B","Southern Flying Team","Southern W2W","Bacton"
    ]
    k2_aliases={"Leman 27B":"27B","Leman 27BC":"27B","RN":"Ravenspurn North"}
    def k2_group(a):
        raw=str(a.get("site","")).strip()
        return k2_aliases.get(raw,raw) if k2_aliases.get(raw,raw) in k2_asset_groups else None

    k2_plan=wks
    k2_conf=audit_conformance(asc)
    k2_pct=round(100*len(asc)/k2_plan) if asc else None
    k2_status=status_both(k2_pct,k2_conf) if asc else "Not enough data"
    k2_routine=[a for a in asc if permit_sample_type(a)=="Routine"]
    k2_nonroutine=[a for a in asc if permit_sample_type(a)=="Non-Routine"]
    k2_unclassified=[a for a in asc if permit_sample_type(a)=="Unclassified"]
    k2_coverage=sorted(set(g for g in (k2_group(a) for a in asc) if g))

    # KPI 3 - Onshore Leadership NUI Engagement (Tier 2)
    # The source checklist states that one No/non-conformance makes the whole checklist
    # "Does not meet CoW Standard". Volume is not forced Red mid-quarter solely because
    # the quarterly target has not yet been reached.
    lmap=get_role_mapping("lead")
    valid_k3_roles=("Operations Director","Deputy Operations Director","Asset Superintendent","Ops Support Manager")
    k3_visits=len(lead)
    k3_results=[]
    for a in lead:
        v=(a.get("summary") or a.get("metadata",{}).get("overall_indicator","")).strip().lower()
        if v=="meets cow standard": k3_results.append(True)
        elif v=="does not meet cow standard": k3_results.append(False)
    k3_conf=round(100*sum(k3_results)/len(k3_results)) if k3_results else None
    k3_question_conf=question_conformance(lead)
    k3_teams=sorted(set(a["site"] for a in lead if a.get("site")))
    k3_roles=sorted(set(lmap.get(a["auditor"]) for a in lead if lmap.get(a["auditor"]) in valid_k3_roles))

    if not lead or k3_conf is None:
        k3_status="Not enough data"
    elif k3_conf<70:
        k3_status="Red"
    elif 70<=k3_conf<=89 or gov["kpi3_coverage"]=="Over / under coverage":
        k3_status="Amber"
    elif k3_visits>=3 and k3_conf>=90 and gov["kpi3_coverage"]=="Reasonable":
        k3_status="Green"
    elif quarter_complete and k3_visits<=1:
        k3_status="Red"
    elif quarter_complete and k3_visits==2:
        k3_status="Amber"
    elif not quarter_complete and k3_visits<3:
        k3_status="In progress"
    else:
        k3_status="Needs review"

    # KPI 4 - Site Leadership NUI Visits (Tier 3)
    # Uses the exact "Level 4 TBT / Compliance Monitoring" terminology.
    tmap=get_role_mapping("tbt")
    valid_k4_roles=("W2W OOE","Medic HSEA","Field Hub OIM")
    tbt_all=[a for a in audits if "Toolbox Talk" in a["form_name"] and a["audit_date"] and (site=="All" or a["site"]==site)]
    tbt_mapped=[a for a in tbt if tmap.get(a["auditor"]) in valid_k4_roles]
    tbt_unmapped=[a for a in tbt if tmap.get(a["auditor"],"Unmapped") not in valid_k4_roles]
    role_counts={r:sum(1 for a in tbt_mapped if tmap.get(a["auditor"])==r) for r in valid_k4_roles}
    q_tbt=[a for a in tbt_all if datetime.fromisoformat(a["audit_date"]).year==year and datetime.fromisoformat(a["audit_date"]).month in qmonths and tmap.get(a["auditor"]) in valid_k4_roles]
    q_field_oim=sum(1 for a in q_tbt if tmap.get(a["auditor"])=="Field Hub OIM")
    k4_conf=audit_conformance(tbt_mapped)
    k4_question_conf=question_conformance(tbt_mapped)
    ooep=round(100*role_counts["W2W OOE"]/wks) if wks else None
    medp=round(100*role_counts["Medic HSEA"]/wks) if wks else None
    has_any_k4_role=bool(tbt_mapped)
    mapping_ready=has_any_k4_role
    k4_routine=sum(1 for a in tbt_mapped if tbt_sample_type(a)=="Routine")
    k4_nonroutine=sum(1 for a in tbt_mapped if tbt_sample_type(a)=="Non-Routine")
    k4_pop=sum(1 for a in tbt_mapped if tbt_sample_type(a)=="POP")
    k4_unclassified=sum(1 for a in tbt_mapped if tbt_sample_type(a)=="Unclassified")

    prev_q_end=q_start-timedelta(days=1)
    prev_q=((prev_q_end.month-1)//3)+1
    prev_qmonths=list(range((prev_q-1)*3+1,(prev_q-1)*3+4))
    prev_q_field_oim=sum(1 for a in tbt_all if datetime.fromisoformat(a["audit_date"]).year==prev_q_end.year and datetime.fromisoformat(a["audit_date"]).month in prev_qmonths and tmap.get(a["auditor"])=="Field Hub OIM")

    if not mapping_ready or k4_conf is None:
        k4_status="Not enough data"
    else:
        ooe_state="Green" if ooep>=100 else ("Amber" if ooep>=50 else "Red")
        if medp>=100: medic_state="Green"
        elif medp>=75: medic_state="Amber"
        elif medp<50: medic_state="Red"
        else: medic_state="Needs review"  # Perenco source does not define the 50–74% band.

        finding_red=gov["kpi4_finding_profile"]=="Significant / repeat"
        finding_amber=gov["kpi4_finding_profile"]=="Isolated / recurring minor"
        l4_state="Red" if (k4_conf<70 or finding_red) else ("Amber" if (k4_conf<90 or finding_amber) else "Green")

        oim_red=int(gov["kpi4_oim_consecutive_missed"])>=2 or int(gov["kpi4_oim_missed_12m"])>2
        oim_amber=gov["kpi4_field_oim_coverage"]=="Limited" or gov["kpi4_visit_justification"]=="Outside planned quarter"

        missed_monthly=(ooep<100 or medp<100)
        missed_oim=(quarter_complete and q_field_oim<1)
        missed_target=missed_monthly or missed_oim
        justification_red=missed_target and gov["kpi4_visit_justification"] in ("Not provided","Not suitable")

        if justification_red or ooe_state=="Red" or medic_state=="Red" or l4_state=="Red" or oim_red:
            k4_status="Red"
        elif medic_state=="Needs review":
            k4_status="Needs review"
        elif ooe_state=="Green" and medic_state=="Green" and l4_state=="Green" and q_field_oim>=1 and gov["kpi4_field_oim_coverage"]=="Reasonable":
            k4_status="Green"
        elif ooe_state=="Amber" or medic_state=="Amber" or l4_state=="Amber" or oim_amber:
            k4_status="Amber"
        elif q_field_oim==0 and not quarter_complete:
            k4_status="In progress"
        elif q_field_oim==0 and quarter_complete:
            k4_status="Needs review"
        elif gov["kpi4_field_oim_coverage"]=="Not assessed":
            k4_status="Needs review"
        else:
            k4_status="Needs review"

    # KPI 5 - rolling 12-month MOI / permit-controlled incident position.
    kpi5_records=load_kpi5_summary()
    k5=kpi5_position(kpi5_records,year,month,site)

    # KPI cards
    st.markdown('<div class="dash-section-label">Executive KPI overview</div>',unsafe_allow_html=True)
    cols=st.columns(5)
    with cols[0]:
        kpi_card("KPI 1 | TIER 3","Site Controller Permit Non-Compliance","—" if k1_pct is None else f"{len(sc)} of {k1_plan} planned",k1_status,
                 "Role map required." if not sc else f"Routine {len(k1_routine)}/{k1_routine_plan} · Non-routine {len(k1_nonroutine)}/{k1_nonroutine_plan} | {k1_conf if k1_conf is not None else '—'}% audit conformance")
    with cols[1]:
        kpi_card("KPI 2 | TIER 2","Asset Superintendent Permit Non-Compliance","—" if k2_pct is None else f"{len(asc)} of {k2_plan} planned",k2_status,
                 "Role map required." if not asc else f"Routine {len(k2_routine)} · Non-routine {len(k2_nonroutine)} | {len(k2_coverage)}/9 asset groups sampled")
    with cols[2]:
        kpi_card("KPI 3 | TIER 2","Onshore Leadership NUI Engagement","—" if not lead else f"{k3_visits} of 3",k3_status,
                 "No quarter data." if not lead else f"{k3_conf if k3_conf is not None else '—'}% checklists meeting CoW standard | Q{q} {'complete' if quarter_complete else 'in progress'}")
    with cols[3]:
        if not tbt:
            k4_detail="No month data."
        elif not mapping_ready:
            k4_detail="No valid KPI 4 role-mapped audits yet."
        else:
            k4_detail=f"OOE {role_counts['W2W OOE']}/{wks} · Medic/HSEA {role_counts['Medic HSEA']}/{wks} · Field OIM {q_field_oim}/1"
            if tbt_unmapped:
                k4_detail += f" | {len(tbt_unmapped)} unmapped audit(s) excluded"
        if k4_status=="Not enough data":
            k4_headline="—"
        else:
            k4_headline=f"{role_counts['W2W OOE']}/{wks} · {role_counts['Medic HSEA']}/{wks} · {q_field_oim}/1"
            k4_detail=f"OOE · Medic/HSEA · Field OIM | Level 4 TBT / Compliance Monitoring {k4_conf}%"
            if tbt_unmapped:
                k4_detail += f" | {len(tbt_unmapped)} unmapped audit(s) excluded"
        kpi_card("KPI 4 | TIER 3","Site Leadership NUI Visits",k4_headline,k4_status,k4_detail)
    with cols[4]:
        if k5["status"]=="No data":
            kpi_card("KPI 5 | TIER 1","Increased Incidents During Permit Controlled Activity","—","No data","No KPI 5 value entered for the selected reporting period.")
        else:
            kpi_card("KPI 5 | TIER 1","Increased Incidents During Permit Controlled Activity",str(k5["count"]),k5["status"],
                     f"Rolling 12m | Previous {k5['previous']} | {k5['trend']}")

    # Leadership summary
    statuses=[k1_status,k2_status,k3_status,k4_status,k5["status"]]
    assessed=[x for x in statuses if x in ("Green","Amber","Red")]
    if "Red" in assessed: overall="RED"; css="dash-bad"
    elif "Amber" in assessed: overall="AMBER"; css="dash-warn"
    elif assessed and all(x=="Green" for x in assessed) and len(assessed)==5: overall="GREEN"; css="dash-good"
    else: overall="PARTIAL DATA"; css=""
    notes=[]

    # KPI 1 - explain the actual driver rather than repeating the RAG status.
    if k1_status in ("Amber","Red"):
        drivers=[]
        if k1_pct is not None and k1_pct < 100:
            drivers.append(f"planned Site Controller sampling delivery is {k1_pct}%")
        if k1_conf is not None and k1_conf < 90:
            drivers.append(f"whole-permit conformance is {k1_conf}%")
        if k1_unclassified:
            drivers.append(f"{len(k1_unclassified)} permit audit(s) are unclassified")
        notes.append("KPI 1: " + "; ".join(drivers) + ".")

    # KPI 2 - include delivery, conformance, rotation and assurance comparison where relevant.
    if k2_status in ("Amber","Red"):
        drivers=[]
        if k2_pct is not None and k2_pct < 100:
            drivers.append(f"Asset Superintendent sampling delivery is {k2_pct}%")
        if k2_conf is not None and k2_conf < 90:
            drivers.append(f"whole-permit conformance is {k2_conf}%")
        if len(k2_coverage) < 9:
            drivers.append(f"rotational asset coverage is {len(k2_coverage)}/9")
        if gov.get("kpi2_assurance_comparison") not in ("Not assessed","Insufficient data","Consistent"):
            drivers.append(f"self-verification / independent assurance comparison: {gov.get('kpi2_assurance_comparison')}")
        if k2_unclassified:
            drivers.append(f"{len(k2_unclassified)} permit audit(s) are unclassified")
        notes.append("KPI 2: " + "; ".join(drivers) + ".")

    # KPI 3 - make clear whether the status is caused by compliance/coverage rather than quarter progress.
    if k3_status in ("Amber","Red"):
        drivers=[]
        if k3_conf is not None and k3_conf < 90:
            drivers.append(f"leadership checklist compliance is {k3_conf}%")
        if gov.get("kpi3_coverage") in ("Over-concentrated","Under-covered"):
            drivers.append(f"NUI coverage is {gov.get('kpi3_coverage').lower()}")
        if quarter_complete and k3_visits < 3:
            drivers.append(f"quarterly engagements are {k3_visits}/3")
        elif not quarter_complete:
            drivers.append(f"Q{q} remains in progress with {k3_visits}/3 engagements recorded")
        drivers.append(f"{len(k3_teams)}/18 NUI teams engaged")
        notes.append("KPI 3: " + "; ".join(drivers) + ".")
    elif k3_status=="Needs review":
        notes.append("KPI 3: NUI coverage requires management assessment before Green can be confirmed.")

    # KPI 4 - identify the operational cause(s).
    if k4_status in ("Amber","Red"):
        drivers=[]
        if ooep is not None and ooep < 100:
            drivers.append(f"W2W OOE visit delivery is {ooep}%")
        if medp is not None and medp < 100:
            drivers.append(f"Medic/HSEA visit delivery is {medp}%")
        if k4_conf is not None and k4_conf < 90:
            drivers.append(f"Level 4 TBT / Compliance Monitoring compliance is {k4_conf}%")
        if gov.get("kpi4_finding_profile") not in ("None","Not assessed"):
            drivers.append(f"finding profile: {gov.get('kpi4_finding_profile')}")
        if gov.get("kpi4_visit_justification") == "Required - not provided":
            drivers.append("required missed-visit justification has not been provided")
        notes.append("KPI 4: " + "; ".join(drivers) + ".")
    elif k4_status=="Needs review":
        notes.append("KPI 4: management review is required for criteria that the Perenco source table does not assign an automatic RAG status.")
    elif k4_status=="In progress":
        notes.append("KPI 4: Field Hub OIM quarterly target remains open; current monthly visit and monitoring performance is shown separately.")

    if k5["status"] in ("Amber","Red"):
        notes.append(f"KPI 5: {k5['reason']}.")

    if not notes:
        notes.append("No intervention statement is generated until sufficient mapped data is available, or all five calculated KPIs are Green.")

    # Executive action line: concise synthesis of the non-Green picture.
    action_parts=[]
    if k1_status in ("Amber","Red") or k2_status in ("Amber","Red"):
        action_parts.append("recover planned permit assurance sampling")
    if (k1_conf is not None and k1_conf < 90) or (k2_conf is not None and k2_conf < 90):
        action_parts.append("address permit conformance weaknesses")
    if k3_conf is not None and k3_conf < 90:
        action_parts.append("review leadership checklist non-conformances")
    if k4_conf is not None and k4_conf < 90:
        action_parts.append("review Level 4 TBT / Compliance Monitoring weaknesses")
    if k5["status"] in ("Amber","Red"):
        action_parts.append("review the rolling 12-month permit-controlled incident trend")

    action_line = ""
    if action_parts:
        action_line = "<br><br><b>Leadership focus:</b> " + "; ".join(action_parts) + "."

    st.markdown(
        f'<div class="dash-note {css}"><b>Overall assurance position: {overall}</b><br>'
        + "<br>".join(notes)
        + action_line
        + '</div>',
        unsafe_allow_html=True
    )

    # Detail tabs
    st.markdown('<div class="dash-section-label">Performance detail & evidence</div>',unsafe_allow_html=True)
    tab1,tab2,tab3,tab4,tab5=st.tabs(["KPI Detail","Non-Compliances & SMART Actions","Weakest Questions","Audit Trail","KPI 5 Incidents"])
    with tab1:
        with st.expander("KPI Criteria", expanded=False):
            st.markdown("""
**KPI 1 – Site Controller (Tier 3)**  
Site-specific weekly routine/non-routine permit sampling. Green: ≥100% required audits completed **and** ≥90% audit conformance. Amber: 70–90% completion and/or 70–89% conformance. Red: <70% completion and/or <70% conformance.

**KPI 2 – Asset Superintendent (Tier 2)**  
Minimum 1 permit audit per week on a rotational basis. Same completion/conformance thresholds as KPI 1. Review also considers site self-verification performance against independent assurance findings.

**KPI 3 – Onshore Leadership (Tier 2)**  
Minimum 3 NUI engagements per quarter. Green also requires 90–100% checklist compliance and reasonable NUI coverage. Amber: 2 engagements and/or 70–89% compliance and/or over/under coverage. Red: 1 or fewer engagements and/or <70% compliance.

**KPI 4 – Site Leadership (Tier 3)**  
W2W OOE: minimum 1/week. Medic/HSEA: minimum 1/week. Field Hub OIM: minimum 1/quarter. Level 4 TBT / Compliance Monitoring: Green ≥90%, Amber 70–89%, Red <70%. Missed-visit justification, NUI coverage, repeat/significant findings and Field Hub OIM missed-quarter rules also affect status.

**KPI 5 – Increased Incidents During Permit Controlled Activity (Tier 1)**  
Rolling 12-month MOI trend. Green: no increase and no serious/repeat trigger. Amber: increasing trend or a single HiPO, significant injury, Loss of Containment or repeat event theme. Red: significant increase, multiple serious events, major Loss of Containment or recurring permit-control failure.
""")
        st.markdown("### Company & Site Performance")
        st.caption("Use the company view for the overall PUK position and the site view to see where assurance delivery and conformance are concentrated.")

        company_tab, site_tab = st.tabs(["Company KPIs", "Site KPIs"])

        with company_tab:
            c1,c2,c3,c4=st.columns(4)
            c1.metric("Site Controller groups","7")
            c2.metric("KPI 1 planned audits",k1_plan if k1_plan is not None else "—")
            c3.metric("KPI 2 asset coverage",f"{len(k2_coverage)} / 9")
            c4.metric("Overall assurance position",overall)
            st.caption("Company KPIs aggregate the applicable PUK sampling groups and leadership measures. KPI 2 remains a company-wide rotational requirement rather than a separate target for every site.")

        with site_tab:
            site_groups=[
                ("Dimlington",1,1),
                ("Cleeton",1,1),
                ("Ravenspurn North",1,1),
                ("Northern NUI's",2,1),
                ("Bacton",1,1),
                ("Leman 27BC",1,1),
                ("Southern NUI's",2,1),
            ]

            def site_kpi_name(v):
                x=str(v or "").strip().lower().replace("’","'")
                aliases={
                    "dimlington":"Dimlington",
                    "cleeton":"Cleeton",
                    "ravenspurn north":"Ravenspurn North",
                    "rn":"Ravenspurn North",
                    "northern nui's":"Northern NUI's",
                    "northern nuis":"Northern NUI's",
                    "northern nui":"Northern NUI's",
                    "bacton":"Bacton",
                    "leman 27bc":"Leman 27BC",
                    "leman 27b":"Leman 27BC",
                    "27bc":"Leman 27BC",
                    "27b":"Leman 27BC",
                    "southern nui's":"Southern NUI's",
                    "southern nuis":"Southern NUI's",
                    "southern nui":"Southern NUI's",
                }
                return aliases.get(x,str(v or "").strip())

            company_month_audits=[
                a for a in audits
                if a.get("audit_date")
                and datetime.fromisoformat(a["audit_date"]).year==year
                and datetime.fromisoformat(a["audit_date"]).month==month
            ]
            company_permit=[
                a for a in company_month_audits
                if "Permit Quality" in a["form_name"]
                and pmap.get(a["auditor"])=="Site Controller"
            ]

            site_rows=[]
            for site_name,rpw,npw in site_groups:
                sa=[x for x in company_permit if site_kpi_name(x.get("site"))==site_name]
                sr=[x for x in sa if permit_sample_type(x)=="Routine"]
                sn=[x for x in sa if permit_sample_type(x)=="Non-Routine"]
                rplan=rpw*wks
                nplan=npw*wks
                total_plan=rplan+nplan
                pp=round(100*len(sa)/total_plan) if total_plan else None
                cf=audit_conformance(sa)
                rag=status_both(pp,cf) if pp is not None and cf is not None else "No data"
                site_rows.append({
                    "Site / Group":site_name,
                    "Routine completed":len(sr),
                    "Routine planned":rplan,
                    "Non-routine completed":len(sn),
                    "Non-routine planned":nplan,
                    "Plan completion":f"{pp}%" if pp is not None else "—",
                    "Whole-permit conformance":f"{cf}%" if cf is not None else "—",
                    "Status":rag,
                })

            site_df=pd.DataFrame(site_rows)
            covered=sum(1 for r in site_rows if (r["Routine completed"]+r["Non-routine completed"])>0)
            a,b,c=st.columns(3)
            a.metric("Site sampling coverage",f"{covered} of 7")
            b.metric("Sites with audit activity",covered)
            c.metric("Sites with no audit activity",7-covered)

            st.markdown("#### Site Controller KPI 1 comparison")
            st.caption("Seven-site comparison of planned sampling delivery and whole-permit conformance for the selected reporting period.")

            site_display=site_df.copy()
            site_display["Routine audits"]=site_display.apply(
                lambda r:f'{r["Routine completed"]} of {r["Routine planned"]} planned',axis=1
            )
            site_display["Non-routine audits"]=site_display.apply(
                lambda r:f'{r["Non-routine completed"]} of {r["Non-routine planned"]} planned',axis=1
            )
            site_display=site_display[
                ["Site / Group","Routine audits","Non-routine audits",
                 "Plan completion","Whole-permit conformance","Status"]
            ]

            st.dataframe(
                site_display,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Site / Group":st.column_config.TextColumn("Site / Group",width="medium"),
                    "Routine audits":st.column_config.TextColumn("Routine audits",width="medium"),
                    "Non-routine audits":st.column_config.TextColumn("Non-routine audits",width="medium"),
                    "Plan completion":st.column_config.TextColumn("Plan completion",width="small"),
                    "Whole-permit conformance":st.column_config.TextColumn("Permit conformance",width="small"),
                    "Status":st.column_config.TextColumn("RAG",width="small"),
                },
            )

            red_sites=[r["Site / Group"] for r in site_rows if r["Status"]=="Red"]
            amber_sites=[r["Site / Group"] for r in site_rows if r["Status"]=="Amber"]
            no_data_sites=[r["Site / Group"] for r in site_rows if r["Status"]=="No data"]

            if red_sites:
                st.error("Sites requiring intervention: "+", ".join(red_sites))
            if amber_sites:
                st.warning("Sites requiring review: "+", ".join(amber_sites))
            if no_data_sites:
                st.info("No KPI 1 audit data recorded: "+", ".join(no_data_sites))

            st.caption(
                "Site KPIs use the same KPI 1 weekly sampling requirements as the company calculation. "
                "The site comparison is diagnostic and does not create a separate KPI target. "
                "Company and site results reconcile to the same assurance records."
            )

        st.markdown("---")
        c1,c2=st.columns(2)
        with c1:
            st.markdown("### KPI 1 · Site Controller")
            a,b=st.columns(2)
            a.metric("Audits completed",len(sc) if sc else "—")
            b.metric("Required audits for selected period",k1_plan if k1_plan else "—")
            a.metric("Routine audits",f"{len(k1_routine)} of {k1_routine_plan} planned" if k1_routine_plan is not None else "—")
            b.metric("Non-routine audits",f"{len(k1_nonroutine)} of {k1_nonroutine_plan} planned" if k1_nonroutine_plan is not None else "—")
            a.metric("Plan completion",f"{k1_pct}%" if k1_pct is not None else "—")
            b.metric("Whole-permit conformance",f"{k1_conf}%" if k1_conf is not None else "—")
            if k1_unclassified:
                st.warning(f"{len(k1_unclassified)} KPI 1 permit audit(s) are unclassified as Routine or Non-Routine and should be corrected.")
            if site=="All" and k1_plan:
                st.caption("All sites selected: target is the aggregate of the seven Site Controller sampling groups. The monthly total is an implementation conversion of the source weekly requirement.")
            st.caption(f"Reporting basis used by this UAT: {wks} calendar reporting weeks. Perenco defines the requirement weekly but does not prescribe a monthly conversion method.")

            st.markdown("### KPI 3 · Onshore Leadership")
            a,b=st.columns(2)
            a.metric("Engagements",f"{k3_visits} of 3" if lead else "—")
            b.metric("Checklists meeting CoW standard",f"{k3_conf}%" if k3_conf is not None else "—")
            a.metric("NUI teams engaged",f"{len(k3_teams)} / 18" if lead else "—")
            b.metric("Quarter",f"Q{q} · {'Complete' if quarter_complete else 'In progress'}" if lead else "—")
            a.metric("Leadership roles visible",f"{len(k3_roles)} / 4" if lead else "—")
            b.metric("Coverage assessment",gov["kpi3_coverage"])
            st.caption("Perenco requires reasonable coverage across the 18 NUI teams (12 W2W and 6 Flying Teams). No numerical coverage threshold has been invented.")

        with c2:
            st.markdown("### KPI 2 · Asset Superintendent")
            a,b=st.columns(2)
            a.metric("Audits completed",len(asc) if asc else "—")
            b.metric("Required audits for selected period",k2_plan)
            a.metric("Routine samples",len(k2_routine) if asc else "—")
            b.metric("Non-routine samples",len(k2_nonroutine) if asc else "—")
            a.metric("Plan completion",f"{k2_pct}%" if k2_pct is not None else "—")
            b.metric("Whole-permit conformance",f"{k2_conf}%" if k2_conf is not None else "—")
            a.metric("Rotational asset coverage",f"{len(k2_coverage)} / 9")
            b.metric("Independent assurance conformance",f"{gov['kpi2_independent_conformance']}%" if gov["kpi2_independent_conformance"] is not None else "Not assessed")
            a.metric("Self-verification findings",gov["kpi2_self_verification_findings"])
            b.metric("Independent findings",gov["kpi2_independent_findings"])
            if k2_unclassified:
                st.warning(f"{len(k2_unclassified)} KPI 2 permit audit(s) are unclassified as Routine or Non-Routine.")
            st.caption(f"Minimum 1 permit audit per week on a rotational basis across RN, Cleeton, Northern Flying Team, Northern W2W, Dimlington, 27B, Southern Flying Team, Southern W2W and Bacton. Alignment review: {gov['kpi2_assurance_comparison']}.")

            st.markdown("### KPI 4 · Site Leadership")
            a,b=st.columns(2)
            a.metric("W2W OOE",f"{role_counts['W2W OOE']} / {wks} ({ooep}%)" if mapping_ready else "Not mapped")
            b.metric("Medic / HSEA",f"{role_counts['Medic HSEA']} / {wks} ({medp}%)" if mapping_ready else "Not mapped")
            a.metric("Field Hub OIM",f"{q_field_oim} / 1 quarter" if mapping_ready else "Not mapped")
            b.metric("Level 4 TBT / Compliance Monitoring",f"{k4_conf}%" if (mapping_ready and k4_conf is not None) else "—")
            s1,s2,s3=st.columns(3)
            s1.metric("Routine samples",k4_routine if mapping_ready else "—")
            s2.metric("Non-routine samples",k4_nonroutine if mapping_ready else "—")
            s3.metric("POP samples",k4_pop if mapping_ready else "—")
            a,b=st.columns(2)
            a.metric("Missed-visit justification",gov["kpi4_visit_justification"])
            b.metric("Field Hub OIM coverage",gov["kpi4_field_oim_coverage"])
            st.caption(f"Finding profile: {gov['kpi4_finding_profile']}. OIM missed-quarter history: {gov['kpi4_oim_consecutive_missed']} consecutive; {gov['kpi4_oim_missed_12m']} in rolling 12 months. The Medic/HSEA 50–74% band remains 'Needs review' because the source table does not assign a RAG status to that range.")

    with tab2:
        findings=[]
        for a in month_audits:
            for r in a["responses"]:
                if str(r.get("response","")).strip().lower()=="no":
                    findings.append({"Audit ID":a["audit_id"],"Date":a["audit_date"],"Site / Team":a["site"],"Form":a["form_name"],"Auditor":a["auditor"],"Question":r.get("question",""),"Comments / Evidence":r.get("comments_evidence",""),"SMART Action":r.get("smart_action","")})
        if findings: st.dataframe(pd.DataFrame(findings),use_container_width=True,hide_index=True)
        else: st.info("No No-responses in the selected month/site view.")

    with tab3:
        q={}
        for a in month_audits:
            for r in a["responses"]:
                v=str(r.get("response","")).strip().lower()
                if v not in ("yes","no"): continue
                key=r.get("question","")
                q.setdefault(key,{"Yes":0,"No":0})
                q[key]["Yes" if v=="yes" else "No"]+=1
        weak=[]
        for question,v in q.items():
            total=v["Yes"]+v["No"]; conf=round(100*v["Yes"]/total) if total else None
            weak.append({"Question":question,"Conformance %":conf,"No responses":v["No"],"Responses":total})
        weak=sorted(weak,key=lambda x:(x["Conformance %"],-x["No responses"]))[:15]
        if weak: st.dataframe(pd.DataFrame(weak),use_container_width=True,hide_index=True)
        else: st.info("No Yes/No response data in this view.")

    with tab4:
        rows=[]
        for a in month_audits:
            rows.append({"Audit ID":a["audit_id"],"Date":a["audit_date"],"Site / Team":a["site"],"Form":a["form_name"],"Auditor":a["auditor"],"Reference":a["reference"],"Result":audit_result(a) or "—"})
        if rows: st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
        else: st.info("No audits in this view.")

    with tab5:
        st.markdown("### KPI 5 · Increased Incidents During Permit Controlled Activity")
        if k5["status"]=="No data":
            st.info("No KPI 5 value has been entered for the selected reporting period.")
        else:
            c1,c2,c3,c4=st.columns(4)
            c1.metric("Rolling 12-month MOIs",k5["count"])
            c2.metric("Previous rolling 12-month",k5["previous"])
            c3.metric("Trend",k5["trend"])
            c4.metric("KPI status",k5["status"])
            st.caption("Perenco KPI 5: Green = no increase and no serious/repeat trigger; Amber = increasing trend or a single HiPO/significant injury/LOC/repeat theme; Red = significant increase, multiple serious events, major LOC or recurring permit-control failure.")
            st.caption(k5["reason"])
            if k5.get("record",{}).get("comments"):
                st.markdown(f"**KPI comment:** {k5['record']['comments']}")


page=st.sidebar.radio("Navigation",["Dashboard","KPI 5 Data","Permit Quality","Toolbox Talk / Permit / POP","Leadership Engagement","Submitted Audits","Dashboard Export"])
enable_scroll_to_top()

if page=="KPI 5 Data":
    render_kpi5_input()

elif page=="Permit Quality":
    banner("SELF VERIFICATION - LEVEL 4 MONITORING","Control of Work:  Permit Quality")
    meta=header_ptw()
    purpose("This monitoring activity is intended to verify day-to-day compliance with Permit-to-Work requirements, ensuring that permits and supporting risk assessments are suitable and sufficient for the task, safe working practices are consistently applied, and gaps in knowledge or understanding that could lead to hazardous errors are identified and addressed. The activity is designed for leadership roles (AA, Site Controller, Asset Superintendent) to strengthen oversight, promote engagement, and provide leadership assurance of Permit-to-Work effectiveness.")
    st.markdown('<div class="blackbar">QUESTION</div>',unsafe_allow_html=True)
    rs=render_monitoring_sections("ptw",DATA["ptw"])
    st.markdown('<div class="blackbar">ENTER THIS AUDIT INTO PTRAC, LOG FINDINGS IN THE AUDIT PLAN & ENSURE EACH NON-COMPLIANCE GENERATES A RECORDED SMART ACTION</div>',unsafe_allow_html=True)
    if st.button("Submit Permit Quality Audit",type="primary",use_container_width=True):
        blanks=[r for r in rs if r["response"] is None]
        if not meta["site"] or not meta["auditor"]: st.error("Complete SITE / INSTALLATION and AUDITOR.")
        elif bool(meta.get("new_wcc"))==bool(meta.get("routine")):
            st.error("Select exactly one classification: New WCC (Non-Routine) or Routine. The audit cannot be submitted until it is classified for KPI reporting.")
        elif blanks:
            st.error(f"{len(blanks)} question(s) still require a response. Taking you to the first unanswered question.")
            jump_to(blanks[0]["anchor"])
        else: st.success("Submitted: "+save("Control of Work: Permit Quality",meta,rs))

elif page=="Toolbox Talk / Permit / POP":
    banner("SELF VERIFICATION - LEVEL 4 MONITORING","Control of Work:  Toolbox Talk, Permit Compliance & Operating Procedures")
    meta=header_tbt()
    purpose("This monitoring activity is intended to be used to self-verify the day-to-day compliance of TBT & Permits Compliance. Ensuring the TBT is suitable for the tasks outlined in the permit and operating procedure, reinforcing safe working practices and identify gaps in team knowledge that could lead to hazardous mistakes. This assurance activity is designed for leadership roles (HSEA, OTL, W2W OOE & Site Controller) to strengthen oversight, promote engagement, and provide leadership assurance of Permit-to-Work effectiveness,")
    st.markdown('<div class="blackbar">QUESTION <span style="margin-left:18%">Site Visit is Required – Sequential Review: TBT followed by Permit Compliance or POP</span></div>',unsafe_allow_html=True)
    activity=meta.get("activity_type")
    rs=render_monitoring_sections("tbt-q1-2",DATA["tbt"][:2])
    st.markdown('<div class="blackbar">AUDITING A POP? MOVE TO QUESTION 8</div>',unsafe_allow_html=True)
    if activity=="POP":
        rs += render_monitoring_sections("tbt-pop-q8",[DATA["pop"]])
    else:
        rs += render_monitoring_sections("tbt-q3-7",DATA["tbt"][2:])
        rs += render_monitoring_sections("tbt-q8",[DATA["pop"]])
    st.markdown('<div class="blackbar">ENTER THIS AUDIT INTO PTRAC, LOG FINDINGS IN THE AUDIT PLAN & ENSURE EACH NON-COMPLIANCE GENERATES A RECORDED SMART ACTION</div>',unsafe_allow_html=True)
    if st.button("Submit TBT / Permit / POP Audit",type="primary",use_container_width=True):
        blanks=[r for r in rs if r["response"] is None]
        if not meta["site"] or not meta["auditor"] or not activity: st.error("Complete SITE / INSTALLATION, AUDITOR and select New WCC, Routine or POP.")
        elif blanks:
            st.error(f"{len(blanks)} displayed question(s) still require a response. Taking you to the first unanswered question.")
            jump_to(blanks[0]["anchor"])
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
            anchor=f"q-lead-{si}-{qi}"
            st.markdown(f'<div id="{anchor}" class="qrow">{q}</div>',unsafe_allow_html=True)
            if section=="Learning & Continuous Improvement" and q.startswith("Can personnel suggest"):
                comment=st.text_area("Comments / Evidence",key=f"lead-{si}-{qi}-c",height=70)
                ans="Comment"
            else:
                ans=st.radio("Response",["Yes","No"],index=None,horizontal=True,key=f"lead-{si}-{qi}-a",label_visibility="collapsed")
                comment=st.text_input("COMMENTS / EVIDENCE",key=f"lead-{si}-{qi}-c",placeholder="Enter comments / evidence")
            rs.append({"section":section,"question":q,"response":ans,"comments_evidence":comment,"anchor":anchor})
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
        elif blanks:
            st.error(f"{len(blanks)} question(s) still require a response. Taking you to the first unanswered question.")
            jump_to(blanks[0]["anchor"])
        elif indicator is None:
            st.error("Select the Overall Control of Work Indicator.")
        else:
            meta={"site":site,"audit_date":str(ad),"auditor":leader,"site_controller":sc,"reference":"","positive_observations":positive,"opportunities_for_improvement":improvement,"actions_agreed":actions,"auditor_notes":notes,"overall_indicator":indicator}
            st.success("Submitted: "+save("Control of Work Leadership Engagement Checklist",meta,rs,indicator))

elif page=="Dashboard":
    render_dashboard()

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
