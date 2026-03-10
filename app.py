import streamlit as st
import json
import os
import uuid
from datetime import datetime, date
import plotly.graph_objects as go
import plotly.express as px
from collections import defaultdict

# ─── CONFIG ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Freelance Tracker",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

FILES = {
    "clients":  os.path.join(DATA_DIR, "clients.json"),
    "projects": os.path.join(DATA_DIR, "projects.json"),
    "expenses": os.path.join(DATA_DIR, "expenses.json"),
}

# ─── THEME ───────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.stApp { background-color: #0F0F1A; color: #E8E8F0; }

section[data-testid="stSidebar"] {
    background: #1A1A2E;
    border-right: 1px solid #2A2A3E;
}
section[data-testid="stSidebar"] * { color: #E8E8F0 !important; }

.metric-card {
    background: #1A1A2E;
    border: 1px solid #2A2A3E;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 12px;
}
.metric-card .label { font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 1px; }
.metric-card .value { font-size: 28px; font-weight: 700; margin-top: 4px; }
.metric-card .sub   { font-size: 12px; color: #888; margin-top: 4px; }

.badge {
    display: inline-block; padding: 3px 10px; border-radius: 20px;
    font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .5px;
}
.badge-active   { background:#1a4a2e; color:#3DAA6D; }
.badge-inactive { background:#3a1a1a; color:#E05C5C; }
.badge-prospect { background:#3a3a1a; color:#F5C842; }
.badge-paid     { background:#1a4a2e; color:#3DAA6D; }
.badge-unpaid   { background:#3a1a1a; color:#E05C5C; }
.badge-progress { background:#1a2a4a; color:#7C6AF7; }
.badge-pending  { background:#3a3a1a; color:#F5C842; }
.badge-done     { background:#1a3a3a; color:#5BC4BF; }

.row-card {
    background:#1A1A2E; border:1px solid #2A2A3E; border-radius:10px;
    padding:14px 18px; margin-bottom:8px;
}
.row-card:hover { border-color:#7C6AF7; }

.section-title {
    font-size: 22px; font-weight: 700; color: #E8E8F0;
    border-left: 4px solid #7C6AF7; padding-left: 12px;
    margin-bottom: 20px; margin-top: 8px;
}

div[data-testid="stForm"] {
    background: #1A1A2E;
    border: 1px solid #2A2A3E;
    border-radius: 12px;
    padding: 20px;
}

.stButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: all 0.2s !important;
}
.stButton > button:hover { transform: translateY(-1px); }

div[data-testid="stSelectbox"] label,
div[data-testid="stTextInput"] label,
div[data-testid="stNumberInput"] label,
div[data-testid="stDateInput"] label,
div[data-testid="stTextArea"] label {
    color: #AAAACC !important; font-size: 13px !important;
}

.alert-unpaid {
    background: #3a1a1a; border: 1px solid #E05C5C; border-radius: 10px;
    padding: 14px 18px; margin-bottom: 10px;
}
.alert-unpaid .name { font-weight: 700; color: #E05C5C; }
.alert-unpaid .detail { font-size: 13px; color: #ccc; margin-top: 4px; }

hr { border-color: #2A2A3E !important; }
</style>
""", unsafe_allow_html=True)

# ─── DATA HELPERS ────────────────────────────────────────────
def load(key):
    path = FILES[key]
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)

def save(key, data):
    with open(FILES[key], "w") as f:
        json.dump(data, f, indent=2, default=str)

def fmt(amount):
    return f"{int(amount):,} DZD".replace(",", " ")

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
    page = st.radio(
        "Navigation",
        ["📊 Dashboard", "👤 Clients", "📁 Projects", "💸 Expenses"],
        label_visibility="collapsed"
    )
    st.markdown("---")
    clients  = load("clients")
    projects = load("projects")
    expenses = load("expenses")
    unpaid   = [p for p in projects if p.get("payment_status") == "Unpaid"]
    if unpaid:
        st.markdown(f"⚠️ **{len(unpaid)} unpaid invoice{'s' if len(unpaid)>1 else ''}**")
    st.markdown(f"<small style='color:#666'>👤 {len(clients)} clients &nbsp;|&nbsp; 📁 {len(projects)} projects</small>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ════════════════════════════════════════════════════════════════
if page == "📊 Dashboard":
    st.markdown('<div class="section-title">Dashboard</div>', unsafe_allow_html=True)

    clients  = load("clients")
    projects = load("projects")
    expenses = load("expenses")

    total_income   = sum(p.get("amount", 0) for p in projects if p.get("payment_status") == "Paid")
    total_unpaid   = sum(p.get("amount", 0) for p in projects if p.get("payment_status") == "Unpaid")
    total_expenses = sum(e.get("amount", 0) for e in expenses)
    profit         = total_income - total_expenses

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class="metric-card">
            <div class="label">Total Income (Paid)</div>
            <div class="value" style="color:#3DAA6D">{fmt(total_income)}</div>
            <div class="sub">{len([p for p in projects if p.get('payment_status')=='Paid'])} paid projects</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="metric-card">
            <div class="label">Unpaid Invoices</div>
            <div class="value" style="color:#E05C5C">{fmt(total_unpaid)}</div>
            <div class="sub">{len(unpaid)} project{'s' if len(unpaid)!=1 else ''} pending</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="metric-card">
            <div class="label">Total Expenses</div>
            <div class="value" style="color:#F5C842">{fmt(total_expenses)}</div>
            <div class="sub">All time</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        color = "#3DAA6D" if profit >= 0 else "#E05C5C"
        margin = f"{(profit/total_income*100):.1f}%" if total_income else "—"
        st.markdown(f"""<div class="metric-card">
            <div class="label">Net Profit</div>
            <div class="value" style="color:{color}">{fmt(profit)}</div>
            <div class="sub">Margin: {margin}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Unpaid Alerts ──────────────────────────────────────────
    if unpaid:
        st.markdown("### ⚠️ Unpaid Invoices")
        for p in unpaid:
            client_name = next((c["name"] for c in clients if c["id"] == p.get("client_id")), "Unknown Client")
            st.markdown(f"""<div class="alert-unpaid">
                <div class="name">📁 {p['name']}</div>
                <div class="detail">Client: {client_name} &nbsp;·&nbsp; Amount: <b>{fmt(p.get('amount',0))}</b> &nbsp;·&nbsp; Date: {str(p.get('date',''))[:10]}</div>
            </div>""", unsafe_allow_html=True)
        st.markdown("---")

    # ── Charts ────────────────────────────────────────────────
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown("### 📈 Monthly Income vs Expenses")
        monthly_income   = defaultdict(float)
        monthly_expenses = defaultdict(float)
        for p in projects:
            if p.get("payment_status") == "Paid":
                monthly_income[month_key(p.get("date", ""))] += p.get("amount", 0)
        for e in expenses:
            monthly_expenses[month_key(e.get("date", ""))] += e.get("amount", 0)
        all_months = sorted(set(list(monthly_income.keys()) + list(monthly_expenses.keys())))
        if all_months:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=all_months, y=[monthly_income[m] for m in all_months],
                name="Income", marker_color="#3DAA6D", opacity=0.9
            ))
            fig.add_trace(go.Bar(
                x=all_months, y=[monthly_expenses[m] for m in all_months],
                name="Expenses", marker_color="#E05C5C", opacity=0.9
            ))
            fig.update_layout(
                barmode="group", plot_bgcolor="#0F0F1A", paper_bgcolor="#0F0F1A",
                font_color="#E8E8F0", legend=dict(bgcolor="#1A1A2E"),
                xaxis=dict(gridcolor="#2A2A3E"), yaxis=dict(gridcolor="#2A2A3E"),
                margin=dict(l=0, r=0, t=10, b=0), height=300
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Add projects and expenses to see this chart.")

    with col_r:
        st.markdown("### 📉 Profit Margin Over Time")
        if all_months:
            profits = [monthly_income[m] - monthly_expenses[m] for m in all_months]
            margins = [
                (profits[i] / monthly_income[m] * 100) if monthly_income[m] else 0
                for i, m in enumerate(all_months)
            ]
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=all_months, y=margins, mode="lines+markers",
                line=dict(color="#7C6AF7", width=2.5),
                marker=dict(size=7, color="#7C6AF7"),
                fill="tozeroy", fillcolor="rgba(124,106,247,0.12)",
                name="Margin %"
            ))
            fig2.add_hline(y=0, line_dash="dash", line_color="#E05C5C", opacity=0.5)
            fig2.update_layout(
                plot_bgcolor="#0F0F1A", paper_bgcolor="#0F0F1A",
                font_color="#E8E8F0",
                xaxis=dict(gridcolor="#2A2A3E"), yaxis=dict(gridcolor="#2A2A3E", ticksuffix="%"),
                margin=dict(l=0, r=0, t=10, b=0), height=300
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Add data to see profit margin trend.")

# ════════════════════════════════════════════════════════════════
# PAGE: CLIENTS
# ════════════════════════════════════════════════════════════════
elif page == "👤 Clients":
    st.markdown('<div class="section-title">Clients</div>', unsafe_allow_html=True)
    clients = load("clients")

    with st.expander("➕ Add New Client", expanded=len(clients) == 0):
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
            status   = c7.selectbox("Status", ["Active", "Prospect", "Inactive"])
            notes    = c8.text_input("Notes")
            submitted = st.form_submit_button("Add Client", use_container_width=True, type="primary")
            if submitted:
                if not name.strip():
                    st.error("Client name is required.")
                else:
                    clients.append({
                        "id": str(uuid.uuid4()), "name": name.strip(),
                        "industry": industry, "contact": contact,
                        "email": email, "phone": phone, "country": country,
                        "status": status, "notes": notes,
                        "created": str(date.today())
                    })
                    save("clients", clients)
                    st.success(f"✅ Client '{name}' added!")
                    st.rerun()

    st.markdown(f"**{len(clients)} client{'s' if len(clients)!=1 else ''}**")
    st.markdown("")

    for i, cl in enumerate(clients):
        with st.container():
            st.markdown(f"""<div class="row-card">
                <b style="font-size:16px">{cl['name']}</b>
                &nbsp;&nbsp;{badge(cl.get('status','Active'), cl.get('status','Active'))}
                &nbsp;<span style="color:#888;font-size:13px">{cl.get('industry','')}</span>
            </div>""", unsafe_allow_html=True)
            with st.expander(f"✏️ Edit / Details — {cl['name']}"):
                with st.form(f"edit_client_{cl['id']}"):
                    ec1, ec2 = st.columns(2)
                    new_name     = ec1.text_input("Name", value=cl["name"])
                    new_industry = ec2.text_input("Industry", value=cl.get("industry",""))
                    ec3, ec4 = st.columns(2)
                    new_contact  = ec3.text_input("Contact", value=cl.get("contact",""))
                    new_email    = ec4.text_input("Email", value=cl.get("email",""))
                    ec5, ec6 = st.columns(2)
                    new_phone    = ec5.text_input("Phone", value=cl.get("phone",""))
                    new_country  = ec6.text_input("Country", value=cl.get("country","Algeria"))
                    ec7, ec8 = st.columns(2)
                    new_status   = ec7.selectbox("Status", ["Active","Prospect","Inactive"], index=["Active","Prospect","Inactive"].index(cl.get("status","Active")))
                    new_notes    = ec8.text_input("Notes", value=cl.get("notes",""))
                    b1, b2 = st.columns(2)
                    save_btn   = b1.form_submit_button("💾 Save Changes", use_container_width=True, type="primary")
                    delete_btn = b2.form_submit_button("🗑️ Delete Client", use_container_width=True)
                    if save_btn:
                        clients[i].update({"name":new_name,"industry":new_industry,"contact":new_contact,
                                           "email":new_email,"phone":new_phone,"country":new_country,
                                           "status":new_status,"notes":new_notes})
                        save("clients", clients)
                        st.success("✅ Saved!")
                        st.rerun()
                    if delete_btn:
                        clients.pop(i)
                        save("clients", clients)
                        st.success("Deleted.")
                        st.rerun()

# ════════════════════════════════════════════════════════════════
# PAGE: PROJECTS
# ════════════════════════════════════════════════════════════════
elif page == "📁 Projects":
    st.markdown('<div class="section-title">Projects</div>', unsafe_allow_html=True)
    clients  = load("clients")
    projects = load("projects")

    client_options = {c["id"]: c["name"] for c in clients}
    client_names   = list(client_options.values())
    client_ids     = list(client_options.keys())

    with st.expander("➕ Add New Project", expanded=len(projects)==0):
        with st.form("add_project", clear_on_submit=True):
            pc1, pc2 = st.columns(2)
            proj_name = pc1.text_input("Project Name *")
            proj_type = pc2.selectbox("Type", ["Video","Photography","Photo+Video","Reels","Event Coverage","Other"])
            pc3, pc4 = st.columns(2)
            if client_names:
                client_sel = pc3.selectbox("Client", client_names)
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
            submitted = st.form_submit_button("Add Project", use_container_width=True, type="primary")
            if submitted:
                if not proj_name.strip():
                    st.error("Project name is required.")
                elif not sel_client_id:
                    st.error("Please add a client first.")
                else:
                    projects.append({
                        "id": str(uuid.uuid4()), "name": proj_name.strip(),
                        "type": proj_type, "client_id": sel_client_id,
                        "date": str(proj_date), "amount": amount,
                        "payment_status": pay_stat, "work_status": work_stat,
                        "notes": notes, "created": str(date.today())
                    })
                    save("projects", projects)
                    st.success(f"✅ Project '{proj_name}' added!")
                    st.rerun()

    # ── Filter bar ────────────────────────────────────────────
    st.markdown("")
    f1, f2, f3 = st.columns(3)
    filter_pay  = f1.selectbox("Payment", ["All","Paid","Unpaid"], label_visibility="collapsed")
    filter_work = f2.selectbox("Status",  ["All","In Progress","Pending","Done"], label_visibility="collapsed")
    filter_cli  = f3.selectbox("Client",  ["All"] + client_names, label_visibility="collapsed")

    filtered = [p for p in projects if
        (filter_pay  == "All" or p.get("payment_status") == filter_pay) and
        (filter_work == "All" or p.get("work_status")    == filter_work) and
        (filter_cli  == "All" or client_options.get(p.get("client_id",""),"") == filter_cli)
    ]
    st.markdown(f"**{len(filtered)} project{'s' if len(filtered)!=1 else ''}**")
    st.markdown("")

    for i_f, p in enumerate(filtered):
        real_idx = next((j for j, x in enumerate(projects) if x["id"] == p["id"]), None)
        client_name = client_options.get(p.get("client_id",""), "Unknown")
        st.markdown(f"""<div class="row-card">
            <b style="font-size:15px">{p['name']}</b>
            &nbsp;&nbsp;{badge(p.get('payment_status','Unpaid'), p.get('payment_status','Unpaid'))}
            &nbsp;{badge(p.get('work_status','Pending'), p.get('work_status','Pending'))}
            <br><span style="color:#888;font-size:13px">{client_name} · {p.get('type','')} · {str(p.get('date',''))[:10]}</span>
            &nbsp;&nbsp;<b style="color:#7C6AF7">{fmt(p.get('amount',0))}</b>
        </div>""", unsafe_allow_html=True)

        with st.expander(f"✏️ Edit — {p['name']}"):
            with st.form(f"edit_proj_{p['id']}"):
                ep1, ep2 = st.columns(2)
                new_pname  = ep1.text_input("Project Name", value=p["name"])
                new_ptype  = ep2.selectbox("Type", ["Video","Photography","Photo+Video","Reels","Event Coverage","Other"],
                                           index=["Video","Photography","Photo+Video","Reels","Event Coverage","Other"].index(p.get("type","Video")) if p.get("type","Video") in ["Video","Photography","Photo+Video","Reels","Event Coverage","Other"] else 0)
                ep3, ep4 = st.columns(2)
                new_amount = ep3.number_input("Amount (DZD)", value=int(p.get("amount",0)), min_value=0, step=1000)
                try:
                    new_date = ep4.date_input("Date", value=datetime.strptime(str(p.get("date","2025-01-01"))[:10], "%Y-%m-%d").date())
                except:
                    new_date = ep4.date_input("Date")
                ep5, ep6 = st.columns(2)
                new_paystat  = ep5.selectbox("Payment Status", ["Unpaid","Paid"],
                                             index=["Unpaid","Paid"].index(p.get("payment_status","Unpaid")))
                new_workstat = ep6.selectbox("Work Status", ["In Progress","Pending","Done"],
                                             index=["In Progress","Pending","Done"].index(p.get("work_status","Pending")))
                new_notes = st.text_input("Notes", value=p.get("notes",""))
                b1, b2 = st.columns(2)
                save_btn   = b1.form_submit_button("💾 Save", use_container_width=True, type="primary")
                delete_btn = b2.form_submit_button("🗑️ Delete", use_container_width=True)
                if save_btn and real_idx is not None:
                    projects[real_idx].update({
                        "name":new_pname,"type":new_ptype,"amount":new_amount,
                        "date":str(new_date),"payment_status":new_paystat,
                        "work_status":new_workstat,"notes":new_notes
                    })
                    save("projects", projects)
                    st.success("✅ Saved!")
                    st.rerun()
                if delete_btn and real_idx is not None:
                    projects.pop(real_idx)
                    save("projects", projects)
                    st.success("Deleted.")
                    st.rerun()

# ════════════════════════════════════════════════════════════════
# PAGE: EXPENSES
# ════════════════════════════════════════════════════════════════
elif page == "💸 Expenses":
    st.markdown('<div class="section-title">Expenses</div>', unsafe_allow_html=True)
    expenses = load("expenses")

    CATEGORIES = [
        "Equipment & Gear", "Software & Subscriptions",
        "Transport & Fuel", "Marketing & Ads",
        "Studio / Location Fees", "Outsourcing",
        "Internet & Phone", "Food & Meetings",
        "Taxes & Admin", "Miscellaneous"
    ]

    with st.expander("➕ Add Expense", expanded=len(expenses)==0):
        with st.form("add_expense", clear_on_submit=True):
            ex1, ex2 = st.columns(2)
            ex_label = ex1.text_input("Description *")
            ex_cat   = ex2.selectbox("Category", CATEGORIES)
            ex3, ex4 = st.columns(2)
            ex_amount = ex3.number_input("Amount (DZD)", min_value=0, step=500)
            ex_date   = ex4.date_input("Date", value=date.today())
            submitted = st.form_submit_button("Add Expense", use_container_width=True, type="primary")
            if submitted:
                if not ex_label.strip():
                    st.error("Description is required.")
                else:
                    expenses.append({
                        "id": str(uuid.uuid4()), "label": ex_label.strip(),
                        "category": ex_cat, "amount": ex_amount,
                        "date": str(ex_date)
                    })
                    save("expenses", expenses)
                    st.success("✅ Expense added!")
                    st.rerun()

    # ── Monthly breakdown chart ───────────────────────────────
    if expenses:
        monthly_by_cat = defaultdict(lambda: defaultdict(float))
        for e in expenses:
            monthly_by_cat[month_key(e["date"])][e["category"]] += e["amount"]
        all_months = sorted(monthly_by_cat.keys())

        st.markdown("### 📊 Spending by Category Over Time")
        colors = ["#7C6AF7","#5BC4BF","#E05C5C","#F5C842","#3DAA6D",
                  "#FF8C69","#87CEEB","#DDA0DD","#98FB98","#F0E68C"]
        fig3 = go.Figure()
        cats_used = sorted(set(e["category"] for e in expenses))
        for ci, cat in enumerate(cats_used):
            fig3.add_trace(go.Bar(
                x=all_months, y=[monthly_by_cat[m][cat] for m in all_months],
                name=cat, marker_color=colors[ci % len(colors)]
            ))
        fig3.update_layout(
            barmode="stack", plot_bgcolor="#0F0F1A", paper_bgcolor="#0F0F1A",
            font_color="#E8E8F0", legend=dict(bgcolor="#1A1A2E", font_size=11),
            xaxis=dict(gridcolor="#2A2A3E"), yaxis=dict(gridcolor="#2A2A3E"),
            margin=dict(l=0, r=0, t=10, b=0), height=350
        )
        st.plotly_chart(fig3, use_container_width=True)

    st.markdown(f"**{len(expenses)} expense records**")
    st.markdown("")

    for i, e in enumerate(expenses):
        with st.container():
            col_a, col_b, col_c = st.columns([4, 2, 1])
            col_a.markdown(f"**{e['label']}** &nbsp; <span style='color:#888;font-size:12px'>{e['category']} · {str(e.get('date',''))[:10]}</span>", unsafe_allow_html=True)
            col_b.markdown(f"<span style='color:#F5C842;font-weight:700'>{fmt(e.get('amount',0))}</span>", unsafe_allow_html=True)
            if col_c.button("🗑️", key=f"del_exp_{e['id']}"):
                expenses.pop(i)
                save("expenses", expenses)
                st.rerun()
            st.markdown("<hr style='margin:4px 0'>", unsafe_allow_html=True)
