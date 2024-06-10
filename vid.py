import streamlit as st
import google.generativeai as genai
from pathlib import Path
import assemblyai as aai
from PIL import Image
from moviepy.editor import *
from moviepy.config import change_settings
import pysrt
from gtts import gTTS
import os
from mutagen import File
from moviepy.editor import ImageClip, AudioFileClip, VideoFileClip, concatenate_videoclips, CompositeVideoClip
from moviepy.video.tools.subtitles import SubtitlesClip
import numpy as np
import re

GOOGLE_API_KEY = 'AIzaSyBeuj_-fGbJA0ZaK4mKekzZWe7TXOpN_R0'
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel(model_name="gemini-pro-vision")
tmodel = genai.GenerativeModel(model_name = "models/gemini-1.0-pro")

change_settings({"IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\convert.exe"})
video_audio=[]
title=[]
def save_uploaded_files(uploaded_files):
    if not os.path.exists("uploaded_images"):
        os.makedirs("uploaded_images")
    file_paths = []
    for uploaded_file in uploaded_files:
        file_path = os.path.join("uploaded_images", uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        file_paths.append(file_path)
    return file_paths

def image_format(image_path):
    img = Path(image_path)
    if not img.exists():
        raise FileNotFoundError(f"Could not find image: {img}")
    image_parts = [
        {
            "mime_type": "image/png",
            "data": img.read_bytes()
        }
    ]
    return image_parts

def gemini_output(input_prompt, image_path):
    image_info = image_format(image_path)
    input_prompt_with_image = [input_prompt, image_info[0], ""]
    response = model.generate_content(input_prompt_with_image)
    return response.text

def sequence_text(result):
    prompt=f'''
    Basic Subtitle : 
    {result}

    - You are provided with a basic subtitle to guide a user through a website.
    - Convert it into a clear and complete content so that we can provide it as a subtitle for a tutorial video.
    - Enrich the content by changing them to be suitable for a professional tutorial video.
    - Mention the Page Number which page the content belongs to . 
    - don't Mention the navigation Items . Mention only the curerntly web .
    - It should be like same as a human explaining the content in a enriched and attractive way .
    - It should be user friendly and in an ambigious way to understand easily.
    - Check for grammar and spelling mistakes before giving the response .
    - Maintain the order of the guidence as you were provided to you.so that it will sync to the video that is playing fot this subtitle.
    '''

    res=tmodel.generate_content(prompt)
    return res.text


def retext(steps, modification, original_text):
    prompt = f"""
    Original Text:
    {original_text}
    
    Steps:
    {steps}
    
    Modification:
    {modification}
    
    Task:
    -Please modify the original text according to the steps and modifications provided. Ensure the modified text follows the same steps format as the original text.
    -Mention the Page Number which page the content belongs to . 
    -
    Modified Text:
    """
    res=tmodel.generate_content(prompt)

    return res.text


def subtitle_generater(subtitle):
    sub=pysrt.open(subtitle)
    st.write(sub)

def text_generation(image_path):
    summary_prompt = (
        "Describe all the buttons and links visible in the website screenshot, including their purposes. "
        "For each button or link, specify the actions that a user can perform, such as clicking, buying, adding, viewing, filling, and visiting. "
        "Do not use examples provided. Analyze the image independently and describe all the actions/buttons present. "
        "Ensure you do not miss any actions/events or functions, as they are crucial for generating a tutorial on using the webpage."
        "Provide a comprehensive summary that accurately represents the functionality of the webpage. "
        "Do not miss any buttons, events, or actions in the screenshot."
    )
    summary_result = gemini_output(summary_prompt, image_path)

    summary_verify_prompt = (
        "Verify the summary to ensure it accurately reflects all functions and events described. "
        "Ensure actions such as clicking, buying, adding, viewing, filling, and visiting are clearly represented. "
        "Do not use examples provided. Analyze the image independently and describe all the actions/buttons present. "
        "Ensure you do not miss any actions/events or functions, as they are crucial for generating a tutorial on using the webpage."
        f"Summary:\n{summary_result}\n"
        "Do not miss any events or actions."
    )
    verify_result = gemini_output(summary_verify_prompt, image_path)

    final_response_prompt = (
        "Create a concise 2-3 line subtitle for a tutorial video on the webpage. "
        "The subtitle should guide users on performing actions such as clicking, buying, adding, viewing, filling, and visiting. "
        "Do not use examples provided. Analyze the image independently and describe all the actions/buttons present. "
        "Ensure the subtitle includes all key actions and buttons without missing any."
        f"Summary:\n{verify_result}\n"
        "The final result should contain all the available actions/buttons and their functions."
    )
    subtitle = gemini_output(final_response_prompt, image_path)
    return subtitle

def clean(text):
    pages = text.split('**Page ')

    cleaned_pages = []
    for page in pages:
        if page.strip():  # Skip any empty strings resulting from the split
            cleaned_page = page.replace('\n', ' ').strip()
            modified_string = re.sub(r'[0-9]+', '', cleaned_page).strip()
            clean_page=modified_string.replace('**','')
            clean=clean_page.replace(':','').strip()
            cleaned_pages.append(clean) 


    return cleaned_pages


def time_to_seconds(time_obj):
    return time_obj.hours * 3600 + time_obj.minutes * 60 + time_obj.seconds + time_obj.milliseconds / 1000

def create_subtitle_clips(subtitles, videosize, fontsize=30, font='Arial', color='white', debug=False):
    subtitle_clips = []
    for subtitle in subtitles:
        start_time = time_to_seconds(subtitle.start)
        end_time = time_to_seconds(subtitle.end)
        duration = end_time - start_time
        video_width, video_height = videosize
        text_clip = TextClip(subtitle.text, fontsize=fontsize, font=font, color=color, bg_color='black', size=(video_width * 0.5, None), method='caption').set_start(start_time).set_duration(duration)
        subtitle_x_position = 'center'
        subtitle_y_position = video_height * 9 / 10
        text_position = (subtitle_x_position, subtitle_y_position)
        subtitle_clips.append(text_clip.set_position(text_position))
    return subtitle_clips


def srtrecreate(file_path,user,i):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    blocks = content.strip().split('\n\n')
    response = ''

    
    for block in blocks:
        match = re.match(r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3})\n(.+)', block, re.DOTALL)
        if match:
            index = match.group(1)
            timestamp = match.group(2)
            text = match.group(3).replace('\n', ' ')
            response += f"{index}\n{timestamp}\n{text}\n\n"

    prompt = f'''
    SRT File:
        {response}

        ***
    Find and replace with correct spelling in all the required places. For your reference of what spellings must be changed with high piority is given below:
    {user}

    You are given with the naming convections for a company's website and you need to replace the inappropriate words with given suitable words. 
    Check the Splling and Return the corrected content in the same SRT format.
    Don't change any time frame details give all as it is by changing only the spelling mistakes.
    Don't mention the replaced words or other stuffs only give the final replaced content.

    '''
    
    res = tmodel.generate_content(prompt)
    
    corrected_subtitles = res.text.strip()
    corrected_blocks = corrected_subtitles.split('\n\n')
    file_path='sub'+str(i)+'.srt'
    with open(file_path, 'w', encoding='utf-8') as corrected_file:
        for corrected_block in corrected_blocks:
            corrected_file.write(corrected_block.strip() + '\n\n')

    st.write("Spelling correction completed and saved to 'subtitles.srt'.")
    return file_path

