# -*- coding: utf-8 -*-
"""app

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1sj3HNpaVDW7MPfj2IAbZ0cScRlkOcMdh
"""
import streamlit as st
import openai

st.set_page_config(page_title="E-Commerce Competitor Strategy Dashboard", layout="wide")

# Retrieve API key from Streamlit Secrets
API_KEY = st.secrets["api_keys"]["OPENAI_API_KEY"]
openai.api_key = API_KEY  # Set API key for OpenAI

# Function to generate response using OpenAI API
def generate_response(user_input):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",  # Or "gpt-3.5-turbo" if you prefer
            messages=[{"role": "user", "content": user_input}]
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        st.error(f"⚠️ OpenAI API Error: {e}")  # Print the exact error
        return f"Error: {str(e)}"

# ✅ Streamlit User Interface
st.title("Competitor Strategy Tracker")  # App Title

# ✅ Input box for user query
user_query = st.text_input("Enter your query:")

# ✅ Button to trigger AI response
if st.button("Get Insights"):
    if user_query:  # Ensure input is not empty
        result = generate_response(user_query)  # Call OpenAI function
        st.write(result)  # Display result
    else:
        st.warning("Please enter a query first!")  # Show warning if input is empty

import json
from datetime import datetime
import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from openai import AzureOpenAI
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from statsmodels.tsa.arima.model import ARIMA
from transformers import pipeline

# Constants for API keys and Slack webhook
API_KEY = ""  # Groq API Key
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
from transformers import pipeline
def analyze_sentiment(reviews):
    try:
       sentiment_pipeline = pipeline("sentiment-analysis", model="nlptown/bert-base-multilingual-uncased-sentiment")
       return sentiment_pipeline(reviews)  
    except Exception as e:
       print("Error loading sentiment model:", e)
       sentiment_pipeline = None  # Prevents app crash
       return None

def train_predictive_model(data):
    """Train a predictive model to estimate competitor discount strategies."""
    # Convert discount to numeric and preprocess price
    data["discount"] = data["discount"].str.replace("%", "").astype(float)
    data["price"] = data["price"].astype(int)

    # Create a new column for predicted discounts
    data["Predicted_Discount"] = data["discount"] + (data["price"] * 0.05).round(2)

    # Prepare features and target variable
    X = data[["price", "discount"]]
    y = data["Predicted_Discount"]

    # Split data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Train a Random Forest Regressor
    model = RandomForestRegressor(random_state=42)
    model.fit(X_train, y_train)
    return model

def forecast_discounts_arima(data, future_days=5):
    """Forecast future discount values using ARIMA model."""
    data = data.sort_index()  # Ensure data is sorted by date
    data["discount"] = pd.to_numeric(data["discount"], errors="coerce")  # Convert discount to numeric
    data = data.dropna(subset=["discount"])  # Drop rows with missing discounts

    discount_series = data["discount"]
    if discount_series.empty:
        return pd.DataFrame(columns=["Date", "Predicted_Discount"]).set_index("Date")

    if not isinstance(data.index, pd.DatetimeIndex):
        data.index = pd.to_datetime(data.index)  # Convert index to datetime if not already

    # Fit ARIMA model
    model = ARIMA(discount_series, order=(2, 1, 0))
    model_fit = model.fit()

    # Forecast future values
    forecast = model_fit.forecast(steps=future_days)
    future_dates = pd.date_range(
        start=discount_series.index[-1] + pd.Timedelta(days=1), periods=future_days
    )

    # Create a DataFrame for forecasted values
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
    """Generate strategic recommendations using an AI model."""
    date = datetime.now()
    prompt = f"""
    You are a highly skilled business strategist specializing in e-commerce. Based on the following details, suggest:

1. **Product Name**: {title}

2. **Competitor Data**:
{competitor_data}

3. **Sentiment Analysis**:
{sentiment}

4. **Today's Date**: {str(date)}

### Task:
- Analyze competitor data and identify key pricing trends.
- Leverage sentiment analysis insights to highlight areas where customer satisfaction can be improved.
- Use discount predictions to suggest pricing strategies for the next 5 days.
- Recommend promotional campaigns and marketing strategies aligned with customer sentiments.

Provide your recommendations in the following format:
1. **Pricing Strategy**
2. **Promotional Campaign Ideas**
3. **Customer Satisfaction Recommendations**
    """

    data = {
        "messages": [{"role": "user", "content": prompt}],
        "model": "llama3-8b-8192",
        "temperature": 0,
    }

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}

    res = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(data),
        headers=headers,
    )

    res = res.json()
    if "choices" in res and res["choices"]:
        return res["choices"][0]["message"]["content"]
    else:
        return "Error: Unable to generate recommendations. Please check the API key and response."

# Streamlit UI Configuration
st.title("E-Commerce Competitor Dashboard")
st.sidebar.header("Select a Product")

# Load competitor data and list product names
competitor_data = load_and_preprocess_data("competitor_data.csv", drop_na_columns=["date", "discount"])
products = competitor_data["title"].unique().tolist()

# Sidebar for selecting a product
selected_product = st.sidebar.selectbox("Choose a product to analyze:", products)

# Filter data for selected product
competitor_data_filtered = competitor_data[competitor_data["title"] == selected_product]
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
    sentiments = analyze_sentiment(reviews)
# Data Validation Checks (Insert at line 220)
# Check the first few rows of the dataframe to verify the data
print(sentiment_df.head())

# Check the columns to verify the structure
print(sentiment_df.columns)

# Check for missing values in the dataframe
print(sentiment_df.isnull().sum())
# Updated Plotting Code
import plotly.express as px

# Check if the dataframe is not empty and has the required columns
if not sentiment_df.empty and 'label' in sentiment_df.columns and 'count' in sentiment_df.columns:
    fig = px.bar(sentiment_df, x="label", y="count", title="Sentiment Analysis Results")
    fig.show()
else:
    print("DataFrame is empty or missing required columns.")
    st.write("No reviews available for this product.")

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
competitor_data_with_predictions = forecast_discounts_arima(competitor_data_filtered)

st.subheader("Competitor Current and Predicted Discounts")
st.table(competitor_data_with_predictions.tail(10))

# Generate and display strategic recommendations
sentiment_output = sentiments if not product_reviews.empty else "No reviews available"
recommendations = generate_strategy_recommendation(
    selected_product,
    competitor_data_with_predictions,
    sentiment_output
)

st.subheader("Strategic Recommendations")
st.write(recommendations)

# Send recommendations to Slack
send_to_slack(recommendations)
