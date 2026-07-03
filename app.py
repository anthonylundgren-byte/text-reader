import streamlit as st
import io
import os

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Text Reader & Transcriber",
    page_icon="🎙️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Tesseract path detection (Windows) ─────────────────────────────────────────
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

# ── Extraction helpers ──────────────────────────────────────────────────────────

def extract_from_docx(file_bytes: bytes) -> str:
    """Extract all paragraph text from a .docx file."""
    import docx
    doc = docx.Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def extract_from_pdf(file_bytes: bytes) -> str:
    """Extract text from every page of a PDF."""
    import pdfplumber
    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n\n".join(text_parts)


def extract_from_image(file_bytes: bytes, lang: str = "eng") -> str:
    """Run Tesseract OCR on an image and return the recognised text."""
    import pytesseract
    from PIL import Image

    tess_path = find_tesseract()
    if tess_path:
        pytesseract.pytesseract.tesseract_cmd = tess_path
    else:
        st.error(
            "⚠️ Tesseract OCR not found. "
            "Please install it from https://github.com/UB-Mannheim/tesseract/wiki "
            "and restart the app."
        )
        return ""

    image = Image.open(io.BytesIO(file_bytes))
    return pytesseract.image_to_string(image, lang=lang)


# ── Text-to-speech component ────────────────────────────────────────────────────

def tts_component(text: str, rate: float = 1.0):
    """
    Inject a Web Speech API player into the page.
    Works on desktop browsers and mobile (iOS Safari / Android Chrome).
    No API key or internet required.
    """
    # Escape backticks and backslashes so the JS template literal is safe
    safe_text = text.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")

    html = f"""
    <div id="tts-container" style="display:flex; gap:8px; flex-wrap:wrap; margin-top:8px;">
      <button id="btn-play"  onclick="startReading()"
        style="padding:10px 20px; font-size:16px; border-radius:8px;
               background:#4CAF50; color:white; border:none; cursor:pointer;">
        ▶ Read Aloud
      </button>
      <button id="btn-pause" onclick="togglePause()"
        style="padding:10px 20px; font-size:16px; border-radius:8px;
               background:#FF9800; color:white; border:none; cursor:pointer;">
        ⏸ Pause
      </button>
      <button id="btn-stop"  onclick="stopReading()"
        style="padding:10px 20px; font-size:16px; border-radius:8px;
               background:#f44336; color:white; border:none; cursor:pointer;">
        ⏹ Stop
      </button>
    </div>

    <div id="tts-status" style="margin-top:6px; font-size:13px; color:#888;"></div>

    <script>
      var synth   = window.speechSynthesis;
      var utterance = null;
      var paused  = false;

      function startReading() {{
        if (synth.speaking) synth.cancel();
        var text = `{safe_text}`;
        utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = {rate};
        utterance.onstart = function()  {{ setStatus("🔊 Reading…"); }};
        utterance.onend   = function()  {{ setStatus("✅ Done");     }};
        utterance.onerror = function(e) {{ setStatus("❌ Error: " + e.error); }};
        synth.speak(utterance);
        paused = false;
        setStatus("🔊 Starting…");
      }}

      function togglePause() {{
        if (synth.speaking && !paused) {{
          synth.pause();
          paused = true;
          setStatus("⏸ Paused");
        }} else if (paused) {{
          synth.resume();
          paused = false;
          setStatus("🔊 Resumed…");
        }}
      }}

      function stopReading() {{
        synth.cancel();
        paused = false;
        setStatus("⏹ Stopped");
      }}

      function setStatus(msg) {{
        document.getElementById("tts-status").textContent = msg;
      }}
    </script>
    """
    st.components.v1.html(html, height=120)


# ── Sidebar ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🎙️ Text Reader")
    st.markdown(
        """
        **How to use:**
        1. Pick an input method (tabs below)
        2. Paste text or upload a file
        3. Click **Extract Text**
        4. Adjust speed, then click **▶ Read Aloud**
        """
    )
    st.divider()
    st.subheader("⚙️ Settings")
    speech_rate = st.slider("Reading speed", min_value=0.5, max_value=2.0, value=1.0, step=0.1)
    ocr_lang    = st.selectbox(
        "OCR language (images)",
        options=["eng", "spa", "fra", "deu", "ita", "por", "chi_sim", "jpn"],
        format_func=lambda x: {
            "eng": "English", "spa": "Spanish", "fra": "French",
            "deu": "German",  "ita": "Italian", "por": "Portuguese",
            "chi_sim": "Chinese (Simplified)", "jpn": "Japanese",
        }.get(x, x),
    )
    st.divider()
    st.caption("Uses your browser's built-in text-to-speech — works on desktop & mobile.")


# ── Main area ───────────────────────────────────────────────────────────────────
st.title("🎙️ Text Reader & Transcriber")
st.caption("Paste text, upload a Word doc, PDF, or image — then have it read back to you.")

