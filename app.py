# -*- coding: utf-8 -*-
"""app

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1sj3HNpaVDW7MPfj2IAbZ0cScRlkOcMdh
"""
import json
from datetime import datetime
import pandas as pd
import plotly.express as px
import requests
import streamlit as st
import openai  
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from statsmodels.tsa.arima.model import ARIMA
from transformers import pipeline

st.set_page_config(page_title="E-Commerce Competitor Strategy Dashboard", layout="wide")

# ✅ Safely Fetch API Key
API_KEY = st.secrets.get("api_keys", {}).get("OPENAI_API_KEY", None)

if API_KEY:
    openai.api_key = API_KEY  # Set OpenAI API key
    st.write("API Key Loaded: True")  # Debugging confirmation
else:
    st.error("⚠ API Key not found! Please check Streamlit secrets configuration.")
    st.stop()  # Stop execution if API key is missing

# ✅ Function to generate response using OpenAI API
def generate_response(user_input):
    if not API_KEY:
        st.error("⚠ OpenAI API Key is missing! Please check Streamlit secrets.")
        return "Error: API Key is missing."

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",  # Or "gpt-3.5-turbo" if needed
            messages=[{"role": "user", "content": user_input}]
        )
        return response["choices"][0]["message"]["content"]

    except openai.error.OpenAIError as e:  # More specific error handling
        st.error(f"⚠ OpenAI API Error: {e}")  
        return "Error: Unable to process request due to API error."

    except Exception as e:
        st.error(f"⚠ Unexpected Error: {e}")  
        return "Error: Something went wrong."


# ✅ Streamlit User Interface
st.title("Competitor Strategy Tracker")  # App Title

# ✅ Input box for user query
user_query = st.text_input("Enter your query:")

# ✅ Button to trigger AI response
if st.button("Get Insights"):
    if not API_KEY:
        st.error("⚠ OpenAI API Key is missing! Please check Streamlit secrets.")
    elif not user_query.strip():  # Prevent empty or whitespace queries
        st.warning("Please enter a valid query!")  
    else:
        result = generate_response(user_query)  # Call OpenAI function
        st.text_area("AI Response", result, height=200)  # Display improved

# Constants for API keys and Slack webhook
API_KEY = st.secrets.get("api_keys", {}).get("OPENAI_API_KEY", None)

if not API_KEY:
    st.error("⚠ API Key Not Found! Please check Streamlit secrets.")
    st.stop()
SLACK_WEBHOOK = "https://hooks.slack.com/services/your/webhook/url"  # Slack webhook URL

def truncate_text(text, max_length=512):
    """Truncate text to a specified maximum length."""
    return text[:max_length]

def load_and_preprocess_data(file_path, drop_na_columns=None):
    """Load and preprocess data from a CSV file."""
    data = pd.read_csv(file_path)
    if drop_na_columns:
        data = data.dropna(subset=drop_na_columns)  # Drop rows with missing values in specified columns
    return data

def analyze_sentiment(reviews):
    """Perform sentiment analysis on customer reviews."""
    try:
        sentiment_pipeline = pipeline("sentiment-analysis", model="nlptown/bert-base-multilingual-uncased-sentiment")
        return sentiment_pipeline(reviews)  
    except Exception as e:
        st.error(f"⚠ Error loading sentiment model: {e}")
        return None  # Return None to prevent crashes

def train_predictive_model(data):
    """Train a predictive model to estimate competitor discount strategies."""

    # ✅ Convert discount & price to numeric safely
    data["discount"] = pd.to_numeric(data["discount"].str.replace("%", "", regex=True), errors="coerce").fillna(0)
    data["price"] = pd.to_numeric(data["price"], errors="coerce").fillna(0).astype(int)

    # ✅ Ensure required columns exist
    required_cols = ["price", "discount"]
    for col in required_cols:
        if col not in data.columns:
            st.error(f"⚠ Missing required column: {col}")
            return None  # Prevent crashes

    # Prepare features and target variable
    X = data[required_cols]
    y = data["discount"] + (data["price"] * 0.05).round(2)  # Define target variable

    # Split data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # ✅ Train a Random Forest Regressor
    model = RandomForestRegressor(random_state=42)
    model.fit(X_train, y_train)

    # ✅ Make predictions
    y_pred = model.predict(X)
    data["Predicted_Discount"] = y_pred  # Store predictions in DataFrame

    return model, data  # Return both model and predictions

