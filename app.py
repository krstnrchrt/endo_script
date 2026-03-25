import streamlit as st
import requests
from bs4 import BeautifulSoup
from PIL import Image
import base64
import io
import os
import zipfile

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Endometriosis Health AI Image Generation", page_icon="🌸")
API_KEY = st.secrets["OPENROUTER_API_KEY"]
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

BRAND_STYLE = (
    "Style: Minimalist illustrations with soft organic shapes.\n\n"
    "Color Palette: Primarily soft colors with neutral sand accents.\n\n"
    "Mood: Calm, empathetic, medical but modern.\n\n"
    "Consistency: High-quality professional blog header aesthetic. \n\n"
    "Subject: Primarily portray women (all ethnicities) in a respectful, non-clinical way. \n\n"
    "Composition: Focus on symbolic, respectful representations of the human body (e.g. silhouettes, hands, abstract forms or cartoon-style). Avoid detailed anatomy.\n\n"
    "No messy backgrounds, no cluttered medical equipment, no bright neon colors.\n\n"
    "The image must be safe, fully clothed, and suitable for medical education.\n\n"
    "Avoid any writing within the image."
)

# --- 2. SCRAPING FUNCTION ---
def get_blog_data():
    url = "https://endometriose.app/aktuelles-2/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/119.0.0.0 Safari/537.36'}
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        blog_data = []

        all_titles = soup.select('.entry-title') # The dot means "class"
        st.write(f"🔍 Diagnostic: Found {len(all_titles)} elements with class 'entry-title'")

        blog_data = []
    
        title_elements = soup.select('.entry-title')
        for element in title_elements:
            link_tag = element.find('a')
            if link_tag:
                title = link_tag.get_text(strip=True)
                url = link_tag['href']
            
            if any(path in url for path in ["/impulse/", "/lernen/", "/antrag/"]): #prioritize blogposts on these paths to avoid noise 
                    blog_data.append({"title": title, "url": url})
        
        # Deduplicate: Sometimes sliders and grids repeat the same post
        unique_blogs = list({v['title']: v for v in blog_data}.values())
        
        st.write(f"Success: Found {len(unique_blogs)} unique blog posts.")
        return unique_blogs[:NUM_BLOGS] # SET NUMBER OF BLOGS TO PROCESS

    except Exception as e:
        st.error(f"Scraper failed: {e}")
        return []

# --- 3. GENERATION FUNCTION ---

def generate_image_workflow(title):
    debug_container = st.expander(f"🪲 Debugger Details: {title[:30]}...")
    
    # Step A: Reasoning for Visual Concept (Text-to-Text)
    payload_text = {
        "model": "google/gemini-3.1-flash-lite-preview",
        "messages": [{"role": "user", "content": f"Describe a simple, symbolic visual for: \"{title}\" within the medical education context. DO NOT focus on detailed anatomy but describe the essence of the topic. Focus on one central object and keep it concise under 30 words."}]
    }
    
    try:
        #1. Get the visual concept 
        res_text = requests.post(OPENROUTER_URL, headers=HEADERS, json=payload_text)
        if res_text.status_code != 200:
            debug_container.error(f"Text API Error: {res_text.text}")
            return None
        

        data_text = res_text.json()
        visual_desc = data_text['choices'][0]['message']['content']
        debug_container.info(f"Visual Concept: {visual_desc}")

        # Step B: Generate Image
        FINAL_PROMPT = f"{visual_desc}. Follow the described brand guidelines:{BRAND_STYLE}"

        payload_img = {
            "model": "black-forest-labs/flux.2-klein-4b", 
            "messages": [{"role": "user", "content": FINAL_PROMPT}],
        }
        res_img = requests.post(OPENROUTER_URL, headers=HEADERS, json=payload_img).json()

        # STEP C: Robust Parsing for the new JSON structure
        try:
            # We look for the image URL in all possible locations
            msg_data = res_img['choices'][0]['message']
            
            if "images" in msg_data:
                img_obj = msg_data['images'][0]
                # DEBUG: Handle the extra 'image_url' nesting
                if "image_url" in img_obj:
                    image_url = img_obj['image_url']['url']
                else:
                    image_url = img_obj['url']
            else:
                image_url = msg_data.get('content', '')

            if "base64," in image_url:
                base64_str = image_url.split("base64,")[1]
                return Image.open(io.BytesIO(base64.b64decode(base64_str)))
            elif image_url.startswith("http"):
                img_res = requests.get(image_url)
                return Image.open(io.BytesIO(img_res.content))
                
        except (KeyError, IndexError, TypeError) as parse_err:
            debug_container.error(f"Parsing error: {parse_err}")
            debug_container.write("Raw response for analysis:")
            debug_container.write(res_img)
            return None

    except Exception as e:
        debug_container.exception(f"Critical Error: {e}")
        return None


# --- 4. UI ---
st.title("🌸 Endo Health: Automated Brand Image Creation")
st.write("This tool scrapes live blog titles and generates cohesive, branded header imagery.")

# --- SIDEBAR CONFIGURATION ---
if "results" not in st.session_state: #Initialize
        st.session_state.results = []

with st.sidebar:
    st.header("⚙️ Configuration")
    #TARGET_URL = st.text_input("Target URL", value="https://endometriose.app/aktuelles-2/")
    NUM_BLOGS = st.slider("Choose the number of blog posts to process", 1, 10, 5)
    
    st.subheader("🎨 Brand Style")
    # Making the brand style editable
    custom_brand_style = st.text_area("View Brand Guidelines and edit if necessary", value=BRAND_STYLE, height=300)

if st.button("Start Workflow"):
    blogs = get_blog_data()
    
    if not blogs:
        st.warning("No blog posts found. Check the website connection.")
    else:
        st.success(f"Starting workflow with {len(blogs)} blog posts. Generating images...")
        st.session_state.results = [] #Clear previous results

        with st.status("🚀 Processing Workflow...", expanded=True) as status:
            for idx, blog in enumerate(blogs):
                st.write(f"Generating image {idx+1}/{len(blogs)}: {blog['title']}")
                img = generate_image_workflow(blog['title'])
                
                if img:
                    # SAVE to session state instead of just displaying
                    st.session_state.results.append({
                        "title": blog['title'],
                        "url": blog['url'],
                        "image": img
                    })
            status.update(label="All images generated! Click here to see details.", state="complete", expanded=False)

# --- 3. RENDERING & DOWNLOAD (Outside the button block) ---
if st.session_state.results:
    st.divider()
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        for i, res in enumerate(st.session_state.results):
            buf = io.BytesIO()
            res['image'].save(buf, format="PNG")
            zf.writestr(f"endo_header_{i+1}.png", buf.getvalue())
            
    st.download_button(
        label="Download All Images as ZIP",
        data=zip_buffer.getvalue(),
        file_name="endo_health_headers.zip",
        mime="application/zip",
        use_container_width=True
    )
    
    st.divider()

    # Display the grid
    cols = st.columns(2)
    for idx, res in enumerate(st.session_state.results):
        with cols[idx % 2]:
            st.subheader(f"{idx+1}. {res['title']}")
            st.link_button("View Original Article", res['url'])
            
            # Display from state
            st.image(res['image'], use_container_width=True)

            # Individual Download option
            buf = io.BytesIO()
            res['image'].save(buf, format="PNG")
            
            st.download_button(
                label="Download This Image",
                data=buf.getvalue(),
                file_name=f"endo_header_{idx+1}.png",
                mime="image/png",
                key=f"dl_btn_{idx}" 
            )
            st.divider()
