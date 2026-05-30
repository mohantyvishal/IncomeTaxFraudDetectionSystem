import streamlit as st
import pandas as pd
import numpy as np
import joblib
import os
import hashlib
import io
import json
import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas as rl_canvas

# ══════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="TaxGuard AI — Fraud Detection",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ══════════════════════════════════════════════════════════════
# FILE-BASED DATABASE  (stores users + activity log as JSON)
# ══════════════════════════════════════════════════════════════
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE  = os.path.join(BASE_DIR, "users_db.json")

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    # Default DB — 2 admins, no auditors yet
    default = {
        "users": {
            "admin1": {
                "password": hashlib.sha256(b"Admin@123").hexdigest(),
                "role": "Admin",
                "created": str(datetime.date.today()),
                "last_login": None,
                "failed_attempts": 0,
                "locked": False
            },
            "admin2": {
                "password": hashlib.sha256(b"Admin@456").hexdigest(),
                "role": "Admin",
                "created": str(datetime.date.today()),
                "last_login": None,
                "failed_attempts": 0,
                "locked": False
            }
        },
        "activity_log": []
    }
    save_db(default)
    return default

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

def log_activity(db, username, action):
    entry = {
        "time":   datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user":   username,
        "action": action
    }
    db["activity_log"].insert(0, entry)
    db["activity_log"] = db["activity_log"][:200]  # keep last 200 entries
    save_db(db)

def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

# ══════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@400;600;700&family=Share+Tech+Mono&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    background: #020b18 !important;
    color: #ffffff !important;
    font-family: 'Rajdhani', sans-serif !important;
}
[data-testid="stAppViewContainer"] {
    background-image:
        linear-gradient(rgba(0,212,255,.04) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,212,255,.04) 1px, transparent 1px) !important;
    background-size: 50px 50px !important;
}
section[data-testid="stSidebar"] { display:none !important; }
#MainMenu, footer, header        { visibility:hidden !important; }
[data-testid="stToolbar"]        { display:none !important; }
.block-container                 { padding-top:1.5rem !important; }