def forecast_discounts_arima(data, future_days=5):
    """Forecast future discount values using ARIMA model."""

    data = data.sort_index()  # Ensure data is sorted by date
    data["discount"] = pd.to_numeric(data["discount"], errors="coerce")  # Convert discount to numeric
    data = data.dropna(subset=["discount"])  # Drop rows with missing discounts

    discount_series = data["discount"].dropna()

    # ✅ Check if discount_series has enough data for ARIMA
    if len(discount_series) < 5:  # ARIMA needs at least 5 data points
        st.warning("⚠ Not enough data for ARIMA forecasting. Returning empty DataFrame.")
        return pd.DataFrame(columns=["Date", "Predicted_Discount"]).set_index("Date")

    # ✅ Ensure proper DateTime index
    try:
        data.index = pd.to_datetime(data.index, errors="coerce")
        if data.index.isna().sum() > 0:
            st.warning("⚠ Some dates could not be converted. ARIMA might not work correctly.")
    except Exception as e:
        st.error(f"⚠ Error converting dates: {e}")
        return pd.DataFrame(columns=["Date", "Predicted_Discount"]).set_index("Date")

    # ✅ Fit ARIMA model with error handling
    try:
        model = ARIMA(discount_series, order=(2, 1, 0))
        model_fit = model.fit()
    except Exception as e:
        st.error(f"⚠ Error fitting ARIMA model: {e}")
        return pd.DataFrame(columns=["Date", "Predicted_Discount"]).set_index("Date")

    # ✅ Forecast future values
    forecast = model_fit.forecast(steps=future_days)
    future_dates = pd.date_range(
        start=discount_series.index[-1] + pd.Timedelta(days=1), periods=future_days
    )

    # ✅ Create a DataFrame for forecasted values
    forecast_df = pd.DataFrame({"date": future_dates, "Predicted_Discount": forecast})
    forecast_df.set_index("date", inplace=True)

    return forecast_df

def send_to_slack(data):
    """Send generated data to a Slack channel."""
    payload = {"text": data}
    response = requests.post(
        SLACK_WEBHOOK,
        data=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )

def generate_strategy_recommendation(title, competitor_data, sentiment):
    """Generate strategic recommendations using OpenAI API (compatible with openai>=1.0.0)."""
    date = datetime.now()
    prompt = f"""
    You are an expert in e-commerce competitor analysis. Based on the details below, provide strategic recommendations.

    **Product Name:** {title}
    **Competitor Data:** {competitor_data}
    **Sentiment Analysis:** {sentiment}
    **Today's Date:** {date}

    ### Task:
    - Identify key pricing trends.
    - Suggest optimal pricing and promotional strategies.
    - Recommend customer engagement improvements.

    Provide recommendations in the format:
    1. **Pricing Strategy**
    2. **Promotional Campaign Ideas**
    3. **Customer Satisfaction Recommendations**
    """

    # ✅ Updated OpenAI client for `openai>=1.0.0`
    client = openai.OpenAI(api_key=st.secrets["api_keys"]["OPENAI_API_KEY"])

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: Unable to generate recommendations. {str(e)}"

# Streamlit UI Configuration
st.title("E-Commerce Competitor Dashboard")
st.sidebar.header("Select a Product")

# Load competitor data and list product names
try:
    competitor_data = load_and_preprocess_data("competitor_data.csv", drop_na_columns=["date", "discount"])
    
    if competitor_data.empty or "title" not in competitor_data.columns:
        st.error("⚠️ Competitor data is empty or missing the 'title' column.")
        products = []
    else:
        products = competitor_data["title"].dropna().unique().tolist()

