from groq import Groq

# Initialize the Groq client
client = Groq()

# Specify the path to the audio file
filename = "test.mp3"

# Open the audio file
with open(filename, "rb") as file:
    # Create a transcription of the audio file
    transcription = client.audio.transcriptions.create(
      file=file, # Required audio file
      model="whisper-large-v3-turbo", # Required model to use for transcription
      prompt="Specify context or spelling",  # Optional
      language="en",  # Optional
      temperature=0.0  # Optional
    )
    print(transcription.text)
