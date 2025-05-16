# 🎧 **WHYSPR** Transcriptor de Audio con Whisper API

Este proyecto incluye dos interfaces gráficas para una misma aplicación: una basada en **Gradio** y otra en **Streamlit**. Ambas permiten a los usuarios cargar archivos de audio y obtener su transcripción en texto utilizando la API de Whisper de OpenAI. También se pueden descargar los resultados en formato **PDF** y **TXT**.

---

## 🚀 Funcionalidades

- ✅ Carga de archivos de audio en formatos comunes (`mp3`, `wav`, `mp4`, `m4a`, etc.)
- ✅ Transcripción automática usando el modelo `whisper-1` de OpenAI
- ✅ División automática de archivos que superan los **25 MB**
- ✅ Generación y descarga de la transcripción en:
  - 📄 Formato PDF
  - 📝 Formato TXT
- ✅ Cálculo automático de:
  - Duración del audio
  - Costo estimado de transcripción a día del primer commit, 15 de mayo de 2025 (0.006 USD/minuto)
  - Número de palabras y velocidad de habla
- ✅ Interfaz con progreso (en ambos frameworks)
- ✅ Botón de cancelación (solo en Gradio)
- ✅ Estadísticas y visualización lateral (solo en Streamlit)

---

## 🧠 Requisitos

- Python 3.9 o superior
- API Key de OpenAI (variable de entorno `OPENAI_API_KEY`)

---

## 📦 Instalación

Clona el repositorio y crea un entorno virtual:

```bash
git clone https://github.com/b0rjen/whyspr.git
cd whyspr
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

> Asegúrate de tener tu clave API de OpenAI configurada:
```bash
export OPENAI_API_KEY=tu_clave_api
```

---

## 🖥️ Ejecución

### 🔹 Opción 1: Gradio

```bash
python app_gradio.py
```

Se abrirá automáticamente una interfaz web local.

### 🔸 Opción 2: Streamlit

```bash
streamlit run app_streamlit.py
```

También abrirá una interfaz web local.

---

## 📁 Estructura del Proyecto

```
.
├── app_gradio.py              # Interfaz con Gradio
├── app_streamlit.py           # Interfaz con Streamlit
├── README.md                  # Este archivo
├── requirements.txt           # Requisitos de Python
└── data/                      # Carpeta de ejemplo con datos de prueba
    ├── quevedo_el_bueno.mp3  # Archivo de audio de muestra
    └── transcription.txt     # Transcripción del archivo de audio
```

---

## 📚 Licencia

MIT. Puedes usar, modificar y distribuir libremente este código.

---

## 🙌 Créditos

Creado por [b0rjen](https://borjen.dev)  
Basado en la API de transcripción de [OpenAI Whisper](https://platform.openai.com/docs/guides/speech-to-text)
