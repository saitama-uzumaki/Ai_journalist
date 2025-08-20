import streamlit as st
import requests
import os

BACKEND_URL = "http://localhost:1234"

def main():
    st.title("📰 Personal AI Journalist")
    
    if 'topics' not in st.session_state:
        st.session_state.topics = []
    
    with st.sidebar:
        st.header("⚙️ Settings")
        source_type = st.selectbox(
            "📡 Data Sources",
            options=["both", "news", "reddit"],
            format_func=lambda x: "📰 News" if x == "news" else ("👾 Reddit" if x == "reddit" else "🔄 Both")
        )
    
    st.markdown("#### 📌 Topic Management") 
    col1, col2 = st.columns([4, 1])
    
    with col1:
        new_topic = st.text_input(
           "✍️ Enter a topic to analyze",
           placeholder="e.g. Artificial Intelligence" 
        ) 
    
    with col2:
        add_disabled = len(st.session_state.topics) >= 3 or not new_topic.strip()
        if st.button("➕ Add", disabled=add_disabled):
            st.session_state.topics.append(new_topic.strip())
            st.rerun()     
    
    if st.session_state.topics:
        st.subheader("✅ Selected Topics")
        for i, topic in enumerate(st.session_state.topics[:3]):
            cols = st.columns([4, 1])
            cols[0].write(f"{i+1}. {topic}")
            if cols[1].button("❌ Remove", key=f"remove_{i}"):
                del st.session_state.topics[i]
                st.rerun()
    
    st.markdown("### 🎤 Audio Generation")
    st.write("🔊 Generate and play audio from your text in real-time")            
    
    if st.button("🚀 Generate Summary", disabled=(len(st.session_state.topics) == 0)):
        if not st.session_state.topics:
            st.error("⚠️ Please add at least one topic")
        else:
            with st.spinner("🔎 Analyzing topics and generating audio..."):
                try:
                    response = requests.post(
                        f"{BACKEND_URL}/generate-news-audio",
                        json={
                            "topics": st.session_state.topics,
                            "source_type": source_type,
                        },
                    )

                    if response.status_code == 200:
                        result = response.json()
                        
                        st.subheader("📄 Generated Summary")
                        st.write(result.get("summary", "No summary available"))
                        
                        if "audio_path" in result:
                            audio_filename = os.path.basename(result["audio_path"])
                            
                            audio_response = requests.get(
                                f"{BACKEND_URL}/download-audio/{audio_filename}"
                            )
                            
                            if audio_response.status_code == 200:
                                st.subheader("🎵 Audio Summary")
                                st.audio(audio_response.content, format="audio/mpeg")
                                st.download_button(
                                    "⬇️ Download Audio Summary",
                                    data=audio_response.content,
                                    file_name="news-summary.mp3",
                                    mime="audio/mpeg",
                                )
                            else:
                                st.error("Failed to retrieve audio file")
                        else:
                            st.error("No audio file was generated")
                    else:
                        handle_api_error(response)

                except requests.exceptions.ConnectionError:
                    st.error("❌ Connection Error: Could not reach the backend server. Make sure your backend is running on port 1234.")
                except Exception as e:
                    st.error(f"⚠️ Unexpected Error: {str(e)}")

def handle_api_error(response):
    """Handle API error responses"""
    try:
        error_detail = response.json().get("detail", "Unknown error")
        st.error(f"API Error ({response.status_code}): {error_detail}")
    except ValueError:
        st.error(f"Unexpected API Response: {response.text}")

if __name__ == '__main__':
    main()