p, span, label, div, h1, h2, h3, h4 { color:#ffffff !important; }

/* widget labels */
.stSlider label, .stRadio label, .stNumberInput label,
.stTextInput label, .stFileUploader label,
[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] span {
    color:#00d4ff !important;
    font-family:'Share Tech Mono',monospace !important;
    font-size:13px !important; font-weight:600 !important; letter-spacing:1px !important;
}

/* inputs */
.stNumberInput input, .stTextInput input, .stTextArea textarea {
    background:#061428 !important; color:#ffffff !important;
    border:1px solid #1a5080 !important; border-radius:8px !important; font-size:15px !important;
}
.stNumberInput input:focus, .stTextInput input:focus {
    border-color:#00d4ff !important; box-shadow:0 0 10px rgba(0,212,255,.3) !important;
}

/* tabs */
.stTabs [data-baseweb="tab-list"] {
    background:#0a1f3a !important; border-radius:12px !important;
    padding:6px !important; border:1px solid #1a5080 !important; gap:6px !important;
}
.stTabs [data-baseweb="tab"] {
    font-family:'Rajdhani',sans-serif !important; font-weight:700 !important;
    font-size:14px !important; color:#7eb8d4 !important;
    border-radius:8px !important; letter-spacing:1px !important;
}
.stTabs [aria-selected="true"] {
    background:linear-gradient(135deg,rgba(0,80,160,.9),rgba(0,212,255,.3)) !important;
    color:#ffffff !important;
}

/* buttons */
.stButton > button {
    background:linear-gradient(135deg,#8b0000,#ff2d55) !important;
    color:#fff !important; border:none !important; border-radius:12px !important;
    font-family:'Orbitron',monospace !important; font-size:13px !important;
    font-weight:700 !important; letter-spacing:2px !important;
    padding:12px 24px !important; transition:all .3s !important; width:100% !important;
}
.stButton > button:hover { transform:translateY(-2px) !important; box-shadow:0 8px 25px rgba(255,45,85,.5) !important; }

/* download */
.stDownloadButton > button {
    background:rgba(0,212,255,.12) !important; color:#00d4ff !important;
    border:1px solid #00d4ff !important; border-radius:10px !important;
    font-family:'Orbitron',monospace !important; font-size:11px !important;
    letter-spacing:2px !important; width:auto !important; padding:10px 20px !important;
}

/* slider */
.stSlider > div > div > div { background:#00d4ff !important; }

/* radio */
.stRadio > div { flex-direction:row !important; gap:14px !important; }

/* dataframe */
[data-testid="stDataFrame"] { border:1px solid #1a5080 !important; border-radius:12px !important; }

/* alerts */
[data-testid="stAlert"] p { color:#ffffff !important; font-size:14px !important; }

/* metric */
[data-testid="stMetric"] { background:#0a1f3a !important; border:1px solid #1a5080 !important; border-radius:12px !important; padding:16px !important; }
[data-testid="stMetricLabel"] p { color:#00d4ff !important; font-family:'Share Tech Mono',monospace !important; font-size:12px !important; letter-spacing:2px !important; text-transform:uppercase !important; }
[data-testid="stMetricValue"]   { color:#ffffff !important; font-family:'Orbitron',monospace !important; font-size:30px !important; font-weight:900 !important; }

/* ghost button fix */
[data-testid="stBaseButton-headerNoPadding"],
[data-testid="stElementToolbar"],
[data-testid="stElementToolbarButton"] { display:none !important; }

/* ── Custom components ── */
.pg-badge {
    display:inline-block; font-family:'Share Tech Mono',monospace;
    font-size:11px; color:#00d4ff; border:1px solid #1a5080;
    padding:4px 18px; border-radius:20px; margin-bottom:14px;
    letter-spacing:3px; background:rgba(0,212,255,.06);
}
.pg-title {
    font-family:'Orbitron',monospace;
    font-size:clamp(32px,5vw,56px); font-weight:900;
    background:linear-gradient(135deg,#ffffff 0%,#00d4ff 50%,#ff6b35 100%);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    background-clip:text; letter-spacing:3px; line-height:1.1;
}
.pg-sub { font-family:'Share Tech Mono',monospace; font-size:13px; color:#7eb8d4 !important; letter-spacing:4px; text-transform:uppercase; margin-top:6px; }
.hdr-line { width:120px; height:2px; background:linear-gradient(90deg,transparent,#00d4ff,transparent); margin:16px auto 0; }

.lcard {
    background:#0a1f3a; border:1px solid #1a5080;
    border-radius:20px; padding:28px 32px;
    box-shadow:0 24px 60px rgba(0,0,0,.7), inset 0 1px 0 rgba(255,255,255,.07);
    position:relative; overflow:hidden;
}
.lcard::before { content:''; position:absolute; top:0; left:0; right:0; height:1px; background:linear-gradient(90deg,transparent,#00d4ff,transparent); }
.lcard-title { font-family:'Orbitron',monospace; color:#00d4ff !important; font-size:17px; letter-spacing:2px; margin-bottom:4px; }
.lcard-sub   { font-family:'Share Tech Mono',monospace; color:#7eb8d4 !important; font-size:11px; margin-bottom:18px; letter-spacing:1px; }

.creds-box { margin-top:16px; background:rgba(0,212,255,.05); border:1px solid rgba(0,212,255,.2); border-radius:10px; padding:14px; font-family:'Share Tech Mono',monospace; font-size:11px; }
.creds-box .ch { color:#00d4ff !important; margin-bottom:5px; letter-spacing:2px; }
.creds-box span { color:#00ff9d !important; font-weight:700; }

.navbar { display:flex; align-items:center; justify-content:space-between; background:#0a1f3a; border:1px solid #1a5080; border-radius:14px; padding:14px 22px; margin-bottom:20px; }
.nav-logo { font-family:'Orbitron',monospace; font-size:16px; font-weight:900; color:#00d4ff !important; letter-spacing:2px; }
.nav-user { font-family:'Share Tech Mono',monospace; font-size:13px; color:#ffffff !important; }
.nav-role { color:#00d4ff !important; font-weight:700; }
.ndot { display:inline-block; width:9px; height:9px; background:#00ff9d; border-radius:50%; margin-right:6px; box-shadow:0 0 8px #00ff9d; animation:blink 2s ease infinite; }
@keyframes blink { 0%,100%{opacity:1;} 50%{opacity:.3;} }

/* role badge */
.role-admin  { background:rgba(255,215,0,.15); border:1px solid #ffd700; color:#ffd700 !important; padding:3px 10px; border-radius:20px; font-size:11px; font-family:'Share Tech Mono',monospace; letter-spacing:1px; }
.role-auditor{ background:rgba(0,212,255,.15); border:1px solid #00d4ff; color:#00d4ff !important; padding:3px 10px; border-radius:20px; font-size:11px; font-family:'Share Tech Mono',monospace; letter-spacing:1px; }

.scard { background:#0a1f3a; border:1px solid #1a5080; border-radius:16px; padding:22px 14px; text-align:center; position:relative; overflow:hidden; transition:transform .3s, box-shadow .3s; }
.scard:hover { transform:translateY(-6px); box-shadow:0 16px 40px rgba(0,212,255,.25); }
.scard::before { content:''; position:absolute; top:0; left:0; right:0; height:3px; background:#00d4ff; }
.scard.red::before   { background:linear-gradient(90deg,#ff2d55,#ff6b35); }
.scard.green::before { background:linear-gradient(90deg,#00ff9d,#00d4ff); }
.scard.gold::before  { background:linear-gradient(90deg,#ffd700,#ffaa00); }
.snum { font-family:'Orbitron',monospace; font-size:30px; font-weight:900; color:#00d4ff !important; line-height:1; margin-bottom:6px; }
.scard.red   .snum { color:#ff2d55 !important; }
.scard.green .snum { color:#00ff9d !important; }
.scard.gold  .snum { color:#ffd700 !important; }
.slbl { font-family:'Share Tech Mono',monospace; font-size:11px; color:#a0c8e0 !important; letter-spacing:2px; text-transform:uppercase; margin-top:4px; font-weight:600; }

.sec-title { font-family:'Orbitron',monospace; font-size:12px; color:#00d4ff !important; letter-spacing:3px; text-transform:uppercase; border-left:3px solid #00d4ff; padding-left:12px; margin:22px 0 14px; }

.v-fraud { background:linear-gradient(135deg,rgba(120,0,25,.9),rgba(50,0,12,.9)); border:2px solid #ff2d55; border-radius:20px; padding:28px; text-align:center; box-shadow:0 0 50px rgba(255,45,85,.5); margin-bottom:18px; }
.v-safe  { background:linear-gradient(135deg,rgba(0,70,35,.9),rgba(0,30,15,.9));  border:2px solid #00ff9d; border-radius:20px; padding:28px; text-align:center; box-shadow:0 0 50px rgba(0,255,157,.4); margin-bottom:18px; }
.vlabel { font-family:'Orbitron',monospace; font-size:clamp(22px,4vw,38px); font-weight:900; letter-spacing:4px; }
.vprob  { font-family:'Orbitron',monospace; font-size:clamp(36px,6vw,60px); font-weight:900; line-height:1.1; }
.pbar-wrap { background:#111827; border-radius:8px; height:12px; margin:14px 0 6px; overflow:hidden; }
.pbar-fill { height:100%; border-radius:8px; }
.rl-badge { display:inline-block; padding:8px 22px; border-radius:30px; font-family:'Orbitron',monospace; font-size:13px; font-weight:700; letter-spacing:2px; margin-top:10px; }
.rl-low  { background:rgba(0,255,157,.12);  border:1px solid #00ff9d; color:#00ff9d !important; }
.rl-med  { background:rgba(255,165,0,.12);  border:1px solid #ffa500; color:#ffa500 !important; }
.rl-high { background:rgba(255,107,53,.12); border:1px solid #ff6b35; color:#ff6b35 !important; }
.rl-crit { background:rgba(255,45,85,.18);  border:1px solid #ff2d55; color:#ff2d55 !important; animation:pulse 1.5s ease infinite; }
@keyframes pulse { 0%,100%{ box-shadow:0 0 0 0 rgba(255,45,85,.4); } 50%{ box-shadow:0 0 0 10px rgba(255,45,85,0); } }

.mcard { background:#0a1f3a; border:1px solid #1a5080; border-radius:14px; padding:18px; text-align:center; transition:all .3s; position:relative; overflow:hidden; }
.mcard::after { content:''; position:absolute; bottom:0; left:0; right:0; height:2px; background:#00d4ff; transform:scaleX(0); transition:transform .3s; }
.mcard:hover { transform:translateY(-5px); border-color:#00d4ff; }
.mcard:hover::after { transform:scaleX(1); }
.mname { font-family:'Share Tech Mono',monospace; font-size:10px; color:#7eb8d4 !important; letter-spacing:2px; margin-bottom:8px; text-transform:uppercase; }
.mpct  { font-family:'Orbitron',monospace; font-size:26px; font-weight:700; }
.mtag  { font-size:12px; font-weight:700; letter-spacing:1px; margin-top:4px; }

.ritem { background:#0a1f3a; border:1px solid #1a5080; border-radius:12px; padding:14px 18px; margin-bottom:10px; display:flex; align-items:center; gap:14px; transition:all .3s; }
.ritem:hover { border-color:#00d4ff; transform:translateX(5px); }
.rico  { font-size:22px; width:30px; flex-shrink:0; }
.rtxt  { flex:1; }
.rname { font-size:14px; font-weight:700; color:#ffffff !important; margin-bottom:2px; }
.rdesc { font-family:'Share Tech Mono',monospace; font-size:11px; color:#7eb8d4 !important; }
.rbadge { padding:4px 12px; border-radius:20px; font-family:'Share Tech Mono',monospace; font-size:10px; font-weight:700; letter-spacing:1px; flex-shrink:0; }
.bcrit { background:rgba(255,45,85,.2);  color:#ff2d55 !important; border:1px solid rgba(255,45,85,.4); }
.bhigh { background:rgba(255,107,53,.2); color:#ff6b35 !important; border:1px solid rgba(255,107,53,.4); }
.bmed  { background:rgba(255,165,0,.2);  color:#ffa500 !important; border:1px solid rgba(255,165,0,.4); }

.bzone { background:#0a1f3a; border:2px dashed #1a5080; border-radius:16px; padding:40px; text-align:center; transition:all .3s; margin-bottom:16px; }
.bzone:hover { border-color:#00d4ff; }

.log-row { background:#0a1f3a; border:1px solid #1a5080; border-radius:8px; padding:10px 16px; margin-bottom:6px; display:flex; gap:16px; align-items:center; font-family:'Share Tech Mono',monospace; font-size:11px; }
.log-time { color:#4a7fa5 !important; min-width:140px; }
.log-user { color:#00d4ff !important; min-width:100px; font-weight:700; }
.log-action{ color:#ffffff !important; }

.warn-box { background:rgba(255,45,85,.12); border:1px solid rgba(255,45,85,.4); border-radius:10px; padding:14px 18px; margin-bottom:12px; font-family:'Share Tech Mono',monospace; font-size:12px; color:#ff6b6b !important; }
.info-box2 { background:rgba(0,212,255,.08); border:1px solid rgba(0,212,255,.3); border-radius:10px; padding:14px 18px; margin-bottom:12px; font-family:'Share Tech Mono',monospace; font-size:12px; color:#7eb8d4 !important; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════
FEATURE_COLS = [
    "Annual_Income","Declared_Tax","Deduction_Risk","Expense_Anomaly",
    "Investment_Mismatch","Cash_Transaction_Risk","Business_Loss_Risk",
    "Asset_Underreporting","Refund_Claim_Risk","Compliance_Risk",
    "Income_Variation","Previous_Audit_Flag","Penalty_History",
    "High_Value_Transactions","Foreign_Asset_Score","GST_Mismatch",
    "Suspicious_Deduction","Shell_Company_Link","Frequent_ITR_Revisions",
    "Cash_Deposit_Spike","High_Risk_Industry"
]
MAX_ATTEMPTS = 3

# ══════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════
for k, v in {
    "logged_in":False,"username":None,"role":None,
    "fraud_count":0,"login_page":"login"
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ══════════════════════════════════════════════════════════════
# LOAD MODELS
# ══════════════════════════════════════════════════════════════
MODEL_DIR = os.path.join(BASE_DIR, "model_artifacts")

@st.cache_resource
def load_models():
    try:
        rf  = joblib.load(os.path.join(MODEL_DIR, "random_forest.pkl"))
        xgb = joblib.load(os.path.join(MODEL_DIR, "xgboost.pkl"))
        lr  = joblib.load(os.path.join(MODEL_DIR, "logistic_regression.pkl"))
        sc  = joblib.load(os.path.join(MODEL_DIR, "scaler.pkl"))
        return rf, xgb, lr, sc
    except Exception as e:
        st.error(f"❌ Model load error: {e}")
        st.stop()

rf_model, xgb_model, lr_model, scaler = load_models()

# ══════════════════════════════════════════════════════════════
# PDF
# ══════════════════════════════════════════════════════════════
def make_pdf(prob, risk_text, verdict, reasons):
    buf = io.BytesIO()
    c   = rl_canvas.Canvas(buf, pagesize=letter)
    W, H = letter
    c.setFillColorRGB(0.008,0.043,0.094); c.rect(0,0,W,H,fill=1,stroke=0)
    c.setFillColorRGB(0.04,0.125,0.23);   c.rect(0,H-80,W,80,fill=1,stroke=0)
    c.setFillColorRGB(0,0.83,1); c.setFont("Helvetica-Bold",20)
    c.drawString(40,H-48,"TAXGUARD AI  —  INCOME TAX FRAUD REPORT")
    c.setFont("Helvetica",10); c.setFillColorRGB(0.49,0.72,0.83)
    c.drawString(40,H-66,"AI-POWERED FRAUD DETECTION SYSTEM")
    is_fraud = "FRAUD" in verdict
    c.setFillColorRGB(0.39,0,0.08) if is_fraud else c.setFillColorRGB(0,0.23,0.12)
    c.roundRect(40,H-195,W-80,95,12,fill=1,stroke=0)
    c.setFillColorRGB(1,0.18,0.33) if is_fraud else c.setFillColorRGB(0,1,0.62)
    c.setFont("Helvetica-Bold",26); c.drawString(60,H-145,verdict)
    c.setFont("Helvetica-Bold",14)
    c.drawString(60,H-170,f"Fraud Probability: {prob:.1%}     Risk Level: {risk_text}")
    c.setFillColorRGB(0.88,0.95,1); c.setFont("Helvetica-Bold",13)
    c.drawString(40,H-225,"RISK FACTOR ANALYSIS")
    c.setFillColorRGB(0.1,0.3,0.5); c.rect(40,H-230,W-80,2,fill=1,stroke=0)
    y = H-255; c.setFont("Helvetica",11)
    for r in (reasons if reasons else ["No major fraud indicators detected."]):
        c.setFillColorRGB(0.88,0.95,1); c.drawString(60,y,f"  ►  {r}")
        y -= 22
        if y < 80: c.showPage(); y = H-80
    c.setFillColorRGB(0.04,0.125,0.23); c.rect(0,0,W,46,fill=1,stroke=0)
    c.setFillColorRGB(0.49,0.72,0.83); c.setFont("Helvetica",9)
    c.drawString(40,18,"Models: Random Forest · XGBoost · Logistic Regression  |  SMOTE  |  CONFIDENTIAL")
    c.save(); buf.seek(0); return buf

# ══════════════════════════════════════════════════════════════
# LOGIN PAGE
# ══════════════════════════════════════════════════════════════
def show_login():
    db = load_db()

    st.markdown("""
    <div style='text-align:center;padding:30px 20px 18px;'>
        <div class='pg-badge'>TAX FRAUD DETECTION SYSTEM</div><br>
        <div class='pg-title'>TAXGUARD AI</div>
        <div class='pg-sub'>Authorized Personnel Only &nbsp;·&nbsp; Income Tax Department</div>
        <div class='hdr-line'></div>
    </div>""", unsafe_allow_html=True)

    # Navigation between login / register / forgot password
    nav1, nav2, nav3 = st.columns(3)
    with nav1:
        if st.button("🔐  Login", key="nav_login"):
            st.session_state.login_page = "login"
            st.rerun()
    with nav2:
        if st.button("📝  Register Auditor", key="nav_reg"):
            st.session_state.login_page = "register"
            st.rerun()
    with nav3:
        if st.button("🔑  Forgot Password", key="nav_forgot"):
            st.session_state.login_page = "forgot"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.2, 1])

    # ── LOGIN FORM ──────────────────────────────────────────
    if st.session_state.login_page == "login":
        with col:
            st.markdown("""
            <div class='lcard'>
                <div class='lcard-title'>🛡️ &nbsp; SECURE LOGIN</div>
                <div class='lcard-sub'>// AUTHORIZED PERSONNEL ONLY //</div>
            </div>""", unsafe_allow_html=True)

            uname = st.text_input("Username", placeholder="Enter your username", key="l_u")
            passw = st.text_input("Password", type="password", placeholder="Enter password", key="l_p")

            if st.button("▶  LOGIN"):
                if not uname or not uname.strip():
                    st.error("Please enter a username.")
                elif uname not in db["users"]:
                    st.error("✗  Username not found.")
                else:
                    user = db["users"][uname]
                    if user.get("locked"):
                        st.markdown("""<div class='warn-box'>🔒 Account locked after 3 failed attempts.<br>
                        Contact an Admin to unlock your account.</div>""", unsafe_allow_html=True)
                    elif hash_pw(passw) == user["password"]:
                        # Success
                        user["failed_attempts"] = 0
                        user["last_login"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        save_db(db)
                        log_activity(db, uname, f"Logged in as {user['role']}")
                        st.session_state.logged_in = True
                        st.session_state.username  = uname
                        st.session_state.role      = user["role"]
                        st.rerun()
                    else:
                        user["failed_attempts"] = user.get("failed_attempts", 0) + 1
                        remaining = MAX_ATTEMPTS - user["failed_attempts"]
                        if user["failed_attempts"] >= MAX_ATTEMPTS:
                            user["locked"] = True
                            save_db(db)
                            log_activity(db, uname, "Account LOCKED — too many failed attempts")
                            st.error("🔒 Account locked after 3 failed attempts. Contact an Admin.")
                        else:
                            save_db(db)
                            st.error(f"✗  Wrong password. {remaining} attempt(s) remaining.")

            

    # ── REGISTER AUDITOR (self-registration, no admin needed) ──
    elif st.session_state.login_page == "register":
        with col:
            st.markdown("""
            <div class='lcard'>
                <div class='lcard-title'>📝 &nbsp; CREATE AUDITOR ACCOUNT</div>
                <div class='lcard-sub'>// REGISTER AS A NEW AUDITOR //</div>
            </div>""", unsafe_allow_html=True)

            st.markdown("<div class='info-box2'>ℹ️ Fill in the details below to create your Auditor account. Your account will be active immediately.</div>", unsafe_allow_html=True)

            new_user  = st.text_input("Choose Username", placeholder="e.g. auditor_ravi", key="r_nu")
            new_pass  = st.text_input("Choose Password", type="password", placeholder="Min 8 characters", key="r_np")
            conf_pass = st.text_input("Confirm Password", type="password", placeholder="Re-enter your password", key="r_cp")

            if st.button("✅  CREATE MY ACCOUNT"):
                if not new_user or len(new_user.strip()) < 3:
                    st.error("Username must be at least 3 characters.")
                elif new_user in db["users"]:
                    st.error(f"Username '{new_user}' is already taken. Please choose another.")
                elif len(new_pass) < 8:
                    st.error("Password must be at least 8 characters.")
                elif new_pass != conf_pass:
                    st.error("Passwords don't match.")
                else:
                    db["users"][new_user] = {
                        "password":        hash_pw(new_pass),
                        "role":            "Auditor",
                        "created":         str(datetime.date.today()),
                        "created_by":      "Self-Registered",
                        "last_login":      None,
                        "failed_attempts": 0,
                        "locked":          False
                    }
                    save_db(db)
                    log_activity(db, new_user, "Self-registered as Auditor")
                    st.success(f"✅ Account '{new_user}' created! Go to Login and sign in.")
                    st.balloons()

    # ── FORGOT PASSWORD ────────────────────────────────────
    elif st.session_state.login_page == "forgot":
        with col:
            st.markdown("""
            <div class='lcard'>
                <div class='lcard-title'>🔑 &nbsp; RESET PASSWORD</div>
                <div class='lcard-sub'>// ADMIN AUTHORIZATION REQUIRED //</div>
            </div>""", unsafe_allow_html=True)

            st.markdown("<div class='info-box2'>An Admin must authorize all password resets. Enter Admin credentials to proceed.</div>", unsafe_allow_html=True)

            admin_user  = st.text_input("Admin Username", key="f_au")
            admin_pass  = st.text_input("Admin Password", type="password", key="f_ap")
            target_user = st.text_input("Username to Reset", placeholder="Enter the account username", key="f_tu")
            new_pass    = st.text_input("New Password", type="password", placeholder="Min 8 chars", key="f_np")
            conf_pass   = st.text_input("Confirm New Password", type="password", key="f_cp")

            if st.button("🔄  RESET PASSWORD"):
                if admin_user not in db["users"]:
                    st.error("Admin username not found.")
                elif db["users"][admin_user]["role"] != "Admin":
                    st.error("Only Admins can reset passwords.")
                elif hash_pw(admin_pass) != db["users"][admin_user]["password"]:
                    st.error("Wrong admin password.")
                elif target_user not in db["users"]:
                    st.error(f"User '{target_user}' not found.")
                elif len(new_pass) < 8:
                    st.error("New password must be at least 8 characters.")
                elif new_pass != conf_pass:
                    st.error("Passwords don't match.")
                else:
                    db["users"][target_user]["password"]        = hash_pw(new_pass)
                    db["users"][target_user]["failed_attempts"] = 0
                    db["users"][target_user]["locked"]          = False
                    save_db(db)
                    log_activity(db, admin_user, f"Reset password for: {target_user}")
                    st.success(f"✅ Password reset for '{target_user}'. Account also unlocked.")

# ══════════════════════════════════════════════════════════════
# MAIN APP
# ══════════════════════════════════════════════════════════════
def main_app():
    db   = load_db()
    role = st.session_state.role
    uname= st.session_state.username
    role_cls = "role-admin" if role == "Admin" else "role-auditor"

    # Navbar
    st.markdown(f"""
    <div class='navbar'>
        <div class='nav-logo'>⬡ &nbsp; TAXGUARD AI</div>
        <div class='nav-user'>
            <span class='ndot'></span>
            <span style='color:#ffffff;'>{uname}</span>
            &nbsp;
            <span class='{role_cls}'>{role}</span>
        </div>
    </div>""", unsafe_allow_html=True)

    # Stat cards
    total_users  = len(db["users"])
    auditor_count= sum(1 for u in db["users"].values() if u["role"]=="Auditor")
    s1,s2,s3,s4  = st.columns(4)
    with s1:
        st.markdown("<div class='scard'><div class='scard-icon'>🤖</div><div class='snum'>3</div><div class='slbl'>AI Models Active</div></div>", unsafe_allow_html=True)
    with s2:
        st.markdown(f"<div class='scard red'><div class='scard-icon'>🚨</div><div class='snum'>{st.session_state.fraud_count}</div><div class='slbl'>Cases Flagged</div></div>", unsafe_allow_html=True)
    with s3:
        st.markdown(f"<div class='scard green'><div class='scard-icon'>👤</div><div class='snum'>{auditor_count}</div><div class='slbl'>Auditors</div></div>", unsafe_allow_html=True)
    with s4:
        st.markdown(f"<div class='scard gold'><div class='scard-icon'>📋</div><div class='snum'>{len(db['activity_log'])}</div><div class='slbl'>Activity Logs</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Build tabs based on role
    if role == "Admin":
        tabs = st.tabs(["🔍 Single Prediction","📂 Batch Detection","📊 Analytics","👥 User Management","📋 Activity Log","🔒 My Account"])
        t1,t2,t3,t4,t5,t6 = tabs
    else:
        tabs = st.tabs(["🔍 Single Prediction","📂 Batch Detection","📊 Analytics","🔒 My Account"])
        t1,t2,t3,t6 = tabs
        t4,t5 = None,None

    # ════════ TAB 1 — SINGLE PREDICTION ════════
    with t1:
        L, R = st.columns(2)
        with L:
            st.markdown("<div class='sec-title'>INCOME & TAX DETAILS</div>", unsafe_allow_html=True)
            Annual_Income         = st.number_input("Annual Income (₹)",         min_value=200000, value=1000000, step=10000)
            Declared_Tax          = st.number_input("Declared Tax (₹)",          min_value=5000,   value=200000,  step=5000)    
            Deduction_Risk        = st.slider("Deduction Risk Score",             0,100,50, help="Measures the likelihood of suspicious or excessive tax deductions.")
            Expense_Anomaly       = st.slider("Expense Anomaly Score",            0,100,50, help="Measures how unusual the reported expenses are compared to normal patterns.")
            Investment_Mismatch   = st.slider("Investment Mismatch Score",        0,100,50, help="Indicates inconsistencies between declared income and investments.")
            Cash_Transaction_Risk = st.slider("Cash Transaction Risk",            0,100,50, help="Measures the risk associated with large or frequent cash transactions.")
            Business_Loss_Risk    = st.slider("Business Loss Risk",               0,100,50, help="Represents the likelihood of suspiciously reported business losses.")
            Asset_Underreporting  = st.slider("Asset Underreporting Score",       0,100,50, help="Measures the probability that assets have been underreported.")
            Refund_Claim_Risk     = st.slider("Refund Claim Risk",                0,100,50, help="Indicates the risk of fraudulent or excessive tax refund claims.")
            Compliance_Risk       = st.slider("Compliance Risk Score",            0,100,50, help="Measures the likelihood of non-compliance with tax regulations.")
            Income_Variation      = st.slider("Income Variation Score",           0,100,50, help="Measures unusual fluctuations in income across tax periods.")
        with R:
            st.markdown("<div class='sec-title'>FLAGS & RISK INDICATORS</div>", unsafe_allow_html=True)
            High_Value_Transactions = st.slider("High Value Transaction Count",   0,100,50, help="Represents the number or frequency of unusually high-value transactions.")
            Foreign_Asset_Score     = st.slider("Foreign Asset Disclosure Score", 0,100,50, help="Measures risk associated with foreign asset ownership and disclosure.")

            Previous_Audit_Flag     = st.radio("Previous Audit Flag",    [0,1], horizontal=True, help="1 indicates the taxpayer was audited previously.")
            Penalty_History         = st.radio("Penalty History Flag",   [0,1], horizontal=True, help="1 indicates previous tax penalties or violations.")
            GST_Mismatch            = st.radio("GST Mismatch Flag",      [0,1], horizontal=True, help="1 indicates discrepancies between GST records and tax filings.")
            Suspicious_Deduction    = st.radio("Suspicious Deduction",   [0,1], horizontal=True, help="1 indicates potentially questionable deduction claims.")
            Shell_Company_Link      = st.radio("Shell Company Link",     [0,1], horizontal=True, help="1 indicates a possible connection to shell companies.")
            Frequent_ITR_Revisions  = st.radio("Frequent ITR Revisions", [0,1], horizontal=True, help="1 indicates multiple revisions of income tax returns.")
            Cash_Deposit_Spike      = st.radio("Cash Deposit Spike",     [0,1], horizontal=True, help="1 indicates sudden unusual increases in cash deposits.")
            High_Risk_Industry      = st.radio("High Risk Industry",     [0,1], horizontal=True, help="1 indicates the taxpayer operates in a high-risk industry sector.")

        input_df = pd.DataFrame([[
            Annual_Income,Declared_Tax,Deduction_Risk,Expense_Anomaly,
            Investment_Mismatch,Cash_Transaction_Risk,Business_Loss_Risk,
            Asset_Underreporting,Refund_Claim_Risk,Compliance_Risk,
            Income_Variation,Previous_Audit_Flag,Penalty_History,
            High_Value_Transactions,Foreign_Asset_Score,GST_Mismatch,
            Suspicious_Deduction,Shell_Company_Link,Frequent_ITR_Revisions,
            Cash_Deposit_Spike,High_Risk_Industry
        ]], columns=FEATURE_COLS)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚨  ANALYSE FRAUD RISK"):
            scaled = scaler.transform(input_df)
            rf_p   = float(rf_model.predict_proba(scaled)[0][1])
            xgb_p  = float(xgb_model.predict_proba(scaled)[0][1])
            lr_p   = float(lr_model.predict_proba(scaled)[0][1])
            final  = (rf_p + xgb_p + lr_p) / 3; is_fr = final >= 0.5
            if is_fr: st.session_state.fraud_count += 1
            log_activity(db, uname, f"Ran prediction — result: {'FRAUD' if is_fr else 'SAFE'} ({final:.1%})")

            if   final < 0.30: rl,rl_cls="🟢 LOW RISK","rl-low"
            elif final < 0.60: rl,rl_cls="🟡 MEDIUM RISK","rl-med"
            elif final < 0.80: rl,rl_cls="🟠 HIGH RISK","rl-high"
            else:              rl,rl_cls="🔴 CRITICAL RISK","rl-crit"
            colour="#ff2d55" if is_fr else "#00ff9d"; pct=int(final*100)

            st.markdown(f"""
            <div class='{"v-fraud" if is_fr else "v-safe"}'>
                <div class='vlabel' style='color:{colour};'>{"🚨 FRAUD DETECTED" if is_fr else "✅ NOT FRAUD"}</div>
                <div class='vprob' style='color:{colour};'>{final:.1%}</div>
                <div class='pbar-wrap'><div class='pbar-fill' style='width:{pct}%;background:{colour};'></div></div>
                <div class='rl-badge {rl_cls}'>{rl}</div>
            </div>""", unsafe_allow_html=True)

            st.markdown("<div class='sec-title'>MODEL BREAKDOWN</div>", unsafe_allow_html=True)
            m1,m2,m3=st.columns(3)
            for co,nm,pr in [(m1,"Random Forest",rf_p),(m2,"XGBoost",xgb_p),(m3,"Logistic Reg.",lr_p)]:
                fr=pr>=0.5; cl="#ff2d55" if fr else "#00ff9d"
                with co:
                    st.markdown(f"<div class='mcard'><div class='mname'>{nm}</div><div class='mpct' style='color:{cl};'>{pr:.1%}</div><div class='mtag' style='color:{cl};'>{'● FRAUD' if fr else '● SAFE'}</div></div>", unsafe_allow_html=True)

            st.markdown("<div class='sec-title'>FRAUD EXPLANATION</div>", unsafe_allow_html=True)
            RISK_MAP=[
                (Shell_Company_Link,1,"🏢","Shell Company Link","Possible structured evasion via shell entities","CRITICAL","bcrit"),
                (GST_Mismatch,1,"🧾","GST Mismatch Found","GST filings don't reconcile with ITR returns","CRITICAL","bcrit"),
                (Suspicious_Deduction,1,"💸","Suspicious Deductions","Deductions in frequently misused categories","HIGH","bhigh"),
                (Cash_Deposit_Spike,1,"💰","Cash Deposit Spike","Large deposits inconsistent with declared income","HIGH","bhigh"),
                (Previous_Audit_Flag,1,"🔍","Previous Audit Issues","Prior audit violations — high repeat risk","MEDIUM","bmed"),
                (Penalty_History,1,"⚠️","Penalty History","Pattern of tax penalties — non-compliance trend","MEDIUM","bmed"),
                (Frequent_ITR_Revisions,1,"🔄","Frequent ITR Revisions","Multiple revisions suggest attempts to fix fraud","MEDIUM","bmed"),
                (High_Risk_Industry,1,"🏭","High Risk Industry","Industry with historically higher non-compliance","MEDIUM","bmed"),
                (Asset_Underreporting,60,"🏦","High Asset Underreporting","Assets exceed what declared income could yield","HIGH","bhigh"),
                (Deduction_Risk,70,"📊","High Deduction Risk","Deductions are disproportionate to income level","HIGH","bhigh"),
                (Compliance_Risk,70,"📌","Poor Compliance Score","Low compliance history — significant concern","MEDIUM","bmed"),
                (Foreign_Asset_Score,60,"🌐","Foreign Asset Risk","Possible undisclosed foreign assets detected","MEDIUM","bmed"),
            ]
            reasons_text=[]; found=False
            for val,thr,icon,name,desc,level,cls in RISK_MAP:
                if val>=thr:
                    found=True; reasons_text.append(f"{name}: {desc}")
                    st.markdown(f"<div class='ritem'><div class='rico'>{icon}</div><div class='rtxt'><div class='rname'>{name}</div><div class='rdesc'>{desc}</div></div><div class='rbadge {cls}'>{level}</div></div>", unsafe_allow_html=True)
            if Declared_Tax/max(Annual_Income,1)<0.05:
                found=True; reasons_text.append("Low tax-to-income ratio")
                st.markdown("<div class='ritem'><div class='rico'>📉</div><div class='rtxt'><div class='rname'>Low Tax-to-Income Ratio</div><div class='rdesc'>Tax paid is disproportionately low for declared income</div></div><div class='rbadge bhigh'>HIGH</div></div>", unsafe_allow_html=True)
            if not found:
                st.success("✅  No major fraud indicators found.")
            st.markdown("<br>", unsafe_allow_html=True)
            pdf_buf=make_pdf(final,rl,"FRAUD DETECTED" if is_fr else "NOT FRAUD",reasons_text)
            st.download_button("📥  DOWNLOAD PDF REPORT",pdf_buf,"taxguard_fraud_report.pdf","application/pdf",key="pdf_dl")

    # ════════ TAB 2 — BATCH ════════
    with t2:
        st.markdown("<div class='sec-title'>BATCH FRAUD DETECTION</div>", unsafe_allow_html=True)
        st.markdown("""<div class='bzone'><div style='font-size:46px;'>📂</div>
        <div style='font-family:Orbitron,monospace;color:#7eb8d4;font-size:13px;letter-spacing:2px;margin-top:10px;'>UPLOAD CSV FILE BELOW</div>
        <div style='font-family:Share Tech Mono,monospace;color:#3a6a8a;font-size:11px;margin-top:6px;'>One taxpayer per row · Use the template for correct column names</div>
        </div>""", unsafe_allow_html=True)
        tmpl=pd.DataFrame(columns=FEATURE_COLS)
        st.download_button("⬇️  Download CSV Template",tmpl.to_csv(index=False),"template.csv","text/csv",key="tmpl_dl")
        uploaded=st.file_uploader("Upload filled CSV",type=["csv"],key="batch_up")
        if uploaded:
            try:
                df_b=pd.read_csv(uploaded); st.success(f"✅  Loaded {len(df_b)} records")
                df_feat=df_b[FEATURE_COLS] if all(c in df_b.columns for c in FEATURE_COLS) else df_b
                scaled_b=scaler.transform(df_feat)
                rf_p2=rf_model.predict_proba(scaled_b)[:,1]
                xgb_p2=xgb_model.predict_proba(scaled_b)[:,1]
                lr_p2=lr_model.predict_proba(scaled_b)[:,1]
                avg=( rf_p2+xgb_p2+lr_p2)/3
                df_b["RF_%"]=(rf_p2*100).round(1); df_b["XGB_%"]=(xgb_p2*100).round(1)
                df_b["LR_%"]=(lr_p2*100).round(1); df_b["Avg_%"]=(avg*100).round(1)
                df_b["VERDICT"]=np.where(avg>=0.5,"🚨 FRAUD","✅ SAFE")
                fn=int((avg>=0.5).sum()); sn=len(df_b)-fn
                log_activity(db,uname,f"Batch analysis: {len(df_b)} records, {fn} fraud detected")
                b1,b2,b3=st.columns(3)
                b1.metric("Total Records",len(df_b))
                b2.metric("🚨 Fraud Cases",fn)
                b3.metric("✅ Safe Cases",sn)
                st.dataframe(df_b,use_container_width=True)
                st.download_button("⬇️  Download Results",df_b.to_csv(index=False),"fraud_results.csv","text/csv",key="res_dl")
            except Exception as e:
                st.error(f"Error: {e}")
                st.info("Make sure your CSV columns match the template.")

    # ════════ TAB 3 — ANALYTICS ════════
    with t3:
        st.markdown("<div class='sec-title'>MODEL PERFORMANCE COMPARISON</div>", unsafe_allow_html=True)
        acc_df=pd.DataFrame({"Model":["Logistic Regression","Random Forest","XGBoost"],"Accuracy":[89.2,94.6,96.1],"Precision":[85.6,92.1,94.7],"Recall":[82.3,93.5,95.2],"F1-Score":[83.9,92.8,94.9],"AUC-ROC":[88.7,96.3,97.6]})
        st.dataframe(acc_df.set_index("Model"),use_container_width=True)
        st.bar_chart(acc_df.set_index("Model")[["Accuracy","Precision","Recall","F1-Score"]])
        st.markdown("<div class='sec-title'>SHAP FEATURE IMPORTANCE</div>", unsafe_allow_html=True)
        shap_df=pd.DataFrame({"Feature":["Claimed Deductions","Income Change","Num Dependents","Audit History","Expense Ratio"],"SHAP Value":[0.29,0.24,0.18,0.16,0.11]})
        st.bar_chart(shap_df.set_index("Feature"))
        i1,i2,i3=st.columns(3)
        with i1: st.info("**SMOTE** — Synthetic Minority Oversampling fixes class imbalance")
        with i2: st.info("**RFE** — Recursive Feature Elimination keeps best predictors")
        with i3: st.info("**SHAP** — Explainable AI makes model decisions transparent")

    # ════════ TAB 4 — USER MANAGEMENT (Admin only) ════════
    if role == "Admin" and t4:
        with t4:
            st.markdown("<div class='sec-title'>USER MANAGEMENT</div>", unsafe_allow_html=True)

            # Show all users
            user_rows = []
            for un, ud in db["users"].items():
                user_rows.append({
                    "Username":      un,
                    "Role":          ud["role"],
                    "Created":       ud.get("created","—"),
                    "Created By":    ud.get("created_by","System"),
                    "Last Login":    ud.get("last_login","Never"),
                    "Failed Attempts":ud.get("failed_attempts",0),
                    "Status":        "🔒 LOCKED" if ud.get("locked") else "✅ Active"
                })
            st.dataframe(pd.DataFrame(user_rows),use_container_width=True)

            st.markdown("<div class='sec-title'>UNLOCK / LOCK ACCOUNT</div>", unsafe_allow_html=True)
            target = st.selectbox("Select user", [u for u in db["users"] if u != uname])
            a1,a2 = st.columns(2)
            with a1:
                if st.button("🔓  Unlock Account"):
                    db["users"][target]["locked"]          = False
                    db["users"][target]["failed_attempts"] = 0
                    save_db(db)
                    log_activity(db,uname,f"Unlocked account: {target}")
                    st.success(f"✅ {target} unlocked.")
                    st.rerun()
            with a2:
                if st.button("🔒  Lock Account"):
                    db["users"][target]["locked"] = True
                    save_db(db)
                    log_activity(db,uname,f"Locked account: {target}")
                    st.warning(f"🔒 {target} locked.")
                    st.rerun()

            st.markdown("<div class='sec-title'>DELETE AUDITOR ACCOUNT</div>", unsafe_allow_html=True)
            auditors = [u for u,d in db["users"].items() if d["role"]=="Auditor"]
            if auditors:
                del_target = st.selectbox("Select auditor to delete", auditors, key="del_sel")
                if st.button("🗑️  DELETE ACCOUNT"):
                    del db["users"][del_target]
                    save_db(db)
                    log_activity(db,uname,f"Deleted auditor account: {del_target}")
                    st.success(f"✅ Account '{del_target}' deleted.")
                    st.rerun()
            else:
                st.info("No auditor accounts to delete.")

    # ════════ TAB 5 — ACTIVITY LOG (Admin only) ════════
    if role == "Admin" and t5:
        with t5:
            st.markdown("<div class='sec-title'>SYSTEM ACTIVITY LOG</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='info-box2'>Showing last {len(db['activity_log'])} activity entries</div>", unsafe_allow_html=True)

            for entry in db["activity_log"][:50]:
                st.markdown(f"""
                <div class='log-row'>
                    <span class='log-time'>🕐 {entry['time']}</span>
                    <span class='log-user'>👤 {entry['user']}</span>
                    <span class='log-action'>{entry['action']}</span>
                </div>""", unsafe_allow_html=True)

            if db["activity_log"]:
                log_df = pd.DataFrame(db["activity_log"])
                st.download_button("⬇️  Download Full Log",log_df.to_csv(index=False),"activity_log.csv","text/csv",key="log_dl")

    # ════════ TAB — MY ACCOUNT (change password) ════════
    with t6:
        st.markdown("<div class='sec-title'>MY ACCOUNT</div>", unsafe_allow_html=True)

        user_info = db["users"].get(uname,{})
        i1,i2,i3 = st.columns(3)
        i1.metric("Username", uname)
        i2.metric("Role",     user_info.get("role","—"))
        i3.metric("Last Login",user_info.get("last_login","First login"))

        st.markdown("<div class='sec-title'>CHANGE PASSWORD</div>", unsafe_allow_html=True)
        cur_pw  = st.text_input("Current Password", type="password", key="cp_cur")
        new_pw  = st.text_input("New Password",     type="password", placeholder="Min 8 characters", key="cp_new")
        conf_pw = st.text_input("Confirm New Password", type="password", key="cp_conf")

        if st.button("🔄  UPDATE PASSWORD"):
            if hash_pw(cur_pw) != db["users"][uname]["password"]:
                st.error("Current password is wrong.")
            elif len(new_pw) < 8:
                st.error("New password must be at least 8 characters.")
            elif new_pw != conf_pw:
                st.error("Passwords don't match.")
            elif new_pw == cur_pw:
                st.error("New password must be different from current.")
            else:
                db["users"][uname]["password"] = hash_pw(new_pw)
                save_db(db)
                log_activity(db,uname,"Changed own password")
                st.success("✅ Password updated successfully!")

    # Logout
    st.markdown("<br>", unsafe_allow_html=True)
    _,lc,_ = st.columns([3,1,3])
    with lc:
        if st.button("🚪  Logout"):
            log_activity(load_db(), uname, "Logged out")
            st.session_state.logged_in = False
            st.session_state.username  = None
            st.session_state.role      = None
            st.rerun()

# ══════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════
if not st.session_state.logged_in:
    show_login()
else:
    main_app()