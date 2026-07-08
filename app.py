import streamlit as st
import uuid
from datetime import datetime, date
import plotly.graph_objects as go
from collections import defaultdict
import gspread
from google.oauth2.service_account import Credentials

# ─── CONFIG ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Freelance Tracker",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── THEME ───────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background-color: #0F0F1A; color: #E8E8F0; }
section[data-testid="stSidebar"] { background: #1A1A2E; border-right: 1px solid #2A2A3E; }
section[data-testid="stSidebar"] * { color: #E8E8F0 !important; }
.metric-card {
    background: #1A1A2E; border: 1px solid #2A2A3E; border-radius: 12px;
    padding: 20px 24px; margin-bottom: 12px;
}
.metric-card .label { font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 1px; }
.metric-card .value { font-size: 28px; font-weight: 700; margin-top: 4px; }
.metric-card .sub   { font-size: 12px; color: #888; margin-top: 4px; }
.wallet-card {
    background: #1A1A2E; border: 1px solid #2A2A3E; border-radius: 14px;
    padding: 22px 20px; margin-bottom: 10px; transition: border-color 0.2s;
}
.wallet-card:hover { border-color: #7C6AF7; }
.wallet-card .wlabel { font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 1.2px; }
.wallet-card .wvalue { font-size: 26px; font-weight: 700; margin-top: 6px; }
.wallet-card .wicon  { font-size: 24px; margin-bottom: 6px; }
.tx-row { background:#1A1A2E; border:1px solid #2A2A3E; border-radius:10px; padding:12px 16px; margin-bottom:6px; display:flex; align-items:center; justify-content:space-between; }
.tx-left .tx-desc { font-weight:600; font-size:14px; }
.tx-left .tx-meta { font-size:12px; color:#888; margin-top:2px; }
.tx-amount-out { font-size:15px; font-weight:700; color:#E05C5C; }
.tx-amount-in  { font-size:15px; font-weight:700; color:#3DAA6D; }
.tx-amount-transfer { font-size:15px; font-weight:700; color:#7C6AF7; }
.badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .5px; }
.badge-active   { background:#1a4a2e; color:#3DAA6D; }
.badge-inactive { background:#3a1a1a; color:#E05C5C; }
.badge-prospect { background:#3a3a1a; color:#F5C842; }
.badge-paid     { background:#1a4a2e; color:#3DAA6D; }
.badge-unpaid   { background:#3a1a1a; color:#E05C5C; }
.badge-progress { background:#1a2a4a; color:#7C6AF7; }
.badge-pending  { background:#3a3a1a; color:#F5C842; }
.badge-done     { background:#1a3a3a; color:#5BC4BF; }
.row-card { background:#1A1A2E; border:1px solid #2A2A3E; border-radius:10px; padding:14px 18px; margin-bottom:8px; }
.section-title { font-size: 22px; font-weight: 700; color: #E8E8F0; border-left: 4px solid #7C6AF7; padding-left: 12px; margin-bottom: 20px; margin-top: 8px; }
div[data-testid="stForm"] { background: #1A1A2E; border: 1px solid #2A2A3E; border-radius: 12px; padding: 20px; }
.stButton > button { border-radius: 8px !important; font-weight: 600 !important; }
.alert-unpaid { background: #3a1a1a; border: 1px solid #E05C5C; border-radius: 10px; padding: 14px 18px; margin-bottom: 10px; }
.alert-unpaid .name { font-weight: 700; color: #E05C5C; }
.alert-unpaid .detail { font-size: 13px; color: #ccc; margin-top: 4px; }
hr { border-color: #2A2A3E !important; }
</style>
""", unsafe_allow_html=True)

# ─── GOOGLE SHEETS CONNECTION ────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

@st.cache_resource
def get_workbook():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    client = gspread.authorize(creds)
    sheet_id = st.secrets.get("SHEET_ID") or st.secrets["gcp_service_account"].get("SHEET_ID")
    return client.open_by_key(sheet_id)

def get_sheet(tab_name):
    return get_workbook().worksheet(tab_name)

def ensure_wallet_tabs():
    """Create wallet-related tabs in Google Sheets if they don't exist."""
    wb = get_workbook()
    existing = [ws.title for ws in wb.worksheets()]
    
    if "wallet_balances" not in existing:
        ws = wb.add_worksheet(title="wallet_balances", rows=10, cols=5)
        ws.update(values=[["account","balance","updated"]], range_name="A1:C1")
        default_accounts = [
            ["baridi", "0", str(date.today())],
            ["personal_bank", "0", str(date.today())],
            ["business_bank", "0", str(date.today())],
            ["cash", "0", str(date.today())],
        ]
        ws.update(values=default_accounts, range_name="A2:C5")
    
    if "wallet_transactions" not in existing:
        ws = wb.add_worksheet(title="wallet_transactions", rows=200, cols=8)
        ws.update(values=[["id","type","account","to_account","amount","description","date","created"]], range_name="A1:H1")

# ─── DATA HELPERS ────────────────────────────────────────────
HEADERS = {
    "clients":  ["id","name","industry","contact","email","phone","country","status","notes","created"],
    "projects": ["id","name","type","client_id","date","amount","payment_status","work_status","notes","created"],
    "wallet_transactions": ["id","type","account","to_account","amount","description","date","created"],
}

def load(tab):
    try:
        return get_sheet(tab).get_all_records()
    except Exception as e:
        st.error(f"Error loading {tab}: {e}")
        return []

def append_row(tab, record):
    ws = get_sheet(tab)
    headers = HEADERS[tab]
    ws.append_row([str(record.get(h, "")) for h in headers], value_input_option="USER_ENTERED")

def update_row(tab, record_id, updated_record):
    ws = get_sheet(tab)
    headers = HEADERS[tab]
    all_ids = ws.col_values(1)
    try:
        row_num = all_ids.index(record_id) + 1
    except ValueError:
        st.error("Record not found.")
        return
    ws.update(values=[[str(updated_record.get(h, "")) for h in headers]],
              range_name=f"A{row_num}:{chr(64+len(headers))}{row_num}")

def delete_row(tab, record_id):
    ws = get_sheet(tab)
    all_ids = ws.col_values(1)
    try:
        row_num = all_ids.index(record_id) + 1
    except ValueError:
        st.error("Record not found.")
        return
    ws.delete_rows(row_num)

# ─── WALLET HELPERS ─────────────────────────────────────────
ACCOUNT_LABELS = {
    "baridi": ("💳", "Baridi Account", "#5BC4BF"),
    "personal_bank": ("🏦", "Personal Bank", "#7C6AF7"),
    "business_bank": ("🏢", "Business Bank", "#3DAA6D"),
    "cash": ("💵", "Cash", "#F5C842"),
}

def load_balances():
    try:
        ws = get_sheet("wallet_balances")
        rows = ws.get_all_records()  # skips header automatically
        result = {"baridi": 0, "personal_bank": 0, "business_bank": 0, "cash": 0}
        for r in rows:
            acc = str(r.get("account", "")).strip()
            if acc in result:
                try:
                    result[acc] = float(str(r.get("balance", 0)).strip() or 0)
                except:
                    result[acc] = 0
        return result
    except:
        return {"baridi": 0, "personal_bank": 0, "business_bank": 0, "cash": 0}

def save_balance(account, new_balance):
    try:
        ws = get_sheet("wallet_balances")
        # col_values(1) includes the header row at index 0
        # so "baridi" in row 2 of sheet → index 1 in list → row_num = 2 ✓
        all_accounts = ws.col_values(1)  # ["account", "baridi", "personal_bank", ...]
        acc_lower = [a.strip().lower() for a in all_accounts]
        try:
            idx = acc_lower.index(account.lower())  # 0-based index in list
            row_num = idx + 1                        # 1-based Google Sheets row
            ws.update(values=[[account, str(new_balance), str(date.today())]], range_name=f"A{row_num}:C{row_num}")
        except ValueError:
            # Account not found — append it
            ws.append_row([account, str(new_balance), str(date.today())], value_input_option="USER_ENTERED")
    except Exception as e:
        st.error(f"Error saving balance: {e}")

def fmt(amount):
    try:
        return f"{int(float(amount)):,} DZD".replace(",", " ")
    except:
        return "0 DZD"

def badge(text, kind):
    kind_map = {
        "Active":"active","Inactive":"inactive","Prospect":"prospect",
        "Paid":"paid","Unpaid":"unpaid","In Progress":"progress",
        "Pending":"pending","Done":"done"
    }
    cls = "badge-" + kind_map.get(text, "active")
    return f'<span class="badge {cls}">{text}</span>'

def month_key(dt_str):
    try:
        return datetime.strptime(str(dt_str)[:10], "%Y-%m-%d").strftime("%Y-%m")
    except:
        return "Unknown"

# ─── SIDEBAR NAV ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎬 Freelance Tracker")
    st.markdown("---")
    page = st.radio("Navigation",
        ["📊 Dashboard", "👤 Clients", "📁 Projects", "💰 Wallet"],
        label_visibility="collapsed")
    st.markdown("---")
    _clients  = load("clients")
    _projects = load("projects")
    _unpaid   = [p for p in _projects if str(p.get("payment_status","")) == "Unpaid"]
    if _unpaid:
        st.markdown(f"⚠️ **{len(_unpaid)} unpaid invoice{'s' if len(_unpaid)>1 else ''}**")
    
    # Wallet totals in sidebar
    try:
        _balances = st.session_state.get("wallet_balances") or load_balances()
        _total = sum(_balances.values())
        st.markdown(f"<small style='color:#666'>💰 Net worth: </small><br><b style='color:#3DAA6D'>{fmt(_total)}</b>", unsafe_allow_html=True)
        st.markdown("---")
    except:
        pass
    
    st.markdown(f"<small style='color:#666'>👤 {len(_clients)} clients &nbsp;|&nbsp; 📁 {len(_projects)} projects</small>",
                unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# DASHBOARD
# ════════════════════════════════════════════════════════════════
if page == "📊 Dashboard":
    st.markdown('<div class="section-title">Dashboard</div>', unsafe_allow_html=True)

    clients  = load("clients")
    projects = load("projects")
    unpaid   = [p for p in projects if str(p.get("payment_status","")) == "Unpaid"]

    total_income = sum(float(p.get("amount",0) or 0) for p in projects if str(p.get("payment_status",""))=="Paid")
    total_unpaid = sum(float(p.get("amount",0) or 0) for p in unpaid)
    balances     = st.session_state.get("wallet_balances") or load_balances()
    total_wealth = sum(balances.values())

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class="metric-card">
            <div class="label">Total Income (Paid)</div>
            <div class="value" style="color:#3DAA6D">{fmt(total_income)}</div>
            <div class="sub">{len(projects)-len(unpaid)} paid projects</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="metric-card">
            <div class="label">Unpaid Invoices</div>
            <div class="value" style="color:#E05C5C">{fmt(total_unpaid)}</div>
            <div class="sub">{len(unpaid)} project{'s' if len(unpaid)!=1 else ''} pending</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="metric-card">
            <div class="label">Cash in Hand</div>
            <div class="value" style="color:#F5C842">{fmt(balances.get('cash', 0))}</div>
            <div class="sub">Wallet · Cash</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="metric-card">
            <div class="label">Total Net Worth</div>
            <div class="value" style="color:#7C6AF7">{fmt(total_wealth)}</div>
            <div class="sub">All accounts combined</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # Wallet snapshot on dashboard
    st.markdown("### 💰 Wallet Snapshot")
    wc1, wc2, wc3, wc4 = st.columns(4)
    wallet_cols = [wc1, wc2, wc3, wc4]
    for i, (acc_key, (icon, label, color)) in enumerate(ACCOUNT_LABELS.items()):
        bal = balances.get(acc_key, 0)
        wallet_cols[i].markdown(f"""<div class="wallet-card">
            <div class="wicon">{icon}</div>
            <div class="wlabel">{label}</div>
            <div class="wvalue" style="color:{color}">{fmt(bal)}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    if unpaid:
        st.markdown("### ⚠️ Unpaid Invoices")
        client_map = {str(c["id"]): c["name"] for c in clients}
        for p in unpaid:
            cn = client_map.get(str(p.get("client_id","")), "Unknown Client")
            st.markdown(f"""<div class="alert-unpaid">
                <div class="name">📁 {p['name']}</div>
                <div class="detail">Client: {cn} &nbsp;·&nbsp; Amount: <b>{fmt(p.get('amount',0))}</b> &nbsp;·&nbsp; Date: {str(p.get('date',''))[:10]}</div>
            </div>""", unsafe_allow_html=True)
        st.markdown("---")

    monthly_income = defaultdict(float)
    for p in projects:
        if str(p.get("payment_status","")) == "Paid":
            monthly_income[month_key(p.get("date",""))] += float(p.get("amount",0) or 0)
    all_months = sorted(m for m in monthly_income if m != "Unknown")

    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("### 📈 Monthly Income")
        if all_months:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=all_months, y=[monthly_income[m] for m in all_months],
                name="Income", marker_color="#3DAA6D",
                text=[fmt(monthly_income[m]) for m in all_months],
                textposition="outside", textfont=dict(size=10, color="#E8E8F0")))
            fig.update_layout(plot_bgcolor="#0F0F1A", paper_bgcolor="#0F0F1A",
                font_color="#E8E8F0", showlegend=False,
                xaxis=dict(gridcolor="#2A2A3E"), yaxis=dict(gridcolor="#2A2A3E"),
                margin=dict(l=0,r=0,t=30,b=0), height=300)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No paid projects yet.")

    with col_r:
        st.markdown("### 🏦 Account Distribution")
        if total_wealth > 0:
            labels = [ACCOUNT_LABELS[k][1] for k in balances]
            values = list(balances.values())
            colors = [ACCOUNT_LABELS[k][2] for k in balances]
            fig2 = go.Figure(go.Pie(
                labels=labels, values=values,
                marker=dict(colors=colors),
                hole=0.55,
                textinfo="label+percent",
                textfont=dict(size=12),
            ))
            fig2.update_layout(
                plot_bgcolor="#0F0F1A", paper_bgcolor="#0F0F1A",
                font_color="#E8E8F0",
                showlegend=False,
                margin=dict(l=0,r=0,t=10,b=0), height=300,
                annotations=[dict(text=fmt(total_wealth), x=0.5, y=0.5,
                    font_size=13, showarrow=False, font_color="#E8E8F0")]
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Set your account balances in the Wallet page.")

# ════════════════════════════════════════════════════════════════
# CLIENTS
# ════════════════════════════════════════════════════════════════
elif page == "👤 Clients":
    st.markdown('<div class="section-title">Clients</div>', unsafe_allow_html=True)
    clients = load("clients")

    with st.expander("➕ Add New Client", expanded=len(clients)==0):
        with st.form("add_client", clear_on_submit=True):
            c1, c2 = st.columns(2)
            name     = c1.text_input("Client / Company Name *")
            industry = c2.text_input("Industry")
            c3, c4 = st.columns(2)
            contact  = c3.text_input("Contact Person")
            email    = c4.text_input("Email")
            c5, c6 = st.columns(2)
            phone    = c5.text_input("Phone")
            country  = c6.text_input("Country", value="Algeria")
            c7, c8 = st.columns(2)
            status = c7.selectbox("Status", ["Active","Prospect","Inactive"])
            notes  = c8.text_input("Notes")
            if st.form_submit_button("Add Client", use_container_width=True, type="primary"):
                if not name.strip():
                    st.error("Client name is required.")
                else:
                    append_row("clients", {
                        "id":str(uuid.uuid4()),"name":name.strip(),"industry":industry,
                        "contact":contact,"email":email,"phone":phone,"country":country,
                        "status":status,"notes":notes,"created":str(date.today())
                    })
                    st.success(f"✅ '{name}' added!")
                    st.rerun()

    st.markdown(f"**{len(clients)} client{'s' if len(clients)!=1 else ''}**")

    for cl in clients:
        st.markdown(f"""<div class="row-card">
            <b style="font-size:16px">{cl['name']}</b>
            &nbsp;&nbsp;{badge(cl.get('status','Active'), cl.get('status','Active'))}
            &nbsp;<span style="color:#888;font-size:13px">{cl.get('industry','')}</span>
        </div>""", unsafe_allow_html=True)
        with st.expander(f"✏️ Edit — {cl['name']}"):
            with st.form(f"edit_client_{cl['id']}"):
                ec1, ec2 = st.columns(2)
                new_name     = ec1.text_input("Name", value=str(cl.get("name","")))
                new_industry = ec2.text_input("Industry", value=str(cl.get("industry","")))
                ec3, ec4 = st.columns(2)
                new_contact  = ec3.text_input("Contact", value=str(cl.get("contact","")))
                new_email    = ec4.text_input("Email", value=str(cl.get("email","")))
                ec5, ec6 = st.columns(2)
                new_phone   = ec5.text_input("Phone", value=str(cl.get("phone","")))
                new_country = ec6.text_input("Country", value=str(cl.get("country","Algeria")))
                ec7, ec8 = st.columns(2)
                statuses    = ["Active","Prospect","Inactive"]
                cur_status  = str(cl.get("status","Active"))
                new_status  = ec7.selectbox("Status", statuses, index=statuses.index(cur_status) if cur_status in statuses else 0)
                new_notes   = ec8.text_input("Notes", value=str(cl.get("notes","")))
                b1, b2 = st.columns(2)
                if b1.form_submit_button("💾 Save", use_container_width=True, type="primary"):
                    update_row("clients", str(cl["id"]), {
                        **cl,"name":new_name,"industry":new_industry,"contact":new_contact,
                        "email":new_email,"phone":new_phone,"country":new_country,
                        "status":new_status,"notes":new_notes
                    })
                    st.success("✅ Saved!")
                    st.rerun()
                if b2.form_submit_button("🗑️ Delete", use_container_width=True):
                    delete_row("clients", str(cl["id"]))
                    st.success("Deleted.")
                    st.rerun()

# ════════════════════════════════════════════════════════════════
# PROJECTS
# ════════════════════════════════════════════════════════════════
elif page == "📁 Projects":
    st.markdown('<div class="section-title">Projects</div>', unsafe_allow_html=True)
    clients  = load("clients")
    projects = load("projects")

    client_map   = {str(c["id"]): c["name"] for c in clients}
    client_names = list(client_map.values())
    client_ids   = list(client_map.keys())

    with st.expander("➕ Add New Project", expanded=len(projects)==0):
        with st.form("add_project", clear_on_submit=True):
            pc1, pc2 = st.columns(2)
            proj_name = pc1.text_input("Project Name *")
            proj_type = pc2.selectbox("Type", ["Video","Photography","Photo+Video","Reels","Event Coverage","Other"])
            pc3, pc4 = st.columns(2)
            if client_names:
                client_sel    = pc3.selectbox("Client", client_names)
                sel_client_id = client_ids[client_names.index(client_sel)]
            else:
                pc3.warning("Add a client first.")
                sel_client_id = None
            proj_date = pc4.date_input("Date", value=date.today())
            pc5, pc6 = st.columns(2)
            amount   = pc5.number_input("Amount (DZD)", min_value=0, step=1000)
            pay_stat = pc6.selectbox("Payment Status", ["Unpaid","Paid"])
            pc7, pc8 = st.columns(2)
            work_stat = pc7.selectbox("Work Status", ["In Progress","Pending","Done"])
            notes     = pc8.text_input("Notes")
            if st.form_submit_button("Add Project", use_container_width=True, type="primary"):
                if not proj_name.strip():
                    st.error("Project name is required.")
                elif not sel_client_id:
                    st.error("Please add a client first.")
                else:
                    append_row("projects", {
                        "id":str(uuid.uuid4()),"name":proj_name.strip(),"type":proj_type,
                        "client_id":sel_client_id,"date":str(proj_date),"amount":amount,
                        "payment_status":pay_stat,"work_status":work_stat,
                        "notes":notes,"created":str(date.today())
                    })
                    st.success(f"✅ '{proj_name}' added!")
                    st.rerun()

    f1, f2, f3 = st.columns(3)
    filter_pay  = f1.selectbox("Payment", ["All","Paid","Unpaid"], label_visibility="collapsed")
    filter_work = f2.selectbox("Status",  ["All","In Progress","Pending","Done"], label_visibility="collapsed")
    filter_cli  = f3.selectbox("Client",  ["All"]+client_names, label_visibility="collapsed")

    filtered = [p for p in projects if
        (filter_pay  == "All" or str(p.get("payment_status","")) == filter_pay) and
        (filter_work == "All" or str(p.get("work_status",""))    == filter_work) and
        (filter_cli  == "All" or client_map.get(str(p.get("client_id",""))) == filter_cli)
    ]
    st.markdown(f"**{len(filtered)} project{'s' if len(filtered)!=1 else ''}**")

    TYPES     = ["Video","Photography","Photo+Video","Reels","Event Coverage","Other"]
    PAY_OPTS  = ["Unpaid","Paid"]
    WORK_OPTS = ["In Progress","Pending","Done"]

    for p in filtered:
        cn = client_map.get(str(p.get("client_id","")), "Unknown")
        st.markdown(f"""<div class="row-card">
            <b style="font-size:15px">{p['name']}</b>
            &nbsp;&nbsp;{badge(str(p.get('payment_status','Unpaid')), str(p.get('payment_status','Unpaid')))}
            &nbsp;{badge(str(p.get('work_status','Pending')), str(p.get('work_status','Pending')))}
            <br><span style="color:#888;font-size:13px">{cn} · {p.get('type','')} · {str(p.get('date',''))[:10]}</span>
            &nbsp;&nbsp;<b style="color:#7C6AF7">{fmt(p.get('amount',0))}</b>
        </div>""", unsafe_allow_html=True)
        with st.expander(f"✏️ Edit — {p['name']}"):
            with st.form(f"edit_proj_{p['id']}"):
                ep1, ep2 = st.columns(2)
                new_pname = ep1.text_input("Project Name", value=str(p.get("name","")))
                cur_type  = str(p.get("type","Video"))
                new_ptype = ep2.selectbox("Type", TYPES, index=TYPES.index(cur_type) if cur_type in TYPES else 0)
                ep3, ep4 = st.columns(2)
                new_amount = ep3.number_input("Amount (DZD)", value=int(float(p.get("amount",0) or 0)), min_value=0, step=1000)
                try:
                    new_date = ep4.date_input("Date", value=datetime.strptime(str(p.get("date","2025-01-01"))[:10], "%Y-%m-%d").date())
                except:
                    new_date = ep4.date_input("Date")
                ep5, ep6 = st.columns(2)
                cur_pay  = str(p.get("payment_status","Unpaid"))
                cur_work = str(p.get("work_status","Pending"))
                new_paystat  = ep5.selectbox("Payment Status", PAY_OPTS,  index=PAY_OPTS.index(cur_pay)   if cur_pay  in PAY_OPTS  else 0)
                new_workstat = ep6.selectbox("Work Status",    WORK_OPTS, index=WORK_OPTS.index(cur_work) if cur_work in WORK_OPTS else 0)
                new_notes = st.text_input("Notes", value=str(p.get("notes","")))
                b1, b2 = st.columns(2)
                if b1.form_submit_button("💾 Save", use_container_width=True, type="primary"):
                    update_row("projects", str(p["id"]), {
                        **p,"name":new_pname,"type":new_ptype,"amount":new_amount,
                        "date":str(new_date),"payment_status":new_paystat,
                        "work_status":new_workstat,"notes":new_notes
                    })
                    st.success("✅ Saved!")
                    st.rerun()
                if b2.form_submit_button("🗑️ Delete", use_container_width=True):
                    delete_row("projects", str(p["id"]))
                    st.success("Deleted.")
                    st.rerun()

# ════════════════════════════════════════════════════════════════
# WALLET
# ════════════════════════════════════════════════════════════════
elif page == "💰 Wallet":
    st.markdown('<div class="section-title">Wallet</div>', unsafe_allow_html=True)

    # Ensure sheets exist
    try:
        ensure_wallet_tabs()
    except Exception as e:
        st.warning(f"Setting up wallet sheets... ({e})")

    # Load from Google Sheets, but override with session_state if we just wrote
    _balances_from_sheet = load_balances()
    if "wallet_balances" not in st.session_state:
        st.session_state["wallet_balances"] = _balances_from_sheet
    else:
        # Merge: sheet is source of truth but session overwrites after a write
        for k in _balances_from_sheet:
            if k not in st.session_state["wallet_balances"]:
                st.session_state["wallet_balances"][k] = _balances_from_sheet[k]
    balances = st.session_state["wallet_balances"]
    total_wealth = sum(balances.values())

    # ── TOP: 4 Account Cards ──────────────────────────────────
    st.markdown("### 🏦 Account Balances")
    cols = st.columns(4)
    for i, (acc_key, (icon, label, color)) in enumerate(ACCOUNT_LABELS.items()):
        bal = balances.get(acc_key, 0)
        cols[i].markdown(f"""<div class="wallet-card">
            <div class="wicon">{icon}</div>
            <div class="wlabel">{label}</div>
            <div class="wvalue" style="color:{color}">{fmt(bal)}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown(f"""<div class="metric-card" style="margin-top:4px">
        <div class="label">Total Net Worth</div>
        <div class="value" style="color:#E8E8F0">{fmt(total_wealth)}</div>
        <div class="sub">All accounts combined</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── TWO COLUMN ACTIONS ───────────────────────────────────
    col_left, col_right = st.columns(2)

    with col_left:
        # ── UPDATE BALANCE ──
        st.markdown("#### ✏️ Update Account Balance")
        with st.form("update_balance", clear_on_submit=False):
            acc_options = {v[1]: k for k, v in ACCOUNT_LABELS.items()}
            sel_acc_label = st.selectbox("Account", list(acc_options.keys()))
            sel_acc_key   = acc_options[sel_acc_label]
            current_bal   = balances.get(sel_acc_key, 0)
            new_bal = st.number_input(
                f"New balance (currently {fmt(current_bal)})",
                min_value=0, step=500,
                value=int(current_bal)
            )
            if st.form_submit_button("💾 Set Balance", use_container_width=True, type="primary"):
                diff = new_bal - current_bal
                save_balance(sel_acc_key, new_bal)
                st.session_state["wallet_balances"][sel_acc_key] = float(new_bal)
                try:
                    append_row("wallet_transactions", {
                        "id": str(uuid.uuid4()),
                        "type": "adjustment",
                        "account": sel_acc_key,
                        "to_account": "",
                        "amount": str(abs(diff)),
                        "description": f"Balance adjustment ({'+' if diff>=0 else '-'}{fmt(abs(diff))})",
                        "date": str(date.today()),
                        "created": str(datetime.now()),
                    })
                except:
                    pass
                st.success(f"✅ {sel_acc_label} updated to {fmt(new_bal)}")
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        # ── LOG SPENDING ──
        st.markdown("#### 💸 Log Spending")
        with st.form("log_spend", clear_on_submit=True):
            spend_acc_label = st.selectbox("Paid from", list(acc_options.keys()), key="spend_acc")
            spend_acc_key   = acc_options[spend_acc_label]
            spend_amount    = st.number_input("Amount (DZD)", min_value=1, step=500, key="spend_amount")
            spend_desc      = st.text_input("What for?", placeholder="e.g. Transport, Food, Equipment…")
            spend_date      = st.date_input("Date", value=date.today(), key="spend_date")
            if st.form_submit_button("➖ Record Spending", use_container_width=True):
                if not spend_desc.strip():
                    st.error("Please describe the spending.")
                else:
                    current = balances.get(spend_acc_key, 0)
                    if spend_amount > current:
                        st.warning(f"⚠️ Not enough in {spend_acc_label} ({fmt(current)}). Recorded anyway.")
                    new_balance = max(0, current - spend_amount)
                    save_balance(spend_acc_key, new_balance)
                    st.session_state["wallet_balances"][spend_acc_key] = float(new_balance)
                    append_row("wallet_transactions", {
                        "id": str(uuid.uuid4()),
                        "type": "spend",
                        "account": spend_acc_key,
                        "to_account": "",
                        "amount": str(spend_amount),
                        "description": spend_desc.strip(),
                        "date": str(spend_date),
                        "created": str(datetime.now()),
                    })
                    st.success(f"✅ -{fmt(spend_amount)} from {spend_acc_label} → {fmt(new_balance)} remaining")
                    st.rerun()

    with col_right:
        # ── LOG INCOME ──
        st.markdown("#### 💰 Log Income / Deposit")
        with st.form("log_income", clear_on_submit=True):
            inc_acc_label = st.selectbox("Into account", list(acc_options.keys()), key="inc_acc")
            inc_acc_key   = acc_options[inc_acc_label]
            inc_amount    = st.number_input("Amount (DZD)", min_value=1, step=500, key="inc_amount")
            inc_desc      = st.text_input("Source / Description", placeholder="e.g. Client payment, Salary…")
            inc_date      = st.date_input("Date", value=date.today(), key="inc_date")
            if st.form_submit_button("➕ Record Income", use_container_width=True, type="primary"):
                if not inc_desc.strip():
                    st.error("Please add a description.")
                else:
                    current = balances.get(inc_acc_key, 0)
                    new_balance = current + inc_amount
                    save_balance(inc_acc_key, new_balance)
                    st.session_state["wallet_balances"][inc_acc_key] = float(new_balance)
                    append_row("wallet_transactions", {
                        "id": str(uuid.uuid4()),
                        "type": "income",
                        "account": inc_acc_key,
                        "to_account": "",
                        "amount": str(inc_amount),
                        "description": inc_desc.strip(),
                        "date": str(inc_date),
                        "created": str(datetime.now()),
                    })
                    st.success(f"✅ +{fmt(inc_amount)} into {inc_acc_label} → {fmt(new_balance)} total")
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        # ── TRANSFER ──
        st.markdown("#### 🔄 Transfer Between Accounts")
        with st.form("transfer", clear_on_submit=True):
            acc_keys   = list(ACCOUNT_LABELS.keys())
            acc_labels = [ACCOUNT_LABELS[k][1] for k in acc_keys]
            from_label = st.selectbox("From", acc_labels, key="tr_from")
            to_label   = st.selectbox("To",   acc_labels, index=1, key="tr_to")
            tr_amount  = st.number_input("Amount (DZD)", min_value=1, step=500, key="tr_amount")
            tr_desc    = st.text_input("Note (optional)", placeholder="e.g. Withdrew cash from Baridi")
            tr_date    = st.date_input("Date", value=date.today(), key="tr_date")
            if st.form_submit_button("🔄 Transfer", use_container_width=True):
                from_key = acc_keys[acc_labels.index(from_label)]
                to_key   = acc_keys[acc_labels.index(to_label)]
                if from_key == to_key:
                    st.error("Source and destination must be different.")
                else:
                    from_bal = balances.get(from_key, 0)
                    to_bal   = balances.get(to_key, 0)
                    if tr_amount > from_bal:
                        st.warning(f"⚠️ Not enough in {from_label}. Recorded anyway.")
                    new_from = max(0, from_bal - tr_amount)
                    new_to   = to_bal + tr_amount
                    save_balance(from_key, new_from)
                    save_balance(to_key, new_to)
                    st.session_state["wallet_balances"][from_key] = float(new_from)
                    st.session_state["wallet_balances"][to_key]   = float(new_to)
                    desc = tr_desc.strip() or f"Transfer {from_label} → {to_label}"
                    append_row("wallet_transactions", {
                        "id": str(uuid.uuid4()),
                        "type": "transfer",
                        "account": from_key,
                        "to_account": to_key,
                        "amount": str(tr_amount),
                        "description": desc,
                        "date": str(tr_date),
                        "created": str(datetime.now()),
                    })
                    st.success(f"✅ Transferred {fmt(tr_amount)}: {from_label} → {to_label}")
                    st.rerun()

    st.markdown("---")

    # ── TRANSACTION HISTORY ──────────────────────────────────
    st.markdown("### 📋 Transaction History")
    try:
        transactions = load("wallet_transactions")
        transactions = sorted(transactions, key=lambda x: str(x.get("date","") or ""), reverse=True)

        if not transactions:
            st.info("No transactions yet. Use the forms above to log spending, income, or transfers.")
        else:
            # Filter bar
            hf1, hf2, hf3 = st.columns(3)
            tx_type_filter = hf1.selectbox("Type", ["All","spend","income","transfer","adjustment"], label_visibility="collapsed")
            acc_filter_label = hf2.selectbox("Account", ["All"] + [v[1] for v in ACCOUNT_LABELS.values()], label_visibility="collapsed")
            limit = hf3.selectbox("Show", ["Last 20","Last 50","All"], label_visibility="collapsed")

            # Apply filters
            filtered_tx = transactions
            if tx_type_filter != "All":
                filtered_tx = [t for t in filtered_tx if t.get("type") == tx_type_filter]
            if acc_filter_label != "All":
                acc_filter_key = next(k for k, v in ACCOUNT_LABELS.items() if v[1] == acc_filter_label)
                filtered_tx = [t for t in filtered_tx if t.get("account") == acc_filter_key or t.get("to_account") == acc_filter_key]
            if limit == "Last 20":
                filtered_tx = filtered_tx[:20]
            elif limit == "Last 50":
                filtered_tx = filtered_tx[:50]

            TYPE_ICONS = {"spend":"💸","income":"💰","transfer":"🔄","adjustment":"✏️"}
            TYPE_COLORS = {"spend":"tx-amount-out","income":"tx-amount-in","transfer":"tx-amount-transfer","adjustment":"tx-amount-transfer"}

            for tx in filtered_tx:
                tx_type = str(tx.get("type",""))
                icon    = TYPE_ICONS.get(tx_type, "•")
                acc_key = str(tx.get("account",""))
                acc_label = ACCOUNT_LABELS.get(acc_key, ("","Unknown","#888"))[1]
                to_acc_key = str(tx.get("to_account",""))
                to_label = ACCOUNT_LABELS.get(to_acc_key, ("","","#888"))[1] if to_acc_key else ""
                amount  = float(tx.get("amount", 0) or 0)
                sign    = "-" if tx_type == "spend" else ("+" if tx_type == "income" else "")
                amt_cls = TYPE_COLORS.get(tx_type, "tx-amount-transfer")
                meta    = acc_label + (f" → {to_label}" if to_label else "") + f" · {str(tx.get('date',''))[:10]}"

                col_tx, col_del = st.columns([12, 1])
                with col_tx:
                    st.markdown(f"""<div class="tx-row">
                        <div class="tx-left">
                            <div class="tx-desc">{icon} {tx.get('description','')}</div>
                            <div class="tx-meta">{meta}</div>
                        </div>
                        <div class="{amt_cls}">{sign}{fmt(amount)}</div>
                    </div>""", unsafe_allow_html=True)
                with col_del:
                    if st.button("🗑️", key=f"del_tx_{tx.get('id','')}"):
                        delete_row("wallet_transactions", str(tx["id"]))
                        st.rerun()

    except Exception as e:
        st.error(f"Could not load transactions: {e}")