def getvideofromimage(image_path, text,index):
    # engine = pyttsx3.init()
    # output_file = "output.wav"
    # engine.save_to_file(text, output_file)
    # engine.runAndWait()
    language = 'en'
    myobj = gTTS(text=text, lang=language, slow=False)
    output_file = "output.wav"
    myobj.save(output_file)
    aai.settings.api_key = "e1313b421dec4789bddac187ad824975"
    transcript = aai.Transcriber().transcribe(output_file)
    subtitles = transcript.export_subtitles_srt()
    subtitle = "subtitles"+str(index)+".srt"
    title.append(subtitle)
    with open(subtitle, "w") as f:
        f.write(subtitles)
    audio_path ='output.wav'
    # audio = AudioSegment.from_file(audio_path, format="wav")
    # duration_ms = len(audio)
    # duration_seconds = duration_ms / 1000
    audio = File(audio_path)
    duration_seconds=audio.info.length
    print("Duration of the audio:", duration_seconds, "seconds")
    image = Image.open(image_path)
    image_np = np.array(image)
    image_clip = ImageClip(image_np)
    video = image_clip.set_duration(duration_seconds).set_fps(24)
    outputvideo_path = 'output_video.mp4'
    video.write_videofile(outputvideo_path, codec='libx264', fps=24)
    print("Video creation completed.")
    video_clip = VideoFileClip(outputvideo_path)
    audio_clip = AudioFileClip(output_file)
    video_clip = video_clip.set_audio(audio_clip)
    outputvideoaudio_path = 'output_video_with_audio'+str(index)+'.mp4'
    st.write(outputvideoaudio_path)
    video_clip.write_videofile(outputvideoaudio_path, codec='libx264', audio_codec='aac')
    print("Video with audio merged successfully.")
    video = VideoFileClip(outputvideoaudio_path)
    video_audio.append(outputvideoaudio_path)
    subtitles = pysrt.open(subtitle)
    begin, end = outputvideoaudio_path.split(".mp4")
    output_video_file = begin + '_subtitling'+str(index)+ ".mp4"
    print("Output file name: ", output_video_file)
    subtitle_clips = create_subtitle_clips(subtitles, video.size)
    final_video = CompositeVideoClip([video] + subtitle_clips)
    final_video.write_videofile(output_video_file)
    return output_video_file