except FileNotFoundError:
    st.error("⚠️ File 'competitor_data.csv' not found. Please upload the correct file.")
    competitor_data = pd.DataFrame()  # Ensure it's an empty DataFrame
    products = []


# Sidebar for selecting a product
if not products:
    st.warning("⚠️ No products available for analysis. Please check the data file.")
    selected_product = None
else:
    selected_product = st.sidebar.selectbox("Choose a product to analyze:", products)

# Filter data for selected product
competitor_data_filtered = competitor_data[competitor_data["title"] == selected_product]

# Debugging: Ensure data is loaded
st.write("Debug: Competitor Data Before Forecasting", competitor_data_filtered)
if competitor_data_filtered.empty:
    st.error("Competitor data is empty! Please check data loading.")

st.write("Competitor CSV Preview:", competitor_data.head())  # Debug competitor data
reviews_data = load_and_preprocess_data("reviews.csv")

# Display competitor analysis
st.header(f"Competitor Analysis for {selected_product}")
st.subheader("Competitor Data")
st.table(competitor_data_filtered.tail(5))

# Perform sentiment analysis
product_reviews = reviews_data[reviews_data["title"] == selected_product]
if not product_reviews.empty:
    if "review_statements" in product_reviews.columns:
        product_reviews["review_statements"] = product_reviews["review_statements"].apply(lambda x: truncate_text(str(x), 512))
    else:
        print("Error: 'review_statements' column is missing! Check if the correct CSV file is loaded.")

    reviews = product_reviews["review_statements"].tolist()
# Debugging: Ensure reviews are loading
if "review_statements" not in reviews_data.columns:
    st.error("Column 'review_statements' missing from reviews.csv! Check data format.")

st.write("Debug: Extracted Reviews for Sentiment Analysis", reviews)

# Perform Sentiment Analysis
if reviews:
    sentiments = analyze_sentiment(reviews)
else:
    sentiments = None
    st.error("No reviews found for sentiment analysis.")

# Load customer reviews data
reviews_path = 'reviews.csv'
try:
    sentiment_df = pd.read_csv(reviews_path)
    st.write(f"Successfully loaded {reviews_path}")
    if sentiment_df.empty or 'label' not in sentiment_df.columns or 'count' not in sentiment_df.columns:
        st.write("Reviews DataFrame is empty or missing required columns.")
except FileNotFoundError:
    st.write(f"Error: {reviews_path} file not found. Please check the file path.")
    sentiment_df = pd.DataFrame()

# Load competitor data
competitor_path = 'competitor_data.csv'
try:
    competitor_df = pd.read_csv(competitor_path)
    st.write(f"Successfully loaded {competitor_path}")
    if competitor_df.empty or 'Date' not in competitor_df.columns or 'Predicted_Discount' not in competitor_df.columns:
        st.write("Competitor DataFrame is empty or missing required columns.")
except FileNotFoundError:
    st.write(f"Error: {competitor_path} file not found. Please check the file path.")
    competitor_df = pd.DataFrame()

# Data Validation Checks for customer reviews
st.write("First few rows of the reviews dataframe:")
st.write(sentiment_df.head())

st.write("Reviews DataFrame columns:")
st.write(sentiment_df.columns)

st.write("Reviews Missing values:")
st.write(sentiment_df.isnull().sum())

# Data Validation Checks for competitor data
st.write("First few rows of the competitor dataframe:")
st.write(competitor_df.head())

st.write("Competitor DataFrame columns:")
st.write(competitor_df.columns)

st.write("Competitor Missing values:")
st.write(competitor_df.isnull().sum())

# Check if the reviews dataframe is not empty and has the required columns
if not sentiment_df.empty and 'label' in sentiment_df.columns and 'count' in sentiment_df.columns:
    fig = px.bar(sentiment_df, x="label", y="count", title="Sentiment Analysis Results")
    st.plotly_chart(fig)
else:
    st.write("Reviews DataFrame is empty or missing required columns. No reviews available for this product.")

# Competitor Discounts Display
if not competitor_df.empty and 'Date' in competitor_df.columns and 'Predicted_Discount' in competitor_df.columns:
    fig2 = px.line(competitor_df, x="Date", y="Predicted_Discount", title="Competitor Current and Predicted Discounts")
    st.plotly_chart(fig2)
