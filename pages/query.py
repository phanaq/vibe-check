import streamlit as st
import base64, requests
from utils.connect import intialize_connections


intialize_connections()

prompt = """
    Please describe the setting that you see in the image, including descriptors of the ambiance and vibe.
    What types of music would be fitting for this setting? What kind of mood is conveyed in the image?
"""

if 'user_feedback' not in st.session_state:
    st.session_state.user_feedback = ''
if 'top_songs' not in st.session_state:
    st.session_state.top_songs = ''

@st.cache_data
def get_setting_description_from_image(photo_input):
    print("get_setting_description_from_image")
    setting_description = ''
    if photo_input:
        image_bytes = photo_input.getvalue()
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {st.secrets["OPENAI_API_KEY"]}"
        }
        payload = {
            "model": "gpt-4o",
            "messages": [
                {
                "role": "user",
                "content": [
                    {
                    "type": "text",
                    "text": """
                        You are an AI agent that helps users find music that matches their current setting.
                        Please describe the ambiance and vibe of the included image. 
                        What types of music would be fitting for this setting? 
                        What kind of mood is conveyed in the image?"""
                    },
                    {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
                }
            ],
            "max_tokens": 300
            }
        print("payload", payload)
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        print("response", response.json())
        setting_description = response.json()["choices"][0]["message"]["content"]
        print(setting_description)

    return setting_description



def handleSubmit():
    print('submit!')
    if st.session_state.photo_input or st.session_state.text_input:
        setting_description = get_setting_description_from_image(st.session_state.photo_input)
        full_search_query = " ".join([setting_description, st.session_state.text_input])
        st.session_state.user_feedback = full_search_query
        findSongs(full_search_query)
    else:
        st.session_state.user_feedback = None

def findSongs(setting_description):
    print("findSongs called")
    top_songs = list(st.session_state.song_collection.find(
        sort={"$vectorize": setting_description},
        projection={"_id": 0, "$vectorize": 1, "$vector": 0},
        limit=5,
        include_similarity=True
    ))
    # print(top_songs)
    st.session_state.top_songs = top_songs
    return


### UI ###
st.title("Vibe Check :musical_note:")

photo_method = st.radio(
    "Select an image upload method:",
    ["Camera", "Upload"],
)

with st.form(key="query_form"):
    st.header("Multimodal Inputs")
    if photo_method == "Camera":
        photo_input = st.camera_input(
            "Take a picture of your setting:", 
            key="photo_input",
        )
    elif photo_method == "Upload":
        photo_input = st.file_uploader(
            "Upload a photo:",
            key="photo_input",
            type=["jpg", "jpeg", "png"]
        )
    text_input = st.text_input(
        "Write a description of your setting:",
        key="text_input"
    )
    st.form_submit_button(on_click=handleSubmit)

with st.container(border=True):
    st.header("Outputs")
    show_prompt = st.checkbox("Show prompt sent to the LLM")
    show_df = st.checkbox("Show data retrieved from Astra DB")
    if st.session_state.user_feedback:
        if show_prompt:
            st.subheader("Prompt")
            with st.container(border=True):
                st.write(st.session_state.user_feedback)
        if show_df:
            st.subheader("Best Matches Retrieved from Astra DB")
            st.dataframe(
                st.session_state.top_songs,
                column_config={
                    "Song_URL": st.column_config.LinkColumn()
                }
            )
        st.subheader("Top Recommended Songs")
        for song in st.session_state.top_songs:
            name = song.get("Song_Name", "N/A")
            artist = song.get("Artist", "N/A")
            url = song.get("Song_URL", "")
            st.write("- [%s - %s](%s)" % (name, artist, url))
    else:
        st.info("No photo or text input uploaded.")
    