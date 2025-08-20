from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from dotenv import load_dotenv
import os

from models import NewsRequest
from news_scraper import NewsScraper
from reddit_scraper import scrape_reddit_topics
from utils import generate_broadcast_news, text_to_audio_elevenlabs_sdk

app = FastAPI()
load_dotenv()

@app.post("/generate-news-audio")
async def generate_news_audio(request: NewsRequest):
    try:
        print(f"Processing request for topics: {request.topics}")
        print(f"Source type: {request.source_type}")
        
        results = {}

        # Scrape news
        if request.source_type in ["news", "both"]:
            print("Starting news scraping...")
            news_scraper = NewsScraper()
            results["news"] = await news_scraper.scrape_news(request.topics)
            print(f"News scraping completed: {results['news']}")

        # Scrape reddit
        if request.source_type in ["reddit", "both"]:
            print("Starting Reddit scraping...")
            results["reddit"] = await scrape_reddit_topics(request.topics)
            print(f"Reddit scraping completed: {results['reddit']}")

        # Extract results
        news_data = results.get("news", {})
        reddit_data = results.get("reddit", {})

        print("Generating broadcast summary...")
        # Generate summary using Gemini
        api_key = os.getenv("GEMINI_API_KEY")
        news_summary = generate_broadcast_news(
            api_key=api_key,
            news_data=news_data,
            reddit_data=reddit_data,
            topics=request.topics
        )
        
        print(f"Summary generated: {news_summary[:100]}...")

        # Convert summary to audio using ElevenLabs
        print("Starting audio conversion...")
        audio_path = text_to_audio_elevenlabs_sdk(
            text=news_summary,
            voice_id="JBFqnCBsd6RMkJVDRzZb",
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
            output_dir="audio"
        )

        if audio_path:
            print(f"Audio conversion successful: {audio_path}")
            return {
                "status": "success",
                "summary": news_summary,
                "audio_path": audio_path
            }
        else:
            print("Audio conversion failed, but returning summary")
            # Return summary even if audio fails
            return {
                "status": "partial_success",
                "summary": news_summary,
                "audio_path": None,
                "message": "Summary generated successfully, but audio conversion failed. You can still read the summary."
            }

    except Exception as e:
        print(f"Backend error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@app.get("/download-audio/{filename}")
async def download_audio(filename: str):
    """Endpoint to download generated audio files"""
    audio_path = f"audio/{filename}"
    if os.path.exists(audio_path):
        # Check if it's a text file (fallback case)
        if filename.endswith('.txt'):
            return FileResponse(
                path=audio_path,
                media_type="text/plain",
                filename=filename
            )
        else:
            return FileResponse(
                path=audio_path,
                media_type="audio/mpeg",
                filename=filename
            )
    else:
        raise HTTPException(status_code=404, detail="Audio file not found")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Backend is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend:app",
        host="0.0.0.0",
        port=1234,
        reload=True
    )