from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI
from fuzzywuzzy import fuzz
import os
import json

# Load environment variables from .env file
load_dotenv()

# Instantiate the OpenAI client
client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

# Ensure that the OpenAI API key is set
if not client.api_key:
    raise ValueError("No OpenAI API key found. Please set the OPENAI_API_KEY environment variable.")

# Function to get YouTube video transcription
def get_youtube_transcription(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript = transcript_list.find_transcript(['en'])
        return transcript.fetch()
    except Exception as e:
        print(f"Error fetching transcript: {e}")
        return None

# Function to send text to OpenAI API and get a response
def process_with_openai(text):
    try:
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            response_format={ "type": "json_object" },
            messages=[
                {"role": "system", "content": "You output the beginning and end of the ad (15 words each) from the following youtube video in JSON with start and end fields. There should be no non-ad related content in the middle. Usually starts with todays video is sponsored by..."},
                {"role": "user", "content": text}
            ]
        )

        return response.choices[0].message.content
    except Exception as e:
        print(f"Error with OpenAI API: {e}")
        return None

# Function to exclude first 10 seconds of the transcription
def exclude_first_10_seconds(transcription):
    return [segment for segment in transcription if segment['start'] >= 10]

# Function to find matching segments in the transcription
def find_matching_segments(transcription, openai_response):
    start_text = openai_response['start']
    end_text = openai_response['end']

    start_segment = None
    end_segment = None
    highest_start_ratio = 0
    highest_end_ratio = 0

    for segment in transcription:
        start_ratio = fuzz.partial_ratio(segment['text'], start_text)
        end_ratio = fuzz.partial_ratio(segment['text'], end_text)

        if start_ratio > highest_start_ratio:
            highest_start_ratio = start_ratio
            start_segment = segment if start_ratio > 70 else None  # Adjust threshold as needed

        if end_ratio > highest_end_ratio:
            highest_end_ratio = end_ratio
            end_segment = segment if end_ratio > 70 else None  # Adjust threshold as needed

    return start_segment, end_segment

# Define a request model
class VideoRequest(BaseModel):
    videoId: str

# Instantiate the FastAPI app
app = FastAPI()

# Add CORS middleware to allow specific origins (or use '*' for all origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://example.com", "https://example.com"],  # List your allowed origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.post("/process_video/")
async def process_video(request: VideoRequest):
    video_id = request.videoId
    transcription = get_youtube_transcription(video_id)

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    filtered_transcription = exclude_first_10_seconds(transcription)
    combined_text = ' '.join([segment['text'] for segment in filtered_transcription])

    response_json = process_with_openai(combined_text)
    if response_json:
        try:
            openai_response = json.loads(response_json)
            start_segment, end_segment = find_matching_segments(filtered_transcription, openai_response)

            if start_segment and end_segment:
                # Calculate the duration of the end segment
                end_duration = end_segment['duration']
                # Return the start times and duration of the segments
                return {
                    "start_time": start_segment['start'],
                    "end_time": end_segment['start'],
                    "end_duration": end_duration
                }
            else:
                return {"message": "Matching segments not found"}
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="Error parsing OpenAI response")
    else:
        raise HTTPException(status_code=500, detail="OpenAI Response: Not available")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)