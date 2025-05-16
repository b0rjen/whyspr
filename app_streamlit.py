import streamlit as st
from openai import OpenAI
import tempfile
import os
from pydub import AudioSegment
import shutil
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

# Configura el cliente de OpenAI
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

st.title("🎧 Transcripción con Whisper API")

# Inicializar session state
if 'transcription' not in st.session_state:
    st.session_state.transcription = None
if 'processed_file' not in st.session_state:
    st.session_state.processed_file = None
if 'audio_duration' not in st.session_state:
    st.session_state.audio_duration = 0
if 'processing_cost' not in st.session_state:
    st.session_state.processing_cost = 0

audio_file = st.file_uploader("Sube tu archivo de audio", type=["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"])

def create_temp_folder():
    temp_dir = os.path.join(tempfile.gettempdir(), "audio_chunks")
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)
    return temp_dir

def split_audio(file_path, max_size_mb=24):
    audio = AudioSegment.from_file(file_path)
    max_size_bytes = max_size_mb * 1024 * 1024
    duration_ms = len(audio)
    bytes_per_ms = len(audio.raw_data) / duration_ms
    max_duration_ms = (max_size_bytes / bytes_per_ms) * 0.95  # Margen de seguridad
    chunks = []
    temp_dir = create_temp_folder()
    for i in range(0, duration_ms, int(max_duration_ms)):
        chunk = audio[i:i + int(max_duration_ms)]
        chunk_path = os.path.join(temp_dir, f"chunk_{i//1000}.mp4")
        chunk.export(chunk_path, format="mp4", codec="aac")
        chunks.append(chunk_path)
    return chunks, temp_dir

def generate_pdf(text, filename="transcription.pdf"):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setFont("Helvetica", 12)
    text_lines = text.split("\n")
    y = 750
    for line in text_lines:
        if y < 50:
            c.showPage()
            y = 750
        # Manejar líneas muy largas
        words = line.split()
        current_line = ""
        for word in words:
            test_line = current_line + " " + word if current_line else word
            if c.stringWidth(test_line, "Helvetica", 12) > 500:  # Ancho máximo
                if current_line:
                    c.drawString(50, y, current_line)
                    y -= 15
                current_line = word
            else:
                current_line = test_line
        if current_line:
            c.drawString(50, y, current_line)
            y -= 15
    c.save()
    buffer.seek(0)
    return buffer

def generate_txt(text, filename="transcription.txt"):
    buffer = io.BytesIO()
    buffer.write(text.encode('utf-8'))
    buffer.seek(0)
    return buffer

def get_audio_duration(file_path):
    """Obtiene la duración del audio en segundos"""
    audio = AudioSegment.from_file(file_path)
    return len(audio) / 1000.0  # Convertir de milisegundos a segundos

def calculate_whisper_cost(duration_seconds):
    """Calcula el costo de usar Whisper API basado en la duración"""
    # Precio de Whisper: $0.006 por minuto
    cost_per_minute = 0.006
    duration_minutes = duration_seconds / 60
    return duration_minutes * cost_per_minute

# Botón para procesar el audio
if audio_file is not None:
    # Verificar si el archivo ha cambiado
    current_file_id = f"{audio_file.name}_{audio_file.size}"
    
    # Si es un archivo nuevo o no hay transcripción guardada
    if st.session_state.processed_file != current_file_id or st.session_state.transcription is None:
        
        if st.button("🎙️ Iniciar Transcripción"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                tmp_file.write(audio_file.read())
                tmp_file_path = tmp_file.name

            with st.spinner("Procesando audio..."):
                file_size = os.path.getsize(tmp_file_path)
                max_size = 25 * 1024 * 1024  # 25 MB
                full_transcription = ""
                temp_dir = None
                
                # Calcular duración y costo
                audio_duration = get_audio_duration(tmp_file_path)
                estimated_cost = calculate_whisper_cost(audio_duration)
                
                st.info(f"⏱️ Duración del audio: {audio_duration/60:.1f} minutos")
                st.info(f"💰 Costo estimado: ${estimated_cost:.4f} USD")

                try:
                    if file_size > max_size:
                        st.warning("El archivo excede el límite de 25 MB. Dividiendo en trozos...")
                        chunks, temp_dir = split_audio(tmp_file_path, max_size_mb=24)
                        
                        progress_bar = st.progress(0)
                        for i, chunk_path in enumerate(chunks):
                            with open(chunk_path, "rb") as f:
                                result = client.audio.transcriptions.create(
                                    model="whisper-1",
                                    file=f
                                )
                                full_transcription += result.text + " "
                            progress_bar.progress((i + 1) / len(chunks))
                        progress_bar.empty()
                    else:
                        with open(tmp_file_path, "rb") as f:
                            result = client.audio.transcriptions.create(
                                model="whisper-1",
                                file=f
                            )
                            full_transcription = result.text

                    # Guardar la transcripción en session state
                    st.session_state.transcription = full_transcription
                    st.session_state.processed_file = current_file_id
                    st.session_state.audio_duration = audio_duration
                    st.session_state.processing_cost = estimated_cost
                    st.success("¡Transcripción completada!")
                    st.balloons()
                    
                except Exception as e:
                    st.error(f"Error al transcribir: {e}")
                finally:
                    # Limpieza
                    if temp_dir and os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir)
                    if os.path.exists(tmp_file_path):
                        os.remove(tmp_file_path)

    # Mostrar transcripción guardada (si existe)
    if st.session_state.transcription:
        st.text_area("Texto transcrito:", value=st.session_state.transcription, height=300)
        
        # Opciones de descarga
        col1, col2, col3 = st.columns(3)
        with col1:
            pdf_buffer = generate_pdf(st.session_state.transcription)
            st.download_button(
                label="📄 Descargar PDF",
                data=pdf_buffer,
                file_name="transcription.pdf",
                mime="application/pdf"
            )
        with col2:
            txt_buffer = generate_txt(st.session_state.transcription)
            st.download_button(
                label="📝 Descargar TXT",
                data=txt_buffer,
                file_name="transcription.txt",
                mime="text/plain"
            )
        with col3:
            if st.button("🗑️ Limpiar"):
                st.session_state.transcription = None
                st.session_state.processed_file = None
                st.session_state.audio_duration = 0
                st.session_state.processing_cost = 0
                st.rerun()

# Información útil
with st.sidebar:
    st.markdown("### 📖 Instrucciones")
    st.markdown("""
    1. Sube un archivo de audio
    2. Haz clic en 'Iniciar Transcripción'
    3. Espera a que termine el proceso
    4. Descarga el resultado en PDF o TXT
    
    ### 💡 Tips
    - Para archivos grandes, el proceso puede tardar varios minutos
    - Puedes copiar el texto directamente del cuadro de texto
    - La transcripción se guarda temporalmente hasta que subas otro archivo
    
    ### 💲 Precio de Whisper API
    - $0.006 USD por minuto de audio
    - Se cobra por duración del audio, no por palabras
    """)
    
    if st.session_state.transcription:
        st.markdown("### 📊 Estadísticas")
        word_count = len(st.session_state.transcription.split())
        duration_min = st.session_state.audio_duration / 60
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Palabras", f"{word_count:,}")
            st.metric("Duración", f"{duration_min:.1f} min")
        with col2:
            st.metric("Costo", f"${st.session_state.processing_cost:.4f}")
            st.metric("$/minuto", "$0.006")
        
        # Cálculo adicional: palabras por minuto (velocidad de habla)
        if duration_min > 0:
            words_per_minute = word_count / duration_min
            st.info(f"⚡ Velocidad de habla: {words_per_minute:.0f} palabras/min")