def sub_video(subtitle_path,outputvideoaudio_path,index):
    video = VideoFileClip(outputvideoaudio_path)
    video_audio.append(outputvideoaudio_path)
    subtitles = pysrt.open(subtitle_path)
    begin, end = outputvideoaudio_path.split(".mp4")
    output_video_file = begin + '_corrected_subtitling'+str(index)+ ".mp4"
    print("Output file name: ", output_video_file)
    subtitle_clips = create_subtitle_clips(subtitles, video.size)
    final_video = CompositeVideoClip([video] + subtitle_clips)
    final_video.write_videofile(output_video_file)
    return output_video_file


def path_image_create(file_paths):
        result=""
        i=1
        for file_path in file_paths:
            result+='Page '+str(i) +' : '+text_generation(file_path)+' \n'
            i+=1
        result_text=sequence_text(result)
        
        result_=clean(result_text)
     
        video_files = []
        index=1
        for image,text in zip(file_paths,result_):
            video_file =getvideofromimage(image,text,index)
            video_files.append(video_file)
            index+=1
        
        video_clips = [VideoFileClip(video_file) for video_file in video_files]
        final_video = concatenate_videoclips(video_clips,method="compose")
        final_video_path = "final_output_video.mp4"
        final_video.write_videofile(final_video_path, codec='libx264', audio_codec='aac')
        st.video(final_video_path)

        return result_text

def main():
    uploaded_files = st.file_uploader("Choose images", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
    if uploaded_files:
        st.write("Uploaded Files:")
        
        file_paths = save_uploaded_files(uploaded_files)
        result_text=""
        if st.button("Submit"):
            result_text=path_image_create(file_paths)
            st.write(result_text)

        st.sidebar.title("Changes Form")

        step = st.sidebar.text_input("write a steps in the video")

        changes = st.sidebar.text_input("Changes in video")

        result_text = st.sidebar.text_input("Result Text")

        if st.sidebar.button("Submit",key='sidebutton'):
            res=retext(step,changes,result_text)
            result_=clean(res)
            video_files = []
            index=20
            for image,text in zip(file_paths,result_):
                video_file =getvideofromimage(image,text,index)
                video_files.append(video_file)
                index+=1
            print(video_files)
            video_clips = [VideoFileClip(video_file) for video_file in video_files]
            final_video = concatenate_videoclips(video_clips,method="compose")
            final_video_path = "final_output_video2.mp4"
            final_video.write_videofile(final_video_path, codec='libx264', audio_codec='aac')
            st.video(final_video_path)
            st.write(result_)

        Fix = st.sidebar.text_input("Fix the Spelling")
        if st.sidebar.button("Submit",key='sidebutton2'):
            title=['subtitles1.srt','subtitles2.srt','subtitles3.srt']
            i=1
            sub_paths=[]
            sub_video_paths=[]
            for path in title:  
                sub_paths.append(srtrecreate(path,Fix,i))
                i+=1
            print(sub_paths)
            video_paths=["output_video_with_audio1.mp4","output_video_with_audio2.mp4","output_video_with_audio3.mp4"]
            for i in range(min(len(video_paths),len(sub_paths))):
                sub_video_paths.append(sub_video(sub_paths[i],video_paths[i],i))
            print(video_paths)
            
            video_clips = [VideoFileClip(video_file) for video_file in sub_video_paths]
            final_video = concatenate_videoclips(video_clips,method="compose")
            final_video_path = "final_video_subtitle.mp4"
            final_video.write_videofile(final_video_path, codec='libx264', audio_codec='aac')
            st.video(final_video_path)

            

if __name__ == '__main__':
    main()
