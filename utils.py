from urllib.parse import quote_plus
import os
import requests
from fastapi import HTTPException
from bs4 import BeautifulSoup
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from datetime import datetime
import uuid

from dotenv import load_dotenv


# Load env file
load_dotenv()

def generate_valid_news_url(keyword: str) -> str:
    """Generate a Google News search URL for a keyword"""
    q = quote_plus(keyword)
    return f"https://news.google.com/search?q={q}&tbm=nws"

def scrape_with_brightdata(url: str) -> str:
    """Scrape a URL using BrightData proxy service"""
    try:
        proxy_host = "zproxy.lum-superproxy.io"
        proxy_port = "22225"
        proxy_user = os.getenv("BRIGHTDATA_USER")
        proxy_pass = os.getenv("BRIGHTDATA_PASS")
        
        proxy_url = f"http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}"
        
        proxies = {
            "http": proxy_url,
            "https": proxy_url
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url, proxies=proxies, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
        
    except requests.exceptions.RequestException as e:
        print(f"BrightData scraping error: {str(e)}")
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            return response.text
        except:
            return f"Error scraping {url}: {str(e)}"

def clean_html_to_text(html_content: str) -> str:
    """Clean HTML content to plain text"""
    soup = BeautifulSoup(html_content, "html.parser")
    text = soup.get_text(separator="\n")
    return text.strip()

def extract_headlines(cleaned_text: str) -> str:
    """Extract headlines from cleaned news text content"""
    headlines = []
    current_block = []
    
    lines = [line.strip() for line in cleaned_text.split('\n') if line.strip()]
    
    for line in lines:
        if line == "More":
            if current_block:
                headlines.append(current_block[0])
                current_block = []
        else:
            current_block.append(line)
    
    if current_block:
        headlines.append(current_block[0])
    
    return "\n".join(headlines)

def summarize_with_gemini_news_script(api_key: str, headlines: str) -> str:
    """Summarize headlines into a TTS-friendly broadcast news script using Gemini"""
    system_prompt = """
You are my personal news editor and scriptwriter for a news podcast. Your job is to turn raw headlines into a professional, broadcast-style news script.

The final output will be read aloud by a news anchor or text-to-speech engine. So:
- Do not include any special characters, emojis, formatting symbols, or markdown.
- Do not add any preamble or framing like "Here's your summary" or "Let me explain".
- Write in full, clear, spoken-language paragraphs.
- Keep the tone formal, professional, and broadcast-style - just like a real TV news script.
- Focus on the most important headlines and turn them into short, informative news segments that sound natural when read aloud.
- Start right away with the actual script, using transitions between topics if needed.

Remember: Your only output should be a clean script that is ready to be read out loud.
"""
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-pro",
            google_api_key=os.getenv("GEMINI_API_KEY"),
            temperature=0.4
        )
        
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=headlines)
        ])
        
        return response.content
    except Exception as e:
        return f"Error generating summary: {str(e)}"

def generate_news_urls_to_scrape(list_of_keywords):
    """Generate URLs for each keyword"""
    valid_urls_dict = {}
    for keyword in list_of_keywords:
        valid_urls_dict[keyword] = generate_valid_news_url(keyword)
    return valid_urls_dict

def generate_broadcast_news(api_key, news_data, reddit_data, topics):
    """Generate a TTS-ready news script based on provided news and Reddit data"""
    system_prompt = """
You are broadcast_news_writer, a professional virtual news reporter. Generate natural, TTS-ready news segments.

For each topic, STRUCTURE BASED ON AVAILABLE DATA:
1. If news exists: "According to official reports..." + summary
2. If Reddit exists: "Online discussions on Reddit reveal..." + summary
3. If both exist: Present news first, then Reddit reactions
4. If neither exists: Skip the topic (shouldn't happen)

Formatting rules:
- ALWAYS start directly with the content, NO INTRODUCTIONS
- Keep audio length 60-120 seconds per topic
- Use natural speech transitions like "Meanwhile, online discussions.."
- Incorporate 1-2 short quotes from Reddit when available
- Maintain neutral tone but highlight key sentiments
- End with "To wrap up this segment..." summary

Write in full paragraphs optimized for speech synthesis. Avoid markdown.
"""
    try:
        topic_blocks = []
        for topic in topics:
            news_content = news_data.get("news_analysis", {}).get(topic, "") if news_data else ""
            reddit_content = reddit_data.get("reddit_analysis", {}).get(topic, "") if reddit_data else ""
            context = []

            if news_content:
                context.append(f"OFFICIAL NEWS CONTENT:\n{news_content}")
            if reddit_content:
                context.append(f"REDDIT DISCUSSION CONTENT:\n{reddit_content}")

            if context:
                topic_blocks.append(f"TOPIC: {topic}\n" + "\n".join(context))

        user_prompt = (
            "Create broadcast segments for these topics using available sources:\n\n" +
            "\n\n--- NEW TOPIC ---\n\n".join(topic_blocks)
        )

        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=api_key,
            temperature=0.7
        )

        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])

        return response.content
    except Exception as e:
        return f"Error generating broadcast: {str(e)}"

def text_to_audio_elevenlabs_sdk(
    text: str,
    voice_id: str = "JBFqnCBsd6RMkJVDRzZb",
    model_id: str = "eleven_multilingual_v2",
    output_format: str = "mp3_44100_128",
    output_dir: str = "audio",
    api_key: str = None
) -> str:
    """Convert text to speech using ElevenLabs SDK with better error handling"""
    try:
        # Try ElevenLabs first
        api_key =api_key or os.getenv("ELEVENLABS_API_KEY")
        
        print(f"Attempting ElevenLabs TTS conversion...")
        print(f"Text length: {len(text)} characters")
        
        # Check if text is too long (ElevenLabs has limits)
        if len(text) > 5000:
            text = text[:5000] + "..."
            print("Text truncated to 5000 characters")
        
        # Try ElevenLabs
        try:
            from elevenlabs.client import ElevenLabs
            from elevenlabs import save
            
            client = ElevenLabs(api_key=api_key)
            
            audio = client.generate(
                text=text,
                voice=voice_id,
                model=model_id
            )
            
            os.makedirs(output_dir, exist_ok=True)
            
            filename = f"tts_{uuid.uuid4().hex[:8]}.mp3"
            filepath = os.path.join(output_dir, filename)
            
            save(audio, filepath)
            print(f"ElevenLabs TTS successful: {filepath}")
            return filepath
            
        except Exception as eleven_error:
            print(f"ElevenLabs failed: {str(eleven_error)}")
            
            # Fallback to gTTS (Google Text-to-Speech)
            try:
                from gtts import gTTS
                import io
                
                print("Falling back to Google TTS...")
                
                tts = gTTS(text=text, lang='en', slow=False)
                
                os.makedirs(output_dir, exist_ok=True)
                filename = f"tts_gtts_{uuid.uuid4().hex[:8]}.mp3"
                filepath = os.path.join(output_dir, filename)
                
                tts.save(filepath)
                print(f"Google TTS successful: {filepath}")
                return filepath
                
            except Exception as gtts_error:
                print(f"Google TTS also failed: {str(gtts_error)}")
                
                # Last fallback - create a dummy audio file with text content
                os.makedirs(output_dir, exist_ok=True)
                filename = f"text_summary_{uuid.uuid4().hex[:8]}.txt"
                filepath = os.path.join(output_dir, filename)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"Audio generation failed. Here's the text summary:\n\n{text}")
                
                print(f"Created text file instead: {filepath}")
                return filepath

    except Exception as e:
        print(f"Complete TTS failure: {str(e)}")
        return None