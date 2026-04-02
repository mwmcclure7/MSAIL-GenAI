import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

# 1. Set up the device (GPU if available, otherwise CPU)
device = "cuda:0" if torch.cuda.is_available() else "cpu"
torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

model_id = "openai/whisper-large-v3-turbo"

# 2. Load the model and processor
print("Loading model...")
model = AutoModelForSpeechSeq2Seq.from_pretrained(
    model_id, 
    torch_dtype=torch_dtype, 
    low_cpu_mem_usage=True, 
    use_safetensors=True
)
model.to(device)

processor = AutoProcessor.from_pretrained(model_id)

# 3. Initialize the speech recognition pipeline
pipe = pipeline(
    "automatic-speech-recognition",
    model=model,
    tokenizer=processor.tokenizer,
    feature_extractor=processor.feature_extractor,
    torch_dtype=torch_dtype,
    device=device,
    chunk_length_s=30,  # Tells the model to process audio in 30-second windows
)

# 4. Transcribe your local audio file
audio_file = "test.mp3"

print(f"Transcribing {audio_file}...")

# 5. Force the language and task to bypass the detection bug
result = pipe(
    audio_file,
    generate_kwargs={
        "task": "transcribe", 
        "language": "english"  # Change this if your audio is in another language
    }
)

# 6. Output the result
print("\nTranscription:")
print(result["text"])
