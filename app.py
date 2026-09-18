import streamlit as st
import requests
import base64
import pandas as pd
from io import BytesIO
from pypdf import PdfReader

st.set_page_config(page_title="PDF Archiv", layout="wide")

TOKEN = st.secrets["GITHUB_TOKEN"]
OWNER = st.secrets["GITHUB_OWNER"]
REPO = st.secrets["GITHUB_REPO"]
BRANCH = st.secrets.get("GITHUB_BRANCH", "main")

HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github+json"
}

@st.cache_data(ttl=600)
def get_pdf_files():
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/git/trees/{BRANCH}?recursive=1"
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    tree = r.json()["tree"]
    return sorted([item["path"] for item in tree if item["path"].lower().endswith(".pdf")])

@st.cache_data(ttl=600)
def download_pdf(path):
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{path}"
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    return base64.b64decode(r.json()["content"])


def pdf_page_count(pdf_bytes):
    try:
        return len(PdfReader(BytesIO(pdf_bytes)).pages)
    except Exception:
        return 0


def pdf_viewer(pdf_bytes):
    data = base64.b64encode(pdf_bytes).decode()
    st.components.v1.html(
        f'<iframe src="data:application/pdf;base64,{data}" width="100%" height="1100"></iframe>',
        height=1100,
    )

st.title("📚 PDF Archiv")

pdf_files = get_pdf_files()

if not pdf_files:
    st.warning("Keine PDFs gefunden")
    st.stop()

@st.cache_data(ttl=600)
def collect_info(files):
    rows = []
    for f in files:
        try:
            rows.append({"Datei": f, "Seiten": pdf_page_count(download_pdf(f))})
        except Exception:
            pass
    return pd.DataFrame(rows)

info = collect_info(pdf_files)

search = st.sidebar.text_input("PDF suchen")
visible = [f for f in pdf_files if search.lower() in f.lower()] if search else pdf_files
selected = st.sidebar.selectbox("PDF auswählen", visible)

st.sidebar.metric("PDFs", len(pdf_files))
st.sidebar.metric("Gesamtseiten", int(info["Seiten"].sum()) if len(info) else 0)

with st.expander("Übersicht aller PDFs"):
    st.dataframe(info, use_container_width=True)

st.subheader(selected)
pdf_viewer(download_pdf(selected))
