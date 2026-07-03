import streamlit as st
import asyncio
import io
import os

# ── Trust Windows certificate store (corporate SSL proxy fix) ─────────────────
try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Text Reader & Transcriber",
    page_icon="🎙️",
    layout="centered",
    initial_sidebar_state="auto",
)

# ── Tesseract path detection (Windows) ────────────────────────────────────────
TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\Users\{}\AppData\Local\Programs\Tesseract-OCR\tesseract.exe".format(
        os.environ.get("USERNAME", "")
    ),
]

def find_tesseract():
    for path in TESSERACT_PATHS:
        if os.path.isfile(path):
            return path
    return None


# ── Extraction helpers ─────────────────────────────────────────────────────────

def extract_from_docx(file_bytes: bytes) -> str:
    """
    Extract all text from a .docx — paragraphs, tables, headers, footers,
    and text boxes. Uses a full XML w:t scan so nothing is missed.
    """
    from docx import Document as DocxDocument

    doc = DocxDocument(io.BytesIO(file_bytes))
    parts = []

    # Helper: collect every text run inside an XML element in reading order
    def collect_runs(elem):
        return "".join(
            t.text for t in elem.iter()
            if t.tag.endswith("}t") and t.text
        )

    # Walk direct children of <w:body> to preserve paragraph/table order
    for child in doc.element.body:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag

        if tag == "p":
            line = collect_runs(child).strip()
            if line:
                parts.append(line)

        elif tag == "tbl":
            # Iterate rows directly; skip nested tables repeating cells
            seen_rows = set()
            for row in child.iter():
                if not row.tag.endswith("}tr"):
                    continue
                row_id = id(row)
                if row_id in seen_rows:
                    continue
                seen_rows.add(row_id)
                cells = []
                for cell in row:
                    if not cell.tag.endswith("}tc"):
                        continue
                    cell_text = collect_runs(cell).strip()
                    if cell_text:
                        cells.append(cell_text)
                if cells:
                    parts.append(" | ".join(cells))

    # Headers and footers
    for section in doc.sections:
        for hf in (section.header, section.footer):
            try:
                for para in hf.paragraphs:
                    if para.text.strip():
                        parts.append(para.text.strip())
            except Exception:
                pass

    result = "\n".join(parts)

    # Nuclear fallback — scrape every single w:t node in the whole file
    # This catches text boxes, SmartArt, callouts, etc.
    if not result.strip():
        all_runs = [
            t.text for t in doc.element.body.iter()
            if t.tag.endswith("}t") and t.text and t.text.strip()
        ]
        result = " ".join(all_runs)

    return result


def extract_from_pdf(file_bytes: bytes) -> str:
    import pdfplumber
    parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                parts.append(text)
    return "\n\n".join(parts)


def extract_from_image(file_bytes: bytes, lang: str = "eng") -> str:
    import pytesseract
    from PIL import Image
    tess = find_tesseract()
    if tess:
        pytesseract.pytesseract.tesseract_cmd = tess
    else:
        st.error(
            "⚠️ Tesseract OCR not found. "
            "Install from https://github.com/UB-Mannheim/tesseract/wiki then restart."
        )
        return ""
    return pytesseract.image_to_string(Image.open(io.BytesIO(file_bytes)), lang=lang)


# ── Edge TTS ───────────────────────────────────────────────────────────────────

VOICES = {
    "🇺🇸 Aria — Female, warm & friendly":        "en-US-AriaNeural",
    "🇺🇸 Jenny — Female, conversational":         "en-US-JennyNeural",
    "🇺🇸 Michelle — Female, professional":        "en-US-MichelleNeural",
    "🇺🇸 Guy — Male, casual":                     "en-US-GuyNeural",
    "🇺🇸 Davis — Male, energetic":                "en-US-DavisNeural",
    "🇺🇸 Tony — Male, calm":                      "en-US-TonyNeural",
    "🇬🇧 Libby — Female, British":                "en-GB-LibbyNeural",
    "🇬🇧 Sonia — Female, British professional":   "en-GB-SoniaNeural",
    "🇬🇧 Ryan — Male, British":                   "en-GB-RyanNeural",
    "🇦🇺 Natasha — Female, Australian":           "en-AU-NatashaNeural",
    "🇦🇺 William — Male, Australian":             "en-AU-WilliamNeural",
}

