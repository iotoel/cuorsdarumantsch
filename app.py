import streamlit as st
import requests
import base64
import pandas as pd

from io import BytesIO
from pypdf import PdfReader
from streamlit_pdf_viewer import pdf_viewer


# --------------------------------------------------
# Konfiguration
# --------------------------------------------------

st.set_page_config(
    page_title="PDF Archiv",
    layout="wide"
)

TOKEN = st.secrets["GITHUB_TOKEN"]
OWNER = st.secrets["GITHUB_OWNER"]
REPO = st.secrets["GITHUB_REPO"]
BRANCH = st.secrets.get("GITHUB_BRANCH", "main")

HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github+json"
}


# --------------------------------------------------
# GitHub
# --------------------------------------------------

@st.cache_data(ttl=600)
def get_pdf_files():

    url = (
        f"https://api.github.com/repos/"
        f"{OWNER}/{REPO}/git/trees/{BRANCH}"
        f"?recursive=1"
    )

    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()

    tree = r.json()["tree"]

    return sorted([
        item["path"]
        for item in tree
        if item["path"].lower().endswith(".pdf")
    ])


@st.cache_data(ttl=600)
def download_pdf(path):

    url = (
        f"https://api.github.com/repos/"
        f"{OWNER}/{REPO}/contents/{path}"
    )

    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()

    data = r.json()

    # GitHub-Rohdownload bevorzugen
    if data.get("download_url"):

        pdf_response = requests.get(
            data["download_url"]
        )

        pdf_response.raise_for_status()

        return pdf_response.content

    # Fallback: Base64-Inhalt
    if data.get("content"):

        return base64.b64decode(
            data["content"]
        )

    return b""


# --------------------------------------------------
# PDF Infos
# --------------------------------------------------

def count_pages(pdf_bytes):

    try:
        reader = PdfReader(
            BytesIO(pdf_bytes)
        )

        return len(reader.pages)

    except Exception:
        return 0


@st.cache_data(ttl=600)
def collect_info(pdf_files):

    rows = []

    for pdf_file in pdf_files:

        try:

            pdf_data = download_pdf(
                pdf_file
            )

            rows.append({
                "Datei": pdf_file,
                "Seiten": count_pages(
                    pdf_data
                ),
                "Bytes": len(pdf_data)
            })

        except Exception:

            rows.append({
                "Datei": pdf_file,
                "Seiten": 0,
                "Bytes": 0
            })

    return pd.DataFrame(rows)


# --------------------------------------------------
# App
# --------------------------------------------------

st.title("📚 PDF Archiv")

try:

    pdf_files = get_pdf_files()

except Exception as ex:

    st.error(
        f"GitHub Fehler: {ex}"
    )

    st.stop()

if not pdf_files:

    st.warning(
        "Keine PDFs gefunden."
    )

    st.stop()

info = collect_info(pdf_files)

search = st.sidebar.text_input(
    "🔎 PDF suchen"
)

if search:

    visible_files = [
        f
        for f in pdf_files
        if search.lower()
        in f.lower()
    ]

else:

    visible_files = pdf_files

selected = st.sidebar.selectbox(
    "PDF auswählen",
    visible_files
)

st.sidebar.metric(
    "PDFs",
    len(pdf_files)
)

st.sidebar.metric(
    "Gesamtseiten",
    int(
        info["Seiten"].sum()
    )
)

with st.expander(
    "📋 Übersicht aller PDFs"
):
    st.dataframe(
        info,
        use_container_width=True
    )

# --------------------------------------------------
# PDF laden
# --------------------------------------------------

pdf_data = download_pdf(
    selected
)

file_size = len(
    pdf_data
)

page_count = count_pages(
    pdf_data
)

st.subheader(selected)

col1, col2 = st.columns(2)

with col1:
    st.metric(
        "Dateigrösse (Bytes)",
        file_size
    )

with col2:
    st.metric(
        "Seiten",
        page_count
    )

# --------------------------------------------------
# Fehlerfall
# --------------------------------------------------

if file_size == 0:

    st.error(
        "GitHub liefert 0 Bytes zurück."
    )

    st.stop()

# --------------------------------------------------
# PDF anzeigen
# --------------------------------------------------

pdf_viewer(
    pdf_data,
    width="100%",
    height=1400,
    render_text=True
)