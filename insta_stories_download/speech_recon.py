import sys
import os
import speech_recognition as sr
from moviepy.editor import VideoFileClip

def transcrever_video(video_path):
    try:
        video = VideoFileClip(video_path)
        
        # Verifica se há áudio no vídeo
        if not video.audio:
            print("Erro: O vídeo não contém faixa de áudio")
            return None
            
        audio_temp = "temp_audio.wav"
        video.audio.write_audiofile(audio_temp, codec='pcm_s16le')  # Força codec WAV
        
    
        # Inicializar o reconhecedor de fala
        recognizer = sr.Recognizer()
        
        try:
            # Carregar o arquivo de áudio
            with sr.AudioFile(audio_temp) as fonte:
                audio_data = recognizer.record(fonte)
                
                # Transcrever usando o Google Speech Recognition
                texto = recognizer.recognize_google(audio_data, language='pt-BR')
                return texto
                
        except sr.UnknownValueError:
            print("Não foi possível entender o áudio")
        except sr.RequestError as e:
            print(f"Erro no serviço de reconhecimento: {e}")
        finally:
            # Limpar arquivo temporário
            if os.path.exists(audio_temp):
                os.remove(audio_temp)
    except AttributeError:
        print("Erro ao processar esse aqui")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python transcrever_video.py <caminho_do_video>")
        sys.exit(1)
    
    video_path = sys.argv[1]
    transcricao = transcrever_video(video_path)
    
    if transcricao:
        print("\nTranscrição do Vídeo:")
        print(transcricao)