def _fmt_rate(val: int) -> str:
    return f"+{val}%" if val >= 0 else f"{val}%"

def _fmt_pitch(val: int) -> str:
    return f"+{val}Hz" if val >= 0 else f"{val}Hz"

async def _tts(text: str, voice: str, rate: str, pitch: str) -> bytes:
    import edge_tts
    kwargs = {"rate": rate}
    if pitch not in ("+0Hz", "-0Hz", "0Hz"):
        kwargs["pitch"] = pitch
    comm = edge_tts.Communicate(text, voice, **kwargs)
    buf = io.BytesIO()
    async for chunk in comm.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    return buf.getvalue()

def generate_audio(text: str, voice: str, rate_pct: int = 0, pitch_pct: int = 0) -> bytes:
    return asyncio.run(_tts(text, voice, _fmt_rate(rate_pct), _fmt_pitch(pitch_pct)))


# ══════════════════════════════════════════════════════════════════════════════
# UI
# ══════════════════════════════════════════════════════════════════════════════

st.title("🎙️ Text Reader & Transcriber")
st.caption("Paste text, upload a Word doc, PDF, or image — extract the text, then have it read aloud.")

# ── Sidebar — minor settings only ─────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Other Settings")
    ocr_lang = st.selectbox(
        "OCR language (images only)",
        options=["eng", "spa", "fra", "deu", "ita", "por", "chi_sim", "jpn"],
        format_func=lambda x: {
            "eng": "English", "spa": "Spanish", "fra": "French",
            "deu": "German",  "ita": "Italian", "por": "Portuguese",
            "chi_sim": "Chinese (Simplified)", "jpn": "Japanese",
        }.get(x, x),
    )
    st.divider()
    st.caption(
        "Voices: Microsoft Edge Neural TTS (free, requires internet)\n\n"
        "OCR: Tesseract (local, no internet needed)"
    )


# ── Step 1 — Input ─────────────────────────────────────────────────────────────
st.subheader("Step 1 — Get your text")

tab_paste, tab_word, tab_pdf, tab_image = st.tabs(
    ["📋 Paste Text", "📄 Word Doc", "📑 PDF", "🖼️ Image / Photo"]
)

with tab_paste:
    pasted = st.text_area(
        "Copy and paste any text here",
        height=220,
        placeholder="Paste from Google Docs, Word, email, a website…",
    )
    if st.button("✅ Use This Text", key="use_paste", type="primary"):
        if pasted.strip():
            st.session_state["text"] = pasted.strip()
            st.session_state.pop("audio", None)
            st.success(f"Loaded {len(pasted.split()):,} words.")
        else:
            st.warning("Text box is empty — paste something first.")

with tab_word:
    st.caption("Upload a **.docx** file (Word 2007 or newer). Old **.doc** files are not supported — open in Word and Save As .docx first.")
    docx_file = st.file_uploader("Choose a .docx file", type=["docx"], key="docx_up")

    if docx_file:
        size_kb = len(docx_file.getvalue()) / 1024
        st.caption(f"File: **{docx_file.name}** · {size_kb:,.0f} KB")

        if st.button("📄 Extract Text from Word Doc", key="ext_docx", type="primary"):
            with st.spinner("Reading document…"):
                try:
                    raw_bytes = docx_file.getvalue()   # getvalue() is safe to call multiple times
                    result = extract_from_docx(raw_bytes)
                    if result.strip():
                        st.session_state["text"] = result.strip()
                        st.session_state.pop("audio", None)
                        st.success(f"✅ Extracted {len(result.split()):,} words from {docx_file.name}.")
                    else:
                        st.warning(
                            "The file opened successfully but no text was found.\n\n"
                            "Possible reasons:\n"
                            "- The document is password-protected\n"
                            "- All text is inside images embedded in the doc (try the Image tab)\n"
                            "- The file is corrupted"
                        )
                except Exception as e:
                    import traceback
                    st.error(
                        f"**Failed to read the file.**\n\n"
                        f"Error: `{e}`\n\n"
                        f"```\n{traceback.format_exc()}\n```"
                    )