# ── Input tabs ──────────────────────────────────────────────────────────────────
tab_paste, tab_word, tab_pdf, tab_image = st.tabs(
    ["📋 Paste Text", "📄 Word Doc", "📑 PDF", "🖼️ Image / Photo"]
)

extracted_text = ""

with tab_paste:
    st.subheader("Paste your text")
    st.caption("Copy from Google Docs, Word, email, websites, or anywhere else.")
    pasted = st.text_area(
        "Paste text here",
        height=250,
        placeholder="Paste any text here…",
        label_visibility="collapsed",
    )
    if st.button("Use This Text", key="use_paste", type="primary"):
        if pasted.strip():
            st.session_state["text"] = pasted.strip()
            st.success(f"✅ {len(pasted.split())} words loaded.")
        else:
            st.warning("Nothing to use — text area is empty.")

with tab_word:
    st.subheader("Upload a Word document (.docx)")
    docx_file = st.file_uploader("Choose a .docx file", type=["docx"], key="docx_up")
    if docx_file and st.button("Extract Text from Word Doc", key="ext_docx", type="primary"):
        with st.spinner("Reading document…"):
            try:
                result = extract_from_docx(docx_file.read())
                st.session_state["text"] = result
                st.success(f"✅ {len(result.split())} words extracted.")
            except Exception as e:
                st.error(f"Could not read file: {e}")

with tab_pdf:
    st.subheader("Upload a PDF")
    pdf_file = st.file_uploader("Choose a PDF file", type=["pdf"], key="pdf_up")
    if pdf_file and st.button("Extract Text from PDF", key="ext_pdf", type="primary"):
        with st.spinner("Reading PDF…"):
            try:
                result = extract_from_pdf(pdf_file.read())
                if not result.strip():
                    st.warning(
                        "No text found — this PDF may be image-based (scanned). "
                        "Try the Image tab instead."
                    )
                else:
                    st.session_state["text"] = result
                    st.success(f"✅ {len(result.split())} words extracted.")
            except Exception as e:
                st.error(f"Could not read PDF: {e}")

with tab_image:
    st.subheader("Upload an image or photo")
    st.caption("Works with photos of documents, screenshots, printed text, signs, etc.")
    img_file = st.file_uploader(
        "Choose an image", type=["png", "jpg", "jpeg", "bmp", "tiff"], key="img_up"
    )
    if img_file:
        st.image(img_file, caption="Uploaded image", use_column_width=True)
    if img_file and st.button("Extract Text via OCR", key="ext_img", type="primary"):
        with st.spinner("Running OCR — this may take a few seconds…"):
            try:
                result = extract_from_image(img_file.read(), lang=ocr_lang)
                if not result.strip():
                    st.warning("No text detected in this image.")
                else:
                    st.session_state["text"] = result
                    st.success(f"✅ {len(result.split())} words detected.")
            except Exception as e:
                st.error(f"OCR failed: {e}")


# ── Output area ─────────────────────────────────────────────────────────────────
st.divider()
st.subheader("📝 Extracted / Transcribed Text")

current_text = st.session_state.get("text", "")

if current_text:
    # Editable display — user can tweak before reading aloud
    edited_text = st.text_area(
        "Text (editable — make changes before reading)",
        value=current_text,
        height=300,
        label_visibility="collapsed",
        key="text_display",
    )

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        word_count = len(edited_text.split())
        char_count = len(edited_text)
        st.caption(f"**{word_count:,} words · {char_count:,} characters**")
    with col3:
        if st.button("🗑️ Clear", key="clear_text"):
            st.session_state.pop("text", None)
            st.rerun()

    # Copy-to-clipboard button
    copy_js = f"""
    <script>
      function copyText() {{
        navigator.clipboard.writeText(`{edited_text.replace("`", "\\`").replace("$", "\\$")}`)
          .then(() => document.getElementById('copy-msg').textContent = '✅ Copied!')
          .catch(() => document.getElementById('copy-msg').textContent = '❌ Copy failed');
        setTimeout(() => document.getElementById('copy-msg').textContent = '', 2000);
      }}
    </script>
    <button onclick="copyText()"
      style="padding:8px 16px; font-size:14px; border-radius:6px;
             background:#1E88E5; color:white; border:none; cursor:pointer; margin-right:8px;">
      📋 Copy to Clipboard
    </button>
    <span id="copy-msg" style="font-size:13px; color:green;"></span>
    """
    st.components.v1.html(copy_js, height=50)

    # ── Text-to-speech ──────────────────────────────────────────────────────────
    st.subheader("🔊 Read Aloud")
    tts_component(edited_text, rate=speech_rate)

    st.info(
        "💡 **Mobile tip:** The Read Aloud button uses your device's built-in voice. "
        "On iOS you may need to unmute your phone's side switch."
    )

else:
    st.info("👆 Choose an input method above, then click the Extract button to get started.")
