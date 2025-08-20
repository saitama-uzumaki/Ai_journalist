import os
import asyncio
from typing import Dict, List
from dotenv import load_dotenv
load_dotenv()

from utils import (
    generate_news_urls_to_scrape,
    scrape_with_brightdata, 
    clean_html_to_text,
    extract_headlines,
    summarize_with_gemini_news_script
)

load_dotenv()

class NewsScraper:
    def __init__(self):
        self._rate_limiter = asyncio.Semaphore(3)

    async def scrape_news(self, topics: List[str]) -> Dict[str, str]:
        """Scrape and analyze news articles for given topics"""
        results = {}
        
        urls_dict = generate_news_urls_to_scrape(topics)
        
        for topic in topics:
            async with self._rate_limiter:
                try:
                    url = urls_dict.get(topic)
                    if not url:
                        results[topic] = f"No URL generated for topic: {topic}"
                        continue
                    
                    print(f"Scraping news for topic: {topic}")
                    search_html = scrape_with_brightdata(url)
                    
                    if not search_html or "Error" in search_html:
                        results[topic] = f"Failed to scrape content for {topic}"
                        continue
                    
                    clean_text = clean_html_to_text(search_html)
                    headlines = extract_headlines(clean_text)
                    
                    if not headlines:
                        results[topic] = f"No headlines found for {topic}"
                        continue
                    
                    summary = summarize_with_gemini_news_script(
                        api_key=os.getenv("GEMINI_API_KEY"),
                        headlines=headlines
                    )
                    
                    results[topic] = summary
                    print(f"Successfully processed news for topic: {topic}")
                    
                except Exception as e:
                    error_msg = f"Error processing {topic}: {str(e)}"
                    print(error_msg)
                    results[topic] = error_msg
                
                await asyncio.sleep(2)
        
        return {"news_analysis": results}


