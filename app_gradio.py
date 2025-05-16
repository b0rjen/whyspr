import gradio as gr
from openai import OpenAI
import tempfile
import os
from pydub import AudioSegment
import shutil
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
import threading

# Configura el cliente de OpenAI
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# Variable global para control de cancelación
cancel_flag = threading.Event()

def create_temp_folder():
    temp_dir = os.path.join(tempfile.gettempdir(), "audio_chunks")
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)
    return temp_dir

def get_audio_duration(file_path):
    """Obtiene la duración del audio en segundos"""
    audio = AudioSegment.from_file(file_path)
    return len(audio) / 1000.0

def calculate_whisper_cost(duration_seconds):
    """Calcula el costo de usar Whisper API basado en la duración"""
    cost_per_minute = 0.006
    duration_minutes = duration_seconds / 60
    return duration_minutes * cost_per_minute

def split_audio(file_path, max_size_mb=24):
    audio = AudioSegment.from_file(file_path)
    max_size_bytes = max_size_mb * 1024 * 1024
    duration_ms = len(audio)
    bytes_per_ms = len(audio.raw_data) / duration_ms
    max_duration_ms = (max_size_bytes / bytes_per_ms) * 0.95
    chunks = []
    temp_dir = create_temp_folder()
    for i in range(0, duration_ms, int(max_duration_ms)):
        chunk = audio[i:i + int(max_duration_ms)]
        chunk_path = os.path.join(temp_dir, f"chunk_{i//1000}.mp4")
        chunk.export(chunk_path, format="mp4", codec="aac")
        chunks.append(chunk_path)
    return chunks, temp_dir

def generate_pdf(text):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setFont("Helvetica", 12)
    text_lines = text.split("\n")
    y = 750
    for line in text_lines:
        if y < 50:
            c.showPage()
            y = 750
        words = line.split()
        current_line = ""
        for word in words:
            test_line = current_line + " " + word if current_line else word
            if c.stringWidth(test_line, "Helvetica", 12) > 500:
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

def transcribe_audio(audio_file, progress=gr.Progress()):
    if audio_file is None:
        return "Por favor, sube un archivo de audio.", None, None, None, None
    
    global cancel_flag
    cancel_flag.clear()
    
    try:
        # Calcular duración y costo
        duration = get_audio_duration(audio_file)
        cost = calculate_whisper_cost(duration)
        
        file_size = os.path.getsize(audio_file)
        max_size = 25 * 1024 * 1024
        
        # Mostrar información inicial
        progress(0, desc=f"Iniciando transcripción... Duración: {duration/60:.1f} min, Costo: ${cost:.4f}")
        
        full_transcription = ""
        temp_dir = None
        
        if file_size > max_size:
            chunks, temp_dir = split_audio(audio_file, max_size_mb=24)
            
            for i, chunk_path in enumerate(chunks):
                if cancel_flag.is_set():
                    return "Transcripción cancelada por el usuario.", None, None, duration, cost
                    
                progress((i + 1) / len(chunks), desc=f"Procesando trozo {i+1}/{len(chunks)}...")
                
                with open(chunk_path, "rb") as f:
                    result = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=f
                    )
                    full_transcription += result.text + " "
        else:
            if cancel_flag.is_set():
                return "Transcripción cancelada por el usuario.", None, None, duration, cost
                
            with open(audio_file, "rb") as f:
                result = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f
                )
                full_transcription = result.text
        
        # Generar archivos de descarga
        pdf_buffer = generate_pdf(full_transcription)
        pdf_path = "transcription.pdf"
        with open(pdf_path, "wb") as f:
            f.write(pdf_buffer.getvalue())
        
        txt_path = "transcription.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(full_transcription)
        
        # Calcular estadísticas
        word_count = len(full_transcription.split())
        words_per_minute = word_count / (duration / 60) if duration > 0 else 0
        
        stats = f"""
        📊 **Estadísticas**
        - Palabras: {word_count:,}
        - Duración: {duration/60:.1f} minutos
        - Costo: ${cost:.4f}
        - Velocidad de habla: {words_per_minute:.0f} palabras/min
        """
        
        return full_transcription, pdf_path, txt_path, stats, None
        
    except Exception as e:
        return f"Error: {str(e)}", None, None, None, None
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

def cancel_transcription():
    global cancel_flag
    cancel_flag.set()
    return "Cancelando transcripción..."

# Crear la interfaz de Gradio
with gr.Blocks(title="Transcripción Whisper", theme=gr.themes.Soft()) as app:
    gr.Markdown("# 🎧 Transcripción con Whisper API")
    gr.Markdown("Sube tu archivo de audio para transcribirlo usando OpenAI Whisper.")
    
    with gr.Row():
        with gr.Column():
            audio_input = gr.File(
                label="📁 Archivo de Audio",
                file_types=[".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm"],
                elem_id="audio_upload"
            )
            
            with gr.Row():
                transcribe_btn = gr.Button("🎙️ Iniciar Transcripción", variant="primary", scale=3)
                cancel_btn = gr.Button("❌ Cancelar", variant="stop", scale=1)
            
            status_text = gr.Textbox(label="Estado", interactive=False)
            
        with gr.Column():
            transcription_output = gr.Textbox(
                label="📝 Texto Transcrito",
                lines=15,
                max_lines=20,
                interactive=False
            )
            
            stats_output = gr.Markdown(label="Estadísticas")
            
            with gr.Row():
                pdf_output = gr.File(label="📄 Descargar PDF", interactive=False)
                txt_output = gr.File(label="📝 Descargar TXT", interactive=False)
    
    # Eventos
    transcribe_btn.click(
        fn=transcribe_audio,
        inputs=[audio_input],
        outputs=[transcription_output, pdf_output, txt_output, stats_output, status_text]
    )
    
    cancel_btn.click(
        fn=cancel_transcription,
        outputs=[status_text]
    )
    
    gr.Markdown("""
    ### 💡 Instrucciones
    1. Sube un archivo de audio (máx. 200MB)
    2. Haz clic en "Iniciar Transcripción"
    3. Espera a que termine el proceso (puedes cancelar en cualquier momento)
    4. Descarga el resultado en PDF o TXT
    
    ### 💲 Costos
    - $0.006 USD por minuto de audio
    - El costo se calcula por duración del audio, no por tiempo de procesamiento
    """)

if __name__ == "__main__":
    app.launch(share=False)