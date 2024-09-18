import streamlit as st
import google.generativeai as genai
import requests
import folium
from streamlit_folium import folium_static
import os, sys
from streamlit_geolocation import streamlit_geolocation

sys.path.insert(0, './')

# Load environment variables
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
GEOAPIFY_API_KEY = st.secrets["GEOAPIFY_API_KEY"]

# Configure Gemini AI
genai.configure(api_key=GEMINI_API_KEY)

# Create the model
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
}
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
)

system_prompt = """
As a highly skilled medical practitioner specializing in image analysis, you are tasked with analyzing medical images for a renowned hospital. Your expertise is crucial in identifying any anomalies, diseases, or health issues that may be present in the images.

Your Responsibilities:
1. Detailed Analysis: Thoroughly examine each image, focusing on identifying any abnormal findings.
2. Findings Report: Document all observed anomalies or signs of disease in a structured format, clearly articulating these findings.
3. Recommendations and Next Steps: Based on your analysis, suggest potential next steps, including further tests or treatments as applicable.
4. Treatment Suggestions: If appropriate, recommend possible treatment options or interventions to address the identified issues.

Important Notes:
1. Scope of Response: Only respond if the image pertains to human health issues.
2. Clarity of Image: If the image quality impedes clear analysis, note that certain aspects are "Unable to determine based on the provided image."
3. Disclaimer: Accompany your analysis with the disclaimer: "Please consult with your doctor before taking any further action."

Your insights are invaluable in guiding clinical decisions. Please proceed with the analysis, adhering to the structured approach outlined above.
"""

def get_nearby_hospitals(lat, lon):
    url = f"https://api.geoapify.com/v2/places?categories=healthcare.hospital&filter=circle:{lon},{lat},5000&limit=5&apiKey={GEOAPIFY_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data['features']
    return []

def create_map(user_lat, user_lon, hospitals):
    m = folium.Map(location=[user_lat, user_lon], zoom_start=13)
    
    # Add user marker
    folium.Marker(
        [user_lat, user_lon],
        popup="Your Location",
        icon=folium.Icon(color="red", icon="home")
    ).add_to(m)
    
    # Add hospital markers
    for hospital in hospitals:
        properties = hospital['properties']
        folium.Marker(
            [properties['lat'], properties['lon']],
            popup=f"<b>{properties['name']}</b><br>{properties['address_line2']}",
            icon=folium.Icon(color="blue", icon="hospital-o", prefix='fa')
        ).add_to(m)
    
    return m

st.set_page_config(
    page_title="MedAssist AI",
    page_icon="🏥",
    layout="wide",
)

st.image("logo.png", width=200)
st.title("Medical AI Assistant")
st.subheader("An AI application Assistant for Healthcare Powered by Gemini AI")

st.write("To enable your location for nearby hospital recommendations, please allow access to your location by clicking this button: ")
location = streamlit_geolocation()
user_lat = location['latitude']
user_lon = location['longitude']
if user_lat is not None and user_lon is not None:
    st.success(f"Location retrieved: {user_lat}, {user_lon}")
else:
    st.error("Unable to retrieve location. Please allow access to your location by clicking the button.")

uploaded_file = st.file_uploader("Upload the medical image for analysis", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.image(uploaded_file, width=300, caption="Uploaded Medical Image")
        submit_button = st.button("Generate the Analysis")

    if submit_button:
        with st.spinner("Analyzing the image..."):
            image_data = uploaded_file.getvalue()
            image_parts = [
                {
                    "mime_type": "image/jpeg",
                    "data": image_data
                },
            ]
            prompt_parts = [
                image_parts[0],
                system_prompt,
            ]

            response = model.generate_content(prompt_parts)
        
        with col2:
            st.subheader("Analysis Results:")
            st.write(response.text)
            st.info("Remember: Always consult with a healthcare professional for accurate diagnosis and treatment.")

        # Get user's location and nearby hospitals
        if user_lat and user_lon:
            nearby_hospitals = get_nearby_hospitals(user_lat, user_lon)
            if nearby_hospitals:
                st.subheader("Nearby Hospitals:")
                
                # Create and display the map
                m = create_map(user_lat, user_lon, nearby_hospitals)
                folium_static(m)
                
                # Display hospital information
                for hospital in nearby_hospitals:
                    properties = hospital['properties']
                    lat = properties.get('lat', None)
                    lon = properties.get('lon', None)
                    google_maps_link = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                    with st.expander(f"{properties['name']}"):
                        st.write(f"Address: {properties['address_line2']}")
                        if 'contact' in properties:
                            contact = properties['contact']
                            if 'phone' in contact:
                                st.write(f"Phone: {contact['phone']}")
                            else:
                                st.write("Phone: Not available")

                            if 'email' in contact:
                                st.write(f"Email: {contact['email']}")
                            else:
                                st.write("Email: Not available")
                        else:
                            st.write("Phone: Not available")
                        
                        if 'contact:website' in properties:
                            st.write(f"Website: {properties['contact:website']}")
                        elif 'website' in properties:
                            st.write(f"Website: {properties['website']}")
                        else:
                            st.write("Website: Not available")
                        st.write(f"[Open in Google Maps]({google_maps_link})")
                
            else:
                st.warning("No nearby hospitals found.")
        else:
            st.error("Unable to retrieve location information for nearby hospital recommendations.")
