[README.md](https://github.com/user-attachments/files/29632179/README.md)
# 🎙️ Text Reader & Transcriber

A Streamlit app that accepts text from multiple sources and reads it aloud — works on desktop and mobile.

## What It Does
| Input | How |
|-------|-----|
| **Paste text** | Copy from Google Docs, Word, email, websites |
| **Word doc (.docx)** | Upload file → extract all text |
| **PDF** | Upload file → extract all text |
| **Image / Photo** | Upload .jpg/.png → OCR reads the text |

**Output:** Displays the text on screen and reads it aloud via your browser's built-in voice.

---

## One-Time Setup

### Step 1 — Install Python libraries
Open a terminal in this folder and run:
```
pip install -r requirements.txt
```

### Step 2 — Install Tesseract OCR (for image reading only)
1. Download the installer from:  
   **https://github.com/UB-Mannheim/tesseract/wiki**
2. Run the installer — keep the default path:  
   `C:\Program Files\Tesseract-OCR\`
3. That's it — the app finds it automatically.

> ⚠️ If you skip Step 2, everything still works except the Image tab.

---

## Running the App

### On your computer (desktop)
```
streamlit run app.py
```
Opens automatically at **http://localhost:8501**

### On your phone (same Wi-Fi network)
```
streamlit run app.py --server.address 0.0.0.0
```
Then on your phone go to:  
**http://YOUR-PC-IP:8501**  
(Find your PC's IP by running `ipconfig` in a terminal — look for `IPv4 Address`)

### On your phone anywhere (free public URL)
Deploy for free on Streamlit Community Cloud:
1. Push this folder to a GitHub repo
2. Go to https://streamlit.io/cloud and sign in with GitHub
3. Click "New app" → select your repo → `app.py` → Deploy
4. You get a permanent `https://your-app.streamlit.app` URL that works from any device

---

## Tips
- **Read Aloud** uses your browser's built-in voice — no internet or API key needed
- On **iPhone/iPad**, make sure the side switch is not on silent
- You can **edit the text** in the output box before reading — useful for fixing OCR errors
- Use the **speed slider** in the sidebar to slow down or speed up the reading
- The **OCR language** dropdown (sidebar) lets you switch between English, Spanish, French, etc.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "Tesseract not found" | Install Tesseract from the link above |
| PDF shows no text | The PDF is image-based (scanned) — save it as a JPG and use the Image tab |
| Read Aloud doesn't work on mobile | Make sure you're using a modern browser (Chrome, Safari, Edge). On iOS, unmute the phone. |
| Voice sounds robotic | Normal — uses your device's built-in TTS. You can change the voice in your OS settings. |