with tab_pdf:
    pdf_file = st.file_uploader("Choose a PDF file", type=["pdf"], key="pdf_up")
    if pdf_file:
        if st.button("📑 Extract Text from PDF", key="ext_pdf", type="primary"):
            with st.spinner("Reading PDF…"):
                try:
                    result = extract_from_pdf(pdf_file.getvalue())
                    if result.strip():
                        st.session_state["text"] = result.strip()
                        st.session_state.pop("audio", None)
                        st.success(f"✅ Extracted {len(result.split()):,} words.")
                    else:
                        st.warning(
                            "No text found. This PDF is probably scanned (image-based). "
                            "Export each page as a JPG and use the Image tab instead."
                        )
                except Exception as e:
                    st.error(f"Could not read PDF: {e}")

with tab_image:
    img_file = st.file_uploader(
        "Choose an image (.jpg, .png, .bmp…)",
        type=["png", "jpg", "jpeg", "bmp", "tiff"],
        key="img_up",
    )
    if img_file:
        st.image(img_file, use_column_width=True)
        if st.button("🖼️ Extract Text via OCR", key="ext_img", type="primary"):
            with st.spinner("Running OCR…"):
                try:
                    result = extract_from_image(img_file.getvalue(), lang=ocr_lang)
                    if result.strip():
                        st.session_state["text"] = result.strip()
                        st.session_state.pop("audio", None)
                        st.success(f"✅ Detected {len(result.split()):,} words.")
                    else:
                        st.warning("No text detected. Make sure the image is clear and not rotated.")
                except Exception as e:
                    st.error(f"OCR failed: {e}")


# ── Step 2 — Review & edit extracted text ─────────────────────────────────────
st.divider()
st.subheader("Step 2 — Review the extracted text")

current_text = st.session_state.get("text", "")

if current_text:
    edited_text = st.text_area(
        "Extracted text (you can edit it before reading aloud)",
        value=current_text,
        height=280,
        label_visibility="collapsed",
    )
    word_count = len(edited_text.split())
    col_a, col_b = st.columns([5, 1])
    with col_a:
        st.caption(f"{word_count:,} words · {len(edited_text):,} characters")
    with col_b:
        if st.button("🗑️ Clear"):
            st.session_state.pop("text", None)
            st.session_state.pop("audio", None)
            st.rerun()

    # ── Step 3 — Voice settings + generate ────────────────────────────────────
    st.divider()
    st.subheader("Step 3 — Choose a voice & read aloud")

    # Voice picker — in the MAIN page so it's always visible
    voice_label = st.selectbox(
        "🎙️ Voice",
        options=list(VOICES.keys()),
        index=0,
        help="All voices are free Microsoft Neural TTS voices.",
    )
    selected_voice = VOICES[voice_label]

    col1, col2 = st.columns(2)
    with col1:
        rate_pct = st.slider(
            "Reading speed",
            min_value=-50, max_value=100, value=0, step=5,
            format="%d%%",
            help="0% = normal. Negative = slower, positive = faster.",
        )
    with col2:
        pitch_pct = st.slider(
            "Pitch",
            min_value=-50, max_value=50, value=0, step=5,
            format="%d%%",
            help="0% = natural. Negative = deeper voice, positive = higher.",
        )

    if word_count > 2000:
        st.warning(
            f"⏳ {word_count:,} words — audio generation may take 30–60 seconds. "
            "You can trim the text above and generate in sections if needed."
        )

    if st.button("🔊 Generate Audio", type="primary", key="gen_audio"):
        with st.spinner(f"Generating audio with {voice_label.split('—')[0].strip()}…"):
            try:
                audio_bytes = generate_audio(
                    edited_text,
                    voice=selected_voice,
                    rate_pct=rate_pct,
                    pitch_pct=pitch_pct,
                )
                st.session_state["audio"] = audio_bytes
                st.success("✅ Audio ready — press ▶ below to play.")
            except Exception as e:
                import traceback
                st.error(
                    f"Audio generation failed: `{e}`\n\n"
                    f"```\n{traceback.format_exc()}\n```"
                )

    if "audio" in st.session_state:
        st.audio(st.session_state["audio"], format="audio/mp3")
        st.download_button(
            "⬇️ Download MP3",
            data=st.session_state["audio"],
            file_name="reading.mp3",
            mime="audio/mpeg",
        )

else:
    st.info("👆 Use one of the tabs above to load your text, then come back here to read it aloud.")