else:
    st.write("Competitor DataFrame is empty or missing required columns.")

# Function to generate strategic recommendations using OpenAI API
def get_strategic_recommendations(api_key, competitor_data, sentiment_output):
    if competitor_data.empty or sentiment_output is None:
        return "Error: Missing competitor data or sentiment analysis."
    try:
        openai.api_key = api_key  # Set the API key for authentication
 
        prompt = f"""
        You are an expert in e-commerce competitor analysis. Based on the details below, provide strategic recommendations.

        **Competitor Data:**  
        {competitor_data}

        **Sentiment Analysis:**  
        {sentiment_output}

        **Task:**  
        - Identify key pricing trends.
        - Suggest optimal pricing and promotional strategies.
        - Recommend customer engagement improvements.

        Provide the recommendations in:
        1. **Pricing Strategy**
        2. **Promotional Campaign Ideas**
        3. **Customer Satisfaction Improvements**
        """

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", 
            messages=[{"role": "user", "content": prompt}]
        )
        return response["choices"][0]["message"]["content"]
    
    except Exception as e:
        return f"Error: Unable to generate recommendations. {str(e)}"

# Ensure API Key is available before proceeding
try:
    api_key = st.secrets["api_keys"]["OPENAI_API_KEY"]  # ✅ Correct Key Access
    
    # Pass actual data to generate recommendations
    recommendations = get_strategic_recommendations(api_key, competitor_data_filtered, sentiments)

    st.write("Strategic Recommendations")
    st.write(recommendations)
except KeyError:
    st.error("⚠ API Key Not Found! Please check Streamlit secrets.")
    st.stop()

# Streamlit code to render the app
st.subheader("Customer Sentiment Analysis")
sentiment_df = pd.DataFrame(sentiments)

# Check if the dataframe is not empty and has the required columns for Streamlit display
if not sentiment_df.empty and 'label' in sentiment_df.columns and 'count' in sentiment_df.columns:
    fig = px.bar(sentiment_df, x="label", y="count", title="Sentiment Analysis Results")
    st.plotly_chart(fig)
else:
    st.write("No reviews available for this product.")

# Forecast discounts using ARIMA
competitor_data_filtered["date"] = pd.to_datetime(competitor_data_filtered["date"], errors="coerce")
competitor_data_filtered.set_index("date", inplace=True)

# ✅ Handle ARIMA errors gracefully
try:
    competitor_data_with_predictions = forecast_discounts_arima(competitor_data_filtered)
    st.write("Debug: ARIMA Predictions", competitor_data_with_predictions)
except Exception as e:
    st.error(f"Error in ARIMA Forecasting: {str(e)}")
    competitor_data_with_predictions = pd.DataFrame()  # Prevent crash

st.subheader("Competitor Current and Predicted Discounts")
st.table(competitor_data_with_predictions.tail(10))

# ✅ Handle empty sentiment values before using them
sentiment_output = sentiments if not product_reviews.empty else "No sentiment data available"

# Debugging: Print values before passing to the function
st.write("Debug: Selected Product", selected_product)
st.write("Debug: Competitor Data", competitor_data_with_predictions)
st.write("Debug: Sentiment Output", sentiment_output)  # Now defined before printing

# Generate Strategic Recommendations
try:
    recommendations = generate_strategy_recommendation(
        selected_product,
        competitor_data_with_predictions,
        sentiment_output
    )
    st.write("Debug: Generated Recommendations", recommendations)  # Print output before display
except Exception as e:
    recommendations = f"Error generating recommendations: {str(e)}"
    st.error(recommendations)

# Display Recommendations
st.subheader("Strategic Recommendations")
st.write(recommendations)

# Send recommendations to Slack (Only if not empty)
if recommendations and "Error" not in recommendations:
    try:
        send_to_slack(recommendations)
        st.success("Recommendations sent to Slack successfully!")
    except Exception as e:
        st.error(f"Failed to send to Slack: {str(e)}")
