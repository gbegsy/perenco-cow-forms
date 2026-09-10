
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
.block-container{max-width:1250px;padding-top:2.25rem;padding-bottom:3rem}
div[data-testid="stSidebar"]{background:#f4f5f7}
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

def weeks_in_month(year,month):
    cal=calendar.monthcalendar(year,month)
    return sum(1 for wk in cal if wk[calendar.MONDAY] != 0)

def status_both(plan_pct, conf):
    if plan_pct is None or conf is None: return "Not enough data"
    if plan_pct < 70 or conf < 70: return "Red"
    if plan_pct >= 100 and conf >= 90: return "Green"
    return "Amber"

def status_class(s):
    return {"Green":"green","Amber":"amber","Red":"red"}.get(s,"")

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
        ]
    ))
    records.append(rec(
        "DEMO-PQ-SC-002","Control of Work: Permit Quality","Dimlington","Demo Site Controller","DEMO-WCC-SC-002",
        [
            {"section":"1. Planning","item":"a","question":"Is the activity planned to be undertaken outside the next 24 hours?","response":"Yes","smart_action":""},
            {"section":"1. Planning","item":"b","question":"Has the WCC been discussed in the daily permit meeting?","response":"Yes","smart_action":""},
            {"section":"2. Raising a NEW WCC","item":"a","question":"Is there a brief, clear and concise summary of scope?","response":"Yes","smart_action":""},
        ]
    ))

    # KPI 2 - Asset Superintendent Permit Quality
    records.append(rec(
        "DEMO-PQ-AS-001","Control of Work: Permit Quality","Ravenspurn North","Demo Asset Superintendent","DEMO-WCC-AS-001",
        [
            {"section":"1. Planning","item":"a","question":"Is the activity planned to be undertaken outside the next 24 hours?","response":"Yes","smart_action":""},
            {"section":"4. Identifying the Correct WCC","item":"a","question":"Has the correct Type of WCC been selected appropriate for the task?","response":"Yes","smart_action":""},
            {"section":"12. Isolation Requirements","item":"a","question":"Have all controls within the ICC been acknowledged and transferred to the WCC?","response":"Yes","smart_action":""},
        ]
    ))

    # KPI 4 - W2W OOE and Medic/HSEA visits
    records.append(rec(
        "DEMO-TBT-OOE-001","Control of Work: Toolbox Talk, Permit Compliance & Operating Procedures","Northern W2W","Demo W2W OOE","DEMO-TBT-OOE-001",
        [
            {"section":"1. TBT Hazard Identification","item":"a","question":"TBT Lead discusses the hazards and controls associated to the task/activity","response":"Yes","smart_action":""},
            {"section":"4. Permit Compliance","item":"a","question":"Is there an up-to-date copy of the WCC at the worksite and signed by all members of the work party?","response":"No","smart_action":"Confirm the current WCC is available at the worksite and obtain all required signatures."},
        ]
    ))
    records.append(rec(
        "DEMO-TBT-HSEA-001","Control of Work: Toolbox Talk, Permit Compliance & Operating Procedures","Southern W2W","Demo Medic HSEA","DEMO-TBT-HSEA-001",
        [
            {"section":"1. TBT Hazard Identification","item":"a","question":"TBT Lead discusses the hazards and controls associated to the task/activity","response":"Yes","smart_action":""},
            {"section":"3. Hazards associated to the Worksite and Equipment","item":"c","question":"Are all access and egress points checked and clear?","response":"Yes","smart_action":""},
        ]
    ))
    records.append(rec(
        "DEMO-TBT-OIM-001","Control of Work: Toolbox Talk, Permit Compliance & Operating Procedures","Cleeton","Demo Field Hub OIM","DEMO-TBT-OIM-001",
        [
            {"section":"1. TBT Hazard Identification","item":"a","question":"TBT Lead discusses the hazards and controls associated to the task/activity","response":"Yes","smart_action":""},
            {"section":"4. Permit Compliance","item":"a","question":"Is there an up-to-date copy of the WCC at the worksite and signed by all members of the work party?","response":"Yes","smart_action":""},
        ]
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
    c.commit()
    c.close()

def clear_demo_data():
    c=conn()
    c.execute("DELETE FROM audits WHERE audit_id LIKE 'DEMO-%'")
    c.execute("DELETE FROM role_mapping WHERE person_name LIKE 'Demo %'")
    c.commit()
    c.close()

def render_dashboard():
    st.markdown("""
    <style>
    .dash-title{font-size:30px;font-weight:800;margin:0 0 4px;color:#16324a}
    .dash-sub{color:#65798c;margin-bottom:16px}
    .kpi{background:#fff;border:1px solid #d7e0e8;border-top:4px solid #a9b6c0;border-radius:10px;padding:14px;min-height:165px;box-shadow:0 2px 10px rgba(16,42,67,.05)}
    .kpi.green{border-top-color:#16865b}.kpi.amber{border-top-color:#b97500}.kpi.red{border-top-color:#c43b3b}
    .kpi h3{font-size:10px;margin:0;color:#65798c;text-transform:uppercase;letter-spacing:.5px}
    .kpi .name{font-weight:700;margin:6px 0 2px;color:#17283a}
    .kpi .num{font-size:27px;font-weight:800;margin:10px 0 6px;color:#17283a}
    .kpi .detail{font-size:11px;color:#65798c;line-height:1.35;margin-top:7px}
    .badge{display:inline-block;padding:4px 8px;border-radius:14px;font-size:10px;font-weight:800;background:#edf1f4;color:#62717d}
    .green .badge{background:#e9f6ef;color:#16865b}.amber .badge{background:#fff4dc;color:#b97500}.red .badge{background:#fdecec;color:#c43b3b}
    .dash-note{padding:12px 14px;border-radius:8px;background:#edf5fb;border-left:4px solid #1679c4;line-height:1.45}
    .dash-warn{background:#fff4dc;border-left-color:#b97500}.dash-bad{background:#fdecec;border-left-color:#c43b3b}.dash-good{background:#e9f6ef;border-left-color:#16865b}
    </style>
    """,unsafe_allow_html=True)
    st.markdown('<div class="dash-title">Control of Work KPI Dashboard</div>',unsafe_allow_html=True)
    st.markdown('<div class="dash-sub">Control of Work Assurance – KPI Performance & Leadership Oversight</div>',unsafe_allow_html=True)

    d1,d2,_=st.columns([1.2,1.2,5])
    if d1.button("Load UAT demo data",use_container_width=True):
        seed_demo_data()
        st.success("Synthetic UAT dataset loaded.")
        st.rerun()
    if d2.button("Clear demo data",use_container_width=True):
        clear_demo_data()
        st.success("Synthetic UAT dataset cleared.")
        st.rerun()
    st.caption("Demo records are prefixed DEMO-* and are synthetic. They exist only to test KPI behaviour.")

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

    # KPI 1
    pmap=get_role_mapping("permit")
    sc=[a for a in permit if pmap.get(a["auditor"])=="Site Controller"]
    asc=[a for a in permit if pmap.get(a["auditor"])=="Asset Superintendent"]
    wks=max(4,weeks_in_month(year,month))
    site_targets={
        "Dimlington":2,"Cleeton":2,"Ravenspurn North":2,"Northern NUI's":3,"Northern NUIs":3,
        "Bacton":2,"Leman 27BC":2,"Leman 27B":2,"Southern NUI's":3,"Southern NUIs":3
    }
    if site!="All" and site in site_targets:
        k1_plan=site_targets[site]*wks
    elif site=="All":
        # 7 defined site groupings: 2+2+2+3+2+2+3 = 16 audits/week
        k1_plan=16*wks
    else:
        k1_plan=None
    k1_conf=audit_conformance(sc)
    k1_pct=round(100*len(sc)/k1_plan) if (sc and k1_plan) else None
    k1_status=status_both(k1_pct,k1_conf) if (sc and k1_plan) else "Not enough data"

    # KPI 2
    k2_plan=wks
    k2_conf=audit_conformance(asc)
    k2_pct=round(100*len(asc)/k2_plan) if asc else None
    k2_status=status_both(k2_pct,k2_conf) if asc else "Not enough data"

    # KPI 3 - use the Leadership form's required Overall CoW Indicator.
    # The source form states that one No/non-conformance makes the checklist "Does not meet CoW Standard".
    k3_visits=len(lead)
    k3_results=[]
    for a in lead:
        v=(a.get("summary") or a.get("metadata",{}).get("overall_indicator","")).strip().lower()
        if v=="meets cow standard": k3_results.append(True)
        elif v=="does not meet cow standard": k3_results.append(False)
    k3_conf=round(100*sum(k3_results)/len(k3_results)) if k3_results else None
    k3_question_conf=question_conformance(lead)
    if not lead or k3_conf is None:
        k3_status="Not enough data"
    elif not quarter_complete:
        k3_status="In progress"
    elif k3_conf<70:
        k3_status="Red"
    elif k3_visits>=3 and k3_conf>=90:
        k3_status="Green"
    elif k3_visits==2:
        k3_status="Amber"
    else:
        k3_status="Red"

    # KPI 4 - calculate from valid role-mapped Level 4 records.
    # Unmapped records are flagged separately instead of blocking valid mapped evidence.
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

    # Prior-quarter Field Hub OIM count supports the two-consecutive-quarter Red rule.
    prev_q_end=q_start-timedelta(days=1)
    prev_q= ((prev_q_end.month-1)//3)+1
    prev_qmonths=list(range((prev_q-1)*3+1,(prev_q-1)*3+4))
    prev_q_field_oim=sum(1 for a in tbt_all if datetime.fromisoformat(a["audit_date"]).year==prev_q_end.year and datetime.fromisoformat(a["audit_date"]).month in prev_qmonths and tmap.get(a["auditor"])=="Field Hub OIM")

    if not mapping_ready or k4_conf is None:
        k4_status="Not enough data"
    else:
        weekly_pcts=[]
        if role_counts["W2W OOE"]>0: weekly_pcts.append(ooep)
        if role_counts["Medic HSEA"]>0: weekly_pcts.append(medp)

        if k4_conf<70 or any(p<50 for p in weekly_pcts):
            k4_status="Red"
        elif q_field_oim==0 and quarter_complete and prev_q_field_oim==0:
            k4_status="Red"
        elif k4_conf>=90 and weekly_pcts and all(p>=100 for p in weekly_pcts) and q_field_oim>=1:
            k4_status="Green"
        elif not quarter_complete and k4_conf>=90 and weekly_pcts and all(p>=100 for p in weekly_pcts) and q_field_oim==0:
            k4_status="In progress"
        else:
            k4_status="Amber"

    # KPI cards
    cols=st.columns(5)
    with cols[0]:
        kpi_card("KPI 1 | TIER 3","Site Controller Permit Non-Compliance","—" if k1_pct is None else f"{k1_pct}%",k1_status,
                 "Role map required." if not sc else f"{len(sc)}/{k1_plan or '—'} planned | {k1_conf if k1_conf is not None else '—'}% audit conformance")
    with cols[1]:
        kpi_card("KPI 2 | TIER 2","Asset Superintendent Permit Non-Compliance","—" if k2_pct is None else f"{k2_pct}%",k2_status,
                 "Role map required." if not asc else f"{len(asc)}/{k2_plan} planned | {k2_conf if k2_conf is not None else '—'}% audit conformance")
    with cols[2]:
        kpi_card("KPI 3 | TIER 2","Onshore Leadership NUI Engagement","—" if not lead else f"{k3_visits} of 3",k3_status,
                 "No quarter data." if not lead else f"{k3_conf if k3_conf is not None else '—'}% checklists meeting CoW standard | Q{q} {'complete' if quarter_complete else 'in progress'}")
    with cols[3]:
        if not tbt:
            k4_detail="No month data."
        elif not mapping_ready:
            k4_detail="No valid KPI 4 role-mapped audits yet."
        else:
            k4_detail=f"OOE {role_counts['W2W OOE']}/{wks}; Medic/HSEA {role_counts['Medic HSEA']}/{wks}; Field OIM {q_field_oim}/1 this quarter"
            if tbt_unmapped:
                k4_detail += f" | {len(tbt_unmapped)} unmapped audit(s) excluded"
        kpi_card("KPI 4 | TIER 3","Site Leadership NUI Visits","—" if k4_status=="Not enough data" else f"{k4_conf}%",k4_status,k4_detail)
    with cols[4]:
        kpi_card("KPI 5 | TIER 1","Permit-Controlled Incidents","—","Not connected","MOI source not yet connected. KPI 5 remains outside the assurance forms.")

    # Leadership summary
    statuses=[k1_status,k2_status,k3_status,k4_status]
    assessed=[x for x in statuses if x in ("Green","Amber","Red")]
    if "Red" in assessed: overall="RED"; css="dash-bad"
    elif "Amber" in assessed: overall="AMBER"; css="dash-warn"
    elif assessed and all(x=="Green" for x in assessed) and len(assessed)==4: overall="GREEN"; css="dash-good"
    else: overall="PARTIAL DATA"; css=""
    notes=[]
    if k1_status in ("Amber","Red"): notes.append(f"KPI 1 is {k1_status}: review Site Controller sampling delivery and permit conformance.")
    if k2_status in ("Amber","Red"): notes.append(f"KPI 2 is {k2_status}: review Asset Superintendent sampling delivery and permit conformance.")
    if k3_status in ("Amber","Red"): notes.append(f"KPI 3 is {k3_status}: review quarterly engagement volume, checklist conformance and NUI coverage.")
    elif k3_status=="In progress": notes.append(f"KPI 3: Q{q} is in progress — {k3_visits} of 3 engagements completed; {k3_conf if k3_conf is not None else '—'}% of completed checklists currently meet the CoW standard.")
    if k4_status in ("Amber","Red"): notes.append(f"KPI 4 is {k4_status}: review site leadership visit delivery and Level 4 monitoring conformance.")
    elif k4_status=="In progress": notes.append(f"KPI 4: reporting period is in progress; weekly visit delivery and conformance are on track, with Field Hub OIM quarter delivery still open.")
    if not notes: notes.append("No intervention statement is generated until sufficient mapped data is available, or all calculated KPIs are Green.")
    st.markdown(f'<div class="dash-note {css}"><b>Overall position: {overall}</b><br>'+"<br>".join(notes)+'</div>',unsafe_allow_html=True)

    # Detail tabs
    tab1,tab2,tab3,tab4=st.tabs(["KPI Detail","Non-Compliances & SMART Actions","Weakest Questions","Audit Trail"])
    with tab1:
        c1,c2=st.columns(2)
        with c1:
            st.subheader("KPI 1 – Site Controller")
            a,b=st.columns(2)
            a.metric("Audits completed",len(sc) if sc else "—")
            b.metric("Planned audits",k1_plan if k1_plan else "—")
            a.metric("Plan completion",f"{k1_pct}%" if k1_pct is not None else "—")
            b.metric("Audit conformance",f"{k1_conf}%" if k1_conf is not None else "—")
            st.caption("Status is only calculated once Site Controller audits are role-mapped.")

            st.subheader("KPI 3 – Onshore Leadership")
            a,b=st.columns(2)
            a.metric("Engagements",f"{k3_visits} of 3" if lead else "—")
            b.metric("Checklists meeting CoW standard",f"{k3_conf}%" if k3_conf is not None else "—")
            a.metric("Locations / teams",len(set(x["site"] for x in lead if x["site"])) if lead else "—")
            b.metric("Quarter",f"Q{q} · {'Complete' if quarter_complete else 'In progress'}" if lead else "—")
            st.caption("Checklist compliance uses the form’s Overall Control of Work Indicator. The KPI remains In progress until the quarter has actually ended; the current checklist result is shown separately for management attention.")

        with c2:
            st.subheader("KPI 2 – Asset Superintendent")
            a,b=st.columns(2)
            a.metric("Audits completed",len(asc) if asc else "—")
            b.metric("Planned audits",k2_plan)
            a.metric("Plan completion",f"{k2_pct}%" if k2_pct is not None else "—")
            b.metric("Audit conformance",f"{k2_conf}%" if k2_conf is not None else "—")
            st.caption("Target: minimum one permit audit per week. Status requires mapped Asset Superintendent audits.")

            st.subheader("KPI 4 – Site Leadership")
            a,b=st.columns(2)
            a.metric("W2W OOE",f"{role_counts['W2W OOE']} / {wks}" if mapping_ready else "Not mapped")
            b.metric("Medic / HSEA",f"{role_counts['Medic HSEA']} / {wks}" if mapping_ready else "Not mapped")
            a.metric("Field Hub OIM",f"{q_field_oim} / 1 quarter" if mapping_ready else "Not mapped")
            b.metric("Level 4 audit conformance",f"{k4_conf}%" if (mapping_ready and k4_conf is not None) else "—")
            st.caption("KPI 4 uses completed Level 4 audits as the compliance basis. Field Hub OIM is assessed against the quarterly target; the two-consecutive-quarter Red rule is applied where history is available.")

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


page=st.sidebar.radio("Select form",["Permit Quality","Toolbox Talk / Permit / POP","Leadership Engagement","Dashboard","Submitted Audits","Dashboard Export"])

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
