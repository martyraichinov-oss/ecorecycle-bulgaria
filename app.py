import streamlit as st
import google.generativeai as genai
from PIL import Image
import os

# Configuration
st.set_page_config(
    page_title="EcoRecycle Bulgaria",
    page_icon="♻️",
    layout="centered"
)

# 1. Header & Mission
st.title("♻️ EcoRecycle Bulgaria")
st.subheader("Да направим България по-чиста заедно!")
st.markdown("""
Добре дошли в първата стъпка към правилното рециклиране. 
Това приложение ви помага да разберете дали пластмасовата опаковка в ръцете ви е подходяща за **жълтия контейнер** на Екопак.
""")

# 2. Initialize Gemini API
def init_gemini():
    """Initialize Gemini API with the configured API key."""
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        return False, "API key not configured"
    try:
        genai.configure(api_key=gemini_api_key)
        return True, "API configured successfully"
    except Exception as e:
        return False, f"Failed to configure API: {str(e)}"

# 3. Get available models with generateContent support
@st.cache_resource
def get_supported_models():
    """
    Retrieve all available models that support generateContent.
    Returns a list of model names.
    """
    try:
        success, msg = init_gemini()
        if not success:
            return [], msg
        
        available_models = []
        try:
            models = genai.list_models()
            for model in models:
                if "generateContent" in model.supported_generation_methods:
                    available_models.append(model.name)
        except Exception as e:
            return [], f"Error listing models: {str(e)}"
        
        return available_models, None
    except Exception as e:
        return [], f"Error in get_supported_models: {str(e)}"

# 4. Select best model dynamically
def select_best_model(available_models):
    """
    Select the best model from available models.
    Prioritizes models containing 'flash' or 'pro' in their name.
    """
    if not available_models:
        return None, "No available models"
    
    # First, try to find a model with 'flash' in the name
    for model in available_models:
        if "flash" in model.lower():
            return model, None
    
    # If no flash model, try to find one with 'pro' in the name
    for model in available_models:
        if "pro" in model.lower():
            return model, None
    
    # If neither, just use the first available model
    return available_models[0], None

# 5. Extract recycling code using Gemini
def extract_recycling_code_gemini(image, selected_model):
    """
    Uses Google Gemini Vision API to extract the recycling code from an image.
    Uses the dynamically selected model.
    """
    try:
        if not selected_model:
            st.error("No model available for processing")
            return "UNKNOWN"
        
        # Initialize model
        model = genai.GenerativeModel(selected_model)
        
        # Convert PIL Image to bytes for Gemini
        from io import BytesIO
        img_byte_arr = BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()

        image_parts = [
            {
                "mime_type": "image/png",
                "data": img_byte_arr
            }
        ]

        prompt_parts = [
            image_parts[0],
            "Analyze this image. Find the plastic recycling symbol (the triangle with arrows). Extract ONLY the number inside the triangle (from 1 to 7). If you find a valid number, return ONLY that number as an integer. If you cannot see a recycling triangle, or if it's unreadable, return the word 'UNKNOWN'."
        ]

        response = model.generate_content(prompt_parts)
        
        # Extract the text response and try to convert to integer
        extracted_text = response.text.strip()
        if extracted_text.isdigit():
            code = int(extracted_text)
            if 1 <= code <= 7:
                return code
            else:
                return "UNKNOWN"
        else:
            return "UNKNOWN"

    except Exception as e:
        error_msg = f"Error processing image with model '{selected_model}': {str(e)}"
        st.error(error_msg)
        return "UNKNOWN"

# 6. Bulgarian Logic Mapping
RECYCLING_RULES = {
    1: {"name": "PET", "status": "success", "msg": "Рециклира се! Изхвърлете в ЖЪЛТИЯ контейнер."},
    2: {"name": "HDPE", "status": "success", "msg": "Рециклира се! Изхвърлете в ЖЪЛТИЯ контейнер."},
    4: {"name": "LDPE", "status": "success", "msg": "Рециклира се! Изхвърлете в ЖЪЛТИЯ контейнер."},
    5: {"name": "PP", "status": "success", "msg": "Рециклира се! Изхвърлете в ЖЪЛТИЯ контейнер."},
    3: {"name": "PVC", "status": "error", "msg": "Не се хвърля в жълтия контейнер! Опасно за рециклиране или изисква специализиран пункт. Изхвърлете в ОБЩИЯ контейнер."},
    6: {"name": "PS", "status": "error", "msg": "Не се хвърля в жълтия контейнер! Опасно за рециклиране или изисква специализиран пункт. Изхвърлете в ОБЩИЯ контейнер."},
    7: {"name": "OTHER", "status": "error", "msg": "Не се хвърля в жълтия контейнер! Опасно за рециклиране или изисква специализиран пункт. Изхвърлете в ОБЩИЯ контейнер."},
}

# 7. Main Input: Camera & File Uploader
st.divider()
st.write("### Как искате да сканирате етикета?")

# Използваме табове за по-добро потребителско изживяване на мобилни устройства
tab1, tab2 = st.tabs(["📸 Снимане с камера", "📁 Качване от галерия"])

with tab1:
    camera_file = st.camera_input("Насочете камерата към символа за рециклиране")

with tab2:
    uploaded_file = st.file_uploader(
        "Изберете снимка от устройството си", 
        type=["jpg", "jpeg", "png"],
        help="Търсете триъгълника със стрелки и цифра вътре."
    )

# Определяме кой файл да обработим
image_to_process = camera_file if camera_file is not None else uploaded_file

if image_to_process is not None:
    # Зареждаме снимката
    image = Image.open(image_to_process)
    
    # Ако идва от галерията, я показваме (камерата си има собствено превю)
    if uploaded_file is not None:
         st.image(image, caption='Качена снимка', use_container_width=True)
    
    available_models, error = get_supported_models()
    selected_model, selection_error = select_best_model(available_models)
    
    if selection_error or not selected_model:
        st.error(f"Временен проблем със сървъра. Моля, опитайте по-късно.")
    else:
        with st.spinner('Анализиране на етикета чрез AI...'):
            code = extract_recycling_code_gemini(image, selected_model)
            
            # UI Output
            if code != "UNKNOWN":
                rule = RECYCLING_RULES.get(code)
                
                st.write(f"### Резултат от сканирането: **Код {code} ({rule['name']})**")
                
                if rule["status"] == "success":
                    st.success(rule["msg"])
                else:
                    st.error(rule["msg"])
            else:
                st.warning("Не успяхме да разчетем кода. Моля, уверете се, че символът е добре осветен и на фокус.")

st.divider()
st.info("💡 **Знаете ли че?** Рециклирането на един тон пластмаса спестява енергията, необходима на две домакинства за цяла година.")
