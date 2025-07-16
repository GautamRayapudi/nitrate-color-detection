import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import os
from datetime import datetime
import json
import re

# Configure page
st.set_page_config(
    page_title="Nitrite Test Kit AI Analysis",
    page_icon="🧪",
    layout="wide"
)

# Initialize session state
if 'predictions' not in st.session_state:
    st.session_state.predictions = []

def setup_gemini(api_key):
    """Setup Gemini API with provided API key"""
    try:
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        st.sidebar.error(f"Invalid API key: {str(e)}")
        return False

def analyze_with_gemini(image, unit="mg/L"):
    """Analyze nitrite test kit image using Gemini"""
    try:
        # Initialize the model
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Create the prompt
        prompt = f"""
        You are an expert at analyzing water test kit results. Please analyze this nitrite test kit image.

        I can see a test tube with colored liquid and a reference color chart. Please:

        1. Identify the test tube in the image (it's usually a clear glass tube with pink/clear liquid)
        2. Compare the color of the liquid in the test tube to the reference color chart shown in the image
        3. Determine which reference color (0.0, 0.5, 1.0, 2.0, 3.0, or 5.0 {unit}) best matches the test tube liquid
        4. Provide a confidence level (0-100%) for your assessment

        Please respond in the following JSON format:
        {{
            "predicted_level": <number>,
            "confidence": <number 0-100>,
            "explanation": "<brief explanation of what you observed>",
            "tube_description": "<description of the test tube liquid color>",
            "matched_reference": "<description of the matching reference color>"
        }}

        Be very precise in your color matching. Look carefully at the liquid inside the test tube and compare it to each reference color block.
        """
        
        # Generate response
        response = model.generate_content([prompt, image])
        
        # Parse JSON response
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result
            else:
                # Fallback parsing if JSON is not properly formatted
                return parse_text_response(response.text)
                
        except json.JSONDecodeError:
            return parse_text_response(response.text)
            
    except Exception as e:
        st.error(f"Error analyzing image: {str(e)}")
        return None

def parse_text_response(text):
    """Parse text response if JSON parsing fails"""
    try:
        # Extract numerical values using regex
        level_match = re.search(r'(?:level|prediction).*?(\d+\.?\d*)', text, re.IGNORECASE)
        confidence_match = re.search(r'confidence.*?(\d+)', text, re.IGNORECASE)
        
        predicted_level = float(level_match.group(1)) if level_match else 1.0
        confidence = float(confidence_match.group(1)) if confidence_match else 50.0
        
        return {
            "predicted_level": predicted_level,
            "confidence": confidence,
            "explanation": text[:200] + "..." if len(text) > 200 else text,
            "tube_description": "AI analysis completed",
            "matched_reference": f"Closest match: {predicted_level} mg/L"
        }
    except:
        return {
            "predicted_level": 1.0,
            "confidence": 50.0,
            "explanation": "Could not parse detailed results",
            "tube_description": "Analysis attempted",
            "matched_reference": "Default result"
        }

def save_prediction(level, confidence, unit, explanation=""):
    """Save prediction to CSV file"""
    new_prediction = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'predicted_level': level,
        'confidence': confidence,
        'unit': unit,
        'explanation': explanation
    }
    
    # Add to session state
    st.session_state.predictions.append(new_prediction)
    
    # Save to CSV
    df = pd.DataFrame(st.session_state.predictions)
    df.to_csv('gemini_predictions.csv', index=False)

