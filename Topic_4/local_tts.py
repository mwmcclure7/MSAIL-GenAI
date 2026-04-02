from kokoro import KPipeline
import soundfile as sf

print("Loading Kokoro-82M Pipeline...")
# Initialize the pipeline. 
# lang_code='a' specifies American English. ('b' is British English)
pipeline = KPipeline(lang_code='a') 

text_to_speak = """
This is a test of the Kokoro text-to-speech model. 
Because it only has 82 million parameters, it runs incredibly fast, 
even on older graphics cards or basic processors!
"""

print("Generating audio...")
# The pipeline acts as a generator, yielding audio chunks
generator = pipeline(
    text_to_speak,
    voice='af_heart',  # 'af_heart' is a high-quality American Female voice
    speed=1.0,         # You can speed up or slow down the audio here
    split_pattern=r'\n+' # This tells the model to process the audio line-by-line
)

# Loop through the generated chunks and save them
for i, (graphemes, phonemes, audio) in enumerate(generator):
    # graphemes = the raw text
    # phonemes = the phonetic translation the model used
    # audio = the actual audio array
    
    output_filename = f"kokoro_output_chunk_{i}.wav"
    
    # Kokoro outputs audio natively at 24,000 Hz
    sf.write(output_filename, audio, 24000)
    print(f"Saved: {output_filename}")

print("\nSuccess! All audio chunks have been saved.")
