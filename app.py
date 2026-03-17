import streamlit as st
import pandas as pd
import requests
import tensorflow as tf
from PIL import Image
import numpy as np
import base64
from io import BytesIO
from datetime import datetime
import warnings

# إخفاء التنبيهات الزائدة
warnings.filterwarnings('ignore')
tf.get_logger().setLevel('ERROR')

# --- 1️⃣ CONFIGURATION & BRANDING CSS ---
st.set_page_config(page_title="AuditChain AI", layout="wide", page_icon="🛡️")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');
    
    :root {
      --deep-navy: #0A192F;
      --audit-lime: #BEF264;
      --glass: rgba(255, 255, 255, 0.03);
      --border-color: rgba(190, 242, 100, 0.15);
    }

    .stApp {
        background-color: var(--deep-navy);
        color: white !important;
        font-family: 'Inter', sans-serif;
    }

    /* تصحيح وضوح النصوص البيضاء */
    .stMarkdown, p, span, label {
        color: white !important;
    }

    /* Professional Logo Styling */
    .logo-container { padding: 10px 0; margin-bottom: 25px; }
    .logo-text { font-size: 2.4rem; font-weight: 900; color: white !important; letter-spacing: -1.5px; }
    .logo-lime { color: var(--audit-lime) !important; font-style: italic; }

    /* Tables & Containers */
    div[data-testid="stDataFrame"] {
        background: var(--glass);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 8px;
    }
    
    .stExpander {
        background: var(--glass) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 10px !important;
    }

    /* Professional Buttons */
    .stButton > button {
        background: var(--audit-lime) !important;
        color: var(--deep-navy) !important;
        border: none !important;
        padding: 10px 24px !important;
        border-radius: 8px !important;
        font-weight: 900 !important;
        transition: all 0.3s ease !important;
        width: 100%;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(190, 242, 100, 0.3);
    }

    /* Sidebar Clean-up */
    [data-testid="stSidebar"] {
        background-color: rgba(0, 0, 0, 0.2) !important;
        border-right: 1px solid var(--border-color);
    }

    /* Typography */
    h1, h2, h3 { font-weight: 900 !important; letter-spacing: -0.5px; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2️⃣ CORE FUNCTIONS (AI & BLOCKCHAIN) ---

@st.cache_resource
def load_audit_model():
    try:
        return tf.keras.models.load_model('invoice_audit_model.h5')
    except Exception as e:
        st.error(f"Erreur de chargement du modèle AI: {e}")
        return None

model = load_audit_model()

def ai_cnn_analysis(uploaded_file):
    if model is None: return 0.5, "Error"
    image = Image.open(uploaded_file).convert('RGB')
    img = image.resize((224, 224))
    img_array = np.array(img).astype('float32') / 255.0 
    img_array = np.expand_dims(img_array, axis=0)
    prediction = model.predict(img_array, verbose=0)
    risk_score = float(prediction[0][0])
    label = "Low Risk" if risk_score > 0.99 else "High Risk"
    return risk_score, label

def send_to_blockchain(inv_id, amount, score, status="En Attente", img_b64=""):
    url = "http://localhost:5000/api/v1/namespaces/default/messages/broadcast"
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    payload = {
        "header": {"tag": "AUDIT_DATA"},
        "data": [{"value": {
            "invoice_id": inv_id, 
            "amount": amount, 
            "risk": round(score, 4),
            "status": status,
            "image": img_b64,
            "timestamp": now
        }}]
    }
    try:
        res = requests.post(url, json=payload, timeout=5)
        return res.status_code == 202
    except: return False

@st.cache_data(ttl=5)
def get_blockchain_data():
    url = "http://localhost:5000/api/v1/namespaces/default/messages?tag=AUDIT_DATA&limit=50"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            messages = response.json()
            rows = []
            for msg in messages:
                data_id = msg['data'][0]['id']
                data_url = f"http://localhost:5000/api/v1/namespaces/default/data/{data_id}"
                val = requests.get(data_url).json()['value']
                rows.append(val)
            return pd.DataFrame(rows)
    except: return pd.DataFrame()

# --- 3️⃣ SIDEBAR NAVIGATION ---

with st.sidebar:
    st.markdown('<div class="logo-container"><span class="logo-text">Audit<span class="logo-lime">Chain</span></span></div>', unsafe_allow_html=True)
    role = st.radio("Access Level:", ["COMPTABLE", "AUDITEUR"])
    st.write("---")
    if st.button("Refresh Network"):
        st.cache_data.clear()
        st.rerun()

# --- 4️⃣ DASHBOARD LOGIC ---

df = get_blockchain_data()

if role == "COMPTABLE":
    st.markdown('## <span style="color:var(--audit-lime)">Internal</span> Registry', unsafe_allow_html=True)
    col_input, col_table = st.columns([1, 1.8])

    with col_input:
        st.markdown("### Certification")
        with st.container():
            id_f = st.text_input("Invoice ID", placeholder="Ex: F-2026-X")
            mnt = st.number_input("Amount (MAD)", min_value=0.0, step=100.0)
            file = st.file_uploader("Document Scan", type=['png', 'jpg', 'jpeg'])
            
            if st.button("SEAL ON BLOCKCHAIN") and id_f and file:
                with st.spinner('AI Verification...'):
                    score, label = ai_cnn_analysis(file)
                    buffered = BytesIO()
                    Image.open(file).save(buffered, format="PNG")
                    img_str = base64.b64encode(buffered.getvalue()).decode()
                    
                    if send_to_blockchain(id_f, mnt, score, "En Attente", img_str):
                        st.success(f"Verified: {label}")
                        st.cache_data.clear()
                        st.rerun()

    with col_table:
        st.markdown("### Network History")
        if not df.empty:
            clean_df = df[['invoice_id', 'amount', 'risk', 'status', 'timestamp']].copy()
            st.dataframe(
                clean_df.sort_index(ascending=False), 
                use_container_width=True,
                column_config={
                    "risk": st.column_config.ProgressColumn("AI Score", min_value=0, max_value=1),
                    "amount": st.column_config.NumberColumn("Amount", format="%d MAD")
                }
            )

else: # 🔵 AUDITEUR DASHBOARD
    header_col, search_col = st.columns([2, 1])
    with header_col:
        st.markdown('## <span style="color:var(--audit-lime)">Validation</span> Control', unsafe_allow_html=True)
    with search_col:
        query = st.text_input("", placeholder="🔍 Search Invoice ID...")

    tab_pending, tab_history = st.tabs(["📥 Pending Queue", "📜 Audit History"])

    with tab_pending:
        if not df.empty:
            # 1. تصفية البيانات (Filter)
            pending = df[df['status'] == "En Attente"] if 'status' in df.columns else pd.DataFrame()
            
            if query:
                pending = pending[pending['invoice_id'].astype(str).str.contains(query, case=False)]
            
            # 2. التأكد واش كاين نتائج
            if pending.empty:
                st.info("Aucun document correspondant trouvé.")
            else:
                st.markdown(f"**Queue Status:** `{len(pending)} pending documents`")
                
                # --- هنا كيبدا الكود اللي سولتيني عليه ---
                is_searching = len(query) > 0
                
                for index, row in pending.iterrows():
                    # كايتفتح أوطوماتيكيا غير فاش كيكون البحث خدام
                    with st.expander(f"Invoice ID: {row.get('invoice_id')} | Risk: {row.get('risk')}", expanded=is_searching):
                        c_img, c_info = st.columns([1, 1])
                        
                        img_data = row.get('image', "")
                        with c_img:
                            if isinstance(img_data, str) and len(img_data) > 10: 
                                try:
                                    st.image(base64.b64decode(img_data), use_container_width=True)
                                except:
                                    st.error("Format d'image invalide.")
                            else:
                                st.warning("⚠️ Image non disponible.")
                        
                        with c_info:
                            st.markdown(f"**Amount:** `{row.get('amount')} MAD` / **Time:** `{row.get('timestamp')}`")
                            st.markdown(f"**AI Evaluation:** {'⚠️ Critical' if row.get('risk', 0) < 0.95 else '✅ Reliable'}")
                            st.write("---")
                            
                            b1, b2 = st.columns(2)
                            if b1.button("APPROVE", key=f"app_{index}"):
                                send_to_blockchain(row['invoice_id'], row['amount'], row['risk'], "Validée ✅", img_data)
                                st.rerun()
                            if b2.button("REJECT", key=f"rej_{index}"):
                                send_to_blockchain(row['invoice_id'], row['amount'], row['risk'], "Rejetée ❌", img_data)
                                st.rerun()
                # --- نهاية الكود ---

    with tab_history:
        # هنا كيبقى الكود ديال الجدول اللي كيبين التاريخ (History)
        if not df.empty:
            history_df = df[df['status'].str.contains('Validée|Rejetée', na=False)].copy()
            if query:
                history_df = history_df[history_df['invoice_id'].astype(str).str.contains(query, case=False)]
            st.dataframe(history_df[['invoice_id', 'status', 'timestamp', 'amount']].sort_index(ascending=False), 
                         use_container_width=True, hide_index=True)