def main():
    st.title("🧪 AI-Powered Nitrite Test Kit Analysis")
    st.markdown("Upload your test kit image and let AI analyze it instantly!")
    
    # Sidebar for settings
    st.sidebar.header("Settings")
    
    # API Key input
    st.sidebar.subheader("Gemini API Key")
    api_key = st.sidebar.text_input(
        "Enter your Gemini API Key",
        type="password",
        help="Enter your Google Gemini API key to enable AI analysis"
    )
    
    # Validate API key
    api_key_valid = False
    if api_key:
        api_key_valid = setup_gemini(api_key)
    
    unit = st.sidebar.selectbox(
        "Choose unit:",
        ["mg/L", "ppm"],
        index=0
    )
    
    # File upload
    uploaded_file = st.file_uploader(
        "Choose an image...",
        type=['jpg', 'jpeg', 'png'],
        help="Upload an image of your nitrite test kit"
    )
    
    if uploaded_file is not None:
        # Load and display image
        image = Image.open(uploaded_file)
        
        # Create columns for layout
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("📷 Uploaded Image")
            st.image(image, caption="Test Kit Image", use_container_width=True)
        
        with col2:
            st.subheader("🤖 AI Analysis")
            
            # Analyze button
            if st.button("🔍 Analyze with AI", type="primary", disabled=not api_key_valid):
                if not api_key_valid:
                    st.error("Please enter a valid Gemini API key in the sidebar")
                else:
                    with st.spinner("AI is analyzing your test kit..."):
                        result = analyze_with_gemini(image, unit)
                    
                    if result:
                        # Display results
                        st.success("✅ AI Analysis Complete!")
                        
                        # Main result
                        st.markdown(f"""
                        ### 🎯 Predicted Nitrite Level: **{result['predicted_level']} {unit}**
                        **AI Confidence:** {result['confidence']:.1f}%
                        """)
                        
                        # Progress bar for confidence
                        st.progress(result['confidence'] / 100)
                        
                        # Save prediction
                        save_prediction(
                            result['predicted_level'], 
                            result['confidence'], 
                            unit, 
                            result.get('explanation', '')
                        )
                        
                        # Detailed analysis
                        with st.expander("🔍 Detailed AI Analysis"):
                            st.markdown(f"**Test Tube Description:** {result.get('tube_description', 'N/A')}")
                            st.markdown(f"**Matched Reference:** {result.get('matched_reference', 'N/A')}")
                            st.markdown(f"**AI Explanation:** {result.get('explanation', 'N/A')}")
                        
                        # Confidence interpretation
                        confidence = result['confidence']
                        if confidence >= 90:
                            st.success("🎯 Very High Confidence - Excellent match!")
                        elif confidence >= 75:
                            st.info("👍 High Confidence - Good match")
                        elif confidence >= 60:
                            st.warning("⚠️ Moderate Confidence - Consider retaking image")
                        else:
                            st.error("❌ Low Confidence - Please check image quality")
                    
                    else:
                        st.error("❌ Could not analyze the image. Please try again.")
    
    # History section
    st.markdown("---")
    st.subheader("📊 Analysis History")
    
    if st.session_state.predictions:
        df = pd.DataFrame(st.session_state.predictions)
        
        # Display recent predictions
        st.dataframe(df.tail(10), use_container_width=True)
        
        # Simple statistics
        if len(df) > 1:
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("Total Tests", len(df))
            with col_b:
                st.metric("Average Level", f"{df['predicted_level'].mean():.1f} {unit}")
            with col_c:
                st.metric("Average Confidence", f"{df['confidence'].mean():.1f}%")
        
        # Clear history button
        if st.button("🗑️ Clear History"):
            st.session_state.predictions = []
            if os.path.exists('gemini_predictions.csv'):
                os.remove('gemini_predictions.csv')
            st.rerun()
    else:
        st.info("No analyses yet. Upload an image to get started!")
    
    # Information section
    st.markdown("---")
    st.subheader("ℹ️ How AI Analysis Works")
    st.markdown("""
    1. **Upload** your test kit image
    2. **AI Vision** analyzes the entire image using Google's Gemini model
    3. **Recognition** identifies the test tube and reference color chart
    4. **Comparison** matches the test tube liquid color to reference colors
    5. **Results** provides nitrite level with confidence score and explanation
    
    **Advantages of AI Analysis:**
    - 🎯 More accurate color perception than traditional CV
    - 🧠 Understands context and can handle various lighting conditions
    - 📝 Provides detailed explanations of the analysis
    - 🔄 Continuously improving with latest AI models
    """)
    
    # Tips section
    with st.expander("📸 Tips for Best Results"):
        st.markdown("""
        **For optimal AI analysis:**
        - Ensure both test tube and color chart are clearly visible
        - Use good lighting (natural light preferred)
        - Keep the image steady and in focus
        - Include the entire test kit in the frame
        - Avoid shadows covering the test tube or chart
        """)
    
    st.markdown("---")
    st.markdown("**Powered by Google Gemini AI** | For educational purposes only")

if __name__ == "__main__":
    main()