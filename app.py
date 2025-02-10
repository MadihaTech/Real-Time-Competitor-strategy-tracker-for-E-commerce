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
API_KEY = st.secrets.get("api_keys", {}).get("GROQ_API_KEY", None)

if API_KEY:
    st.write("API Key Loaded: True")  # Debugging confirmation
else:
    st.error("⚠ Groq API Key not found! Please check Streamlit secrets configuration.")
    st.stop()  # Stop execution if API key is missing

# ✅ Function to generate response using OpenAI API
def generate_response(user_input):
    if not API_KEY:
        st.error("⚠ Groq API Key is missing! Please check Streamlit secrets.")
        return "Error: API Key is missing."
 # ✅ Prepare API request
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama3-8b-8192",  # ✅ Use a Groq-supported model
        "messages": [{"role": "user", "content": user_input}],
        "temperature": 0.7
    }

    try:
        # ✅ Send API request
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response_json = response.json()

        # ✅ Extract response
        if "choices" in response_json and response_json["choices"]:
            return response_json["choices"][0]["message"]["content"]
        else:
            return f"Error: Groq API response was empty. Response: {response_json}"

    except requests.exceptions.RequestException as e:
        return f"Error: Request to Groq API failed: {e}"
# ✅ Debugging Test
st.write("✅ Groq API Ready to Use")

# ✅ Streamlit User Interface
st.title("Competitor Strategy Tracker")  # App Title

# ✅ Input box for user query
user_query = st.text_input("Enter your query:")

# ✅ Button to trigger AI response
if st.button("Get Insights"):
    if not API_KEY:
        st.error("⚠ Groq API Key is missing! Please check Streamlit secrets.")
    elif not user_query.strip():  # Prevent empty or whitespace queries
        st.warning("⚠ Please enter a valid query!")  
    else:
        result = generate_response(user_query)  # Call Groq API function
        st.text_area("AI Response", result, height=200)  # Display AI response


# ✅ Constants for API keys and Slack webhook
API_KEY = st.secrets.get("api_keys", {}).get("GROQ_API_KEY", None)  # ✅ Use Groq API Key

if not API_KEY:
    st.error("⚠ Groq API Key Not Found! Please check Streamlit secrets.")
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

from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk

# ✅ Download necessary data for Vader (Only required once)
nltk.download('vader_lexicon')

def analyze_sentiment(reviews):
    """Perform sentiment analysis using Vader."""
    analyzer = SentimentIntensityAnalyzer()
    
    # Ensure reviews is a list and not empty
    if not isinstance(reviews, list) or len(reviews) == 0:
        return "No reviews available"

    sentiment_results = []
    for review in reviews:
        score = analyzer.polarity_scores(review)  # Get sentiment scores
        if score['compound'] >= 0.05:
            sentiment_results.append("Positive")
        elif score['compound'] <= -0.05:
            sentiment_results.append("Negative")
        else:
            sentiment_results.append("Neutral")

    return sentiment_results

def train_predictive_model(data):
    """Train a predictive model to estimate competitor discount strategies."""
    
    if data.empty:
        st.error("⚠ Error: Competitor data is empty. Cannot train model.")
        return None, None  # Prevents crash

    # ✅ Convert discount & price to numeric safely
    data["discount"] = pd.to_numeric(data["discount"].str.replace("%", "", regex=True), errors="coerce").fillna(0)
    data["price"] = pd.to_numeric(data["price"], errors="coerce").fillna(0).astype(int)

    # ✅ Ensure required columns exist
    required_cols = ["price", "discount"]
    missing_cols = [col for col in required_cols if col not in data.columns]
    if missing_cols:
        st.error(f"⚠ Error: Missing required columns: {missing_cols}")
        return None, None  # Prevent crashes

    # ✅ Prepare features and target variable
    X = data[required_cols]
    y = data["discount"] + (data["price"] * 0.05).round(2)  # Define target variable

    # ✅ Split data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # ✅ Train a Random Forest Regressor
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # ✅ Make predictions
    data["Predicted_Discount"] = model.predict(X)  # Store predictions in DataFrame
    return model, data  # Return both model and predictions


def forecast_discounts_arima(data, future_days=5):
    """Forecast future discount values using ARIMA model."""
    
    # ✅ Check if data is empty
    if data.empty:
        st.error("⚠ Error: Competitor data is empty. Cannot perform ARIMA forecasting.")
        return pd.DataFrame(columns=["Date", "Predicted_Discount"]).set_index("Date")

    # ✅ Ensure data is sorted by date
    data = data.sort_index()

    # ✅ Convert discount column to numeric, handling errors
    data["discount"] = pd.to_numeric(data["discount"], errors="coerce")

    # ✅ Drop missing discount values
    discount_series = data["discount"].dropna()

    # ✅ Check if enough data exists for forecasting
    if len(discount_series) < 5:
        st.warning("⚠ Warning: Not enough historical data for ARIMA forecasting.")
        return pd.DataFrame(columns=["Date", "Predicted_Discount"]).set_index("Date")

    # ✅ Convert index to datetime if not already
    if not isinstance(data.index, pd.DatetimeIndex):
        data.index = pd.to_datetime(data.index)

    # ✅ Fit ARIMA model
    try:
        model = ARIMA(discount_series, order=(2, 1, 0))  # Order can be tuned
        model_fit = model.fit()
    except Exception as e:
        st.error(f"⚠ Error fitting ARIMA model: {e}")
        return pd.DataFrame(columns=["Date", "Predicted_Discount"]).set_index("Date")

    # ✅ Forecast future values
    forecast = model_fit.forecast(steps=future_days)
    future_dates = pd.date_range(start=discount_series.index[-1] + pd.Timedelta(days=1), periods=future_days)

    # ✅ Create a DataFrame for forecasted values
    forecast_df = pd.DataFrame({"Date": future_dates, "Predicted_Discount": forecast})
    forecast_df.set_index("Date", inplace=True)

    return forecast_df

def send_to_slack(data):
    """Send generated data to a Slack channel with error handling."""
    if not SLACK_WEBHOOK:
        st.error("⚠️ Slack Webhook URL is missing. Please check your configuration.")
        return

    payload = {"text": data}
    
    try:
        response = requests.post(
            SLACK_WEBHOOK,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=10  # ✅ Prevents infinite wait if Slack is unresponsive
        )
        
        if response.status_code == 200:
            st.success("✅ Recommendations sent to Slack successfully!")
        else:
            st.error(f"⚠️ Slack API Error: {response.status_code} - {response.text}")
    
    except requests.exceptions.RequestException as e:
        st.error(f"⚠️ Network error while sending to Slack: {e}")


import requests
import json
import streamlit as st

def generate_strategy_recommendation(api_key, competitor_data, sentiment_output):
    """Generate strategic recommendations using Groq API."""
    
    if not api_key:
        return "Error: Groq API Key is missing. Please update Streamlit secrets."

    if competitor_data.empty or sentiment_output is None:
        return "Error: Missing competitor data or sentiment analysis."
    
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

    Provide recommendations in:
    1. **Pricing Strategy**
    2. **Promotional Campaign Ideas**
    3. **Customer Satisfaction Improvements**
    """

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama3-8b-8192",  # ✅ Ensure this model is supported by Groq API
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data), timeout=10)
        
        # ✅ Check if request was successful
        if response.status_code != 200:
            return f"Error: Groq API returned {response.status_code} - {response.text}"

        response_json = response.json()
        
        # ✅ Validate response structure
        if "choices" in response_json and response_json["choices"]:
            return response_json["choices"][0]["message"]["content"]
        else:
            return f"Error: Groq API response was empty. Response: {response_json}"

    except requests.exceptions.Timeout:
        return "Error: Request to Groq API timed out. Please try again."

    except requests.exceptions.RequestException as e:
        return f"Error: Request to Groq API failed: {e}"

    except json.JSONDecodeError:
        return "Error: Failed to decode Groq API response. It may not be in JSON format."

    except Exception as e:
        return f"Error processing API response: {str(e)}"

# ✅ Ensure API Key is available before proceeding
API_KEY = st.secrets.get("api_keys", {}).get("GROQ_API_KEY", None)

if not API_KEY:
    st.error("⚠️ Groq API Key Not Found! Please check Streamlit secrets.")
    st.stop()  # Stops execution if API key is missing

# ✅ Debugging: Check if competitor data & sentiments are valid
if competitor_data_filtered.empty or sentiments is None:
    st.error("⚠️ Missing competitor data or sentiment analysis. Unable to generate recommendations.")
else:
    try:
        recommendations = generate_strategy_recommendation(API_KEY, competitor_data_filtered, sentiments)

        if "Error" in recommendations:
            st.error(f"⚠️ {recommendations}")  # Display API error messages properly
        else:
            st.subheader("Strategic Recommendations")
            st.write(recommendations)

    except NameError:
        st.error("⚠️ Function `generate_strategy_recommendation` is not defined. Please check your code.")

    except Exception as e:
        st.error(f"⚠️ Unexpected error: {str(e)}")

# ✅ Streamlit UI Configuration
st.title("E-Commerce Competitor Dashboard")
st.sidebar.header("Select a Product")

# ✅ Load competitor data with error handling
try:
    competitor_data = load_and_preprocess_data("competitor_data.csv", drop_na_columns=["date", "discount"])

    if competitor_data.empty or "title" not in competitor_data.columns:
        st.error("⚠️ Competitor data is empty or missing the 'title' column.")
        products = []
    else:
        products = competitor_data["title"].dropna().unique().tolist()

except FileNotFoundError:
    st.error("⚠️ File 'competitor_data.csv' not found. Please upload the correct file.")
    competitor_data = pd.DataFrame()
    products = []

# ✅ Sidebar: Handle case when no products are available
if not products:
    st.warning("⚠️ No products available for analysis. Please check the data file.")
    selected_product = None
else:
    selected_product = st.sidebar.selectbox("Choose a product to analyze:", products)

# ✅ Ensure `selected_product` is valid before filtering
if selected_product:
    competitor_data_filtered = competitor_data[competitor_data["title"] == selected_product]
else:
    competitor_data_filtered = pd.DataFrame()

# ✅ Debugging: Ensure data is loaded
st.write("Debug: Competitor Data Before Forecasting", competitor_data_filtered)
if competitor_data_filtered.empty and selected_product:
    st.error(f"⚠️ No competitor data available for '{selected_product}'! Please check data loading.")

st.write("Competitor CSV Preview:", competitor_data.head())  # Debug competitor data

# ✅ Load reviews data safely
try:
    reviews_data = load_and_preprocess_data("reviews.csv")
    if reviews_data.empty or "title" not in reviews_data.columns:
        st.warning("⚠️ Reviews data is empty or missing 'title' column.")
        reviews_data = pd.DataFrame()  # Set as empty to prevent further errors
except FileNotFoundError:
    st.error("⚠️ File 'reviews.csv' not found. Please upload the correct file.")
    reviews_data = pd.DataFrame()

# ✅ Display competitor analysis only if product is selected
if selected_product:
    st.header(f"Competitor Analysis for {selected_product}")
    st.subheader("Competitor Data")
    st.table(competitor_data_filtered.tail(5))

    # ✅ Perform sentiment analysis only if product reviews exist
    product_reviews = reviews_data[reviews_data["title"] == selected_product] if not reviews_data.empty else pd.DataFrame()
    
    if not product_reviews.empty and "review_statements" in product_reviews.columns:
        product_reviews["review_statements"] = product_reviews["review_statements"].astype(str).apply(lambda x: truncate_text(x, 512))
    else:
   # ✅ Ensure the 'review_statements' column exists before accessing it
if "review_statements" not in reviews_data.columns:
    st.error("⚠️ Column 'review_statements' missing from reviews.csv! Check data format.")
    reviews = []  # Prevent error by assigning an empty list
else:
    product_reviews = reviews_data[reviews_data["title"] == selected_product]
    
    # ✅ Ensure product_reviews is not empty before extracting reviews
    if not product_reviews.empty:
        reviews = product_reviews["review_statements"].dropna().astype(str).tolist()
    else:
        st.warning(f"⚠️ No reviews available for '{selected_product}'.")
        reviews = []  # Assign empty list to prevent errors

# ✅ Debugging output
st.write(f"Debug: Extracted {len(reviews)} reviews for sentiment analysis")

# ✅ Perform Sentiment Analysis
if reviews:
    sentiments = analyze_sentiment(reviews)
    st.write(f"✅ Successfully analyzed {len(reviews)} reviews.")
else:
    sentiments = None
    st.warning("⚠️ No reviews found for sentiment analysis.")

# ✅ Ensure Sentiment Data Exists
if sentiments:
    sentiment_df = pd.DataFrame(sentiments)  # Convert output to DataFrame
    if "label" in sentiment_df.columns and "score" in sentiment_df.columns:
        st.write("✅ Sentiment Analysis Results:", sentiment_df.head())
    else:
        st.error("⚠️ Sentiment DataFrame is missing required columns.")
else:
    sentiment_df = pd.DataFrame()  # Assign empty DataFrame if no sentiment data

# ✅ Debugging Step
st.write("Debug: Sentiment DataFrame Structure", sentiment_df)


# ✅ Load competitor data with improved error handling
competitor_path = "competitor_data.csv"
try:
    competitor_df = pd.read_csv(competitor_path, dtype=str)  # Ensure all data loads as string
    st.write(f"✅ Successfully loaded {competitor_path}")

    # ✅ Standardize column names (convert to lowercase & strip spaces)
    competitor_df.columns = competitor_df.columns.str.strip().str.lower()

    # ✅ Check if required columns exist
    required_cols = {"date", "predicted_discount"}  # Use lowercase to match standard naming
    missing_cols = required_cols - set(competitor_df.columns)

    if competitor_df.empty or missing_cols:
        st.error(f"⚠️ Competitor DataFrame is empty or missing columns: {missing_cols}")
except FileNotFoundError:
    st.error(f"❌ Error: '{competitor_path}' not found. Please upload the correct file.")
    competitor_df = pd.DataFrame()  # Ensure it's an empty DataFrame

# ✅ Debugging Step: Show data preview
st.write("🔍 Debug: Competitor Data Sample", competitor_df.head())


# ✅ Data Validation: Customer Reviews
st.subheader("🔍 Customer Reviews Data Validation")

if sentiment_df.empty:
    st.warning("⚠️ Reviews DataFrame is empty! Please check the source file.")
else:
    st.write("✅ First few rows of the reviews dataframe:")
    st.write(sentiment_df.head())

    st.write("✅ Reviews DataFrame columns:", sentiment_df.columns.tolist())

    # ✅ Check for missing values
    missing_reviews = sentiment_df.isnull().sum()
    st.write("🔍 Missing values in Reviews DataFrame:", missing_reviews[missing_reviews > 0])

# ✅ Data Validation: Competitor Data
st.subheader("🔍 Competitor Data Validation")

if competitor_df.empty:
    st.warning("⚠️ Competitor DataFrame is empty! Please check the source file.")
else:
    st.write("✅ First few rows of the competitor dataframe:")
    st.write(competitor_df.head())

    st.write("✅ Competitor DataFrame columns:", competitor_df.columns.tolist())

    # ✅ Check for missing values
    missing_competitor = competitor_df.isnull().sum()
    st.write("🔍 Missing values in Competitor DataFrame:", missing_competitor[missing_competitor > 0])

# ✅ Sentiment Analysis Visualization
st.subheader("📊 Sentiment Analysis Results")

if not sentiment_df.empty and {'label', 'count'}.issubset(sentiment_df.columns):
    if sentiment_df['count'].sum() > 0:  # Ensure there's data to display
        fig = px.bar(sentiment_df, x="label", y="count", title="Sentiment Analysis Results")
        st.plotly_chart(fig)
    else:
        st.warning("⚠️ No sentiment data to display.")
else:
    st.error("❌ Reviews DataFrame is empty or missing required columns.")

# ✅ Competitor Discounts Visualization
st.subheader("📉 Competitor Discounts Analysis")

# Ensure 'date' column is correctly formatted
if "date" in competitor_df.columns:
    competitor_df["date"] = pd.to_datetime(competitor_df["date"], errors="coerce")

if not competitor_df.empty and {'date', 'Predicted_Discount'}.issubset(competitor_df.columns):
    if competitor_df['Predicted_Discount'].notna().sum() > 0:  # Ensure there's valid discount data
        fig2 = px.line(competitor_df, x="date", y="Predicted_Discount", title="Competitor Current and Predicted Discounts")
        st.plotly_chart(fig2)
    else:
        st.warning("⚠️ No valid discount predictions available.")
else:
    st.error("❌ Competitor DataFrame is empty or missing required columns.")


def get_strategic_recommendations(api_key, competitor_data, sentiment_output):
    """Generate strategic recommendations using the Groq API."""
    if competitor_data.empty or sentiment_output is None:
        return "Error: Missing competitor data or sentiment analysis."

    # ✅ Define the prompt **outside** the if-block
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

    # ✅ Ensure proper indentation for API request
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama3-8b-8192",  # ✅ Use Groq-supported model
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response_json = response.json()
        
        if "choices" in response_json and response_json["choices"]:
            return response_json["choices"][0]["message"]["content"]
        else:
            return f"Error: Groq API response was empty. Response: {response_json}"
    
    except requests.exceptions.RequestException as e:
        return f"Error: Request to Groq API failed: {e}"

# ✅ Ensure API Key is available before proceeding
API_KEY = st.secrets.get("api_keys", {}).get("GROQ_API_KEY", None)  # ✅ Safe access

if API_KEY is None:
    st.error("⚠️ Groq API Key Not Found! Please check Streamlit secrets.")
    st.stop()

# ✅ Prevent crash if sentiment analysis failed
if sentiments is None:
    st.error("⚠️ Sentiment analysis failed. No recommendations can be generated.")
    sentiments = []  # Ensure it's an empty list

# ✅ Generate strategic recommendations
recommendations = get_strategic_recommendations(API_KEY, competitor_data_filtered, sentiments)

# ✅ Display recommendations
st.subheader("Strategic Recommendations")
st.write(recommendations)

# ✅ Streamlit code to render sentiment analysis
st.subheader("Customer Sentiment Analysis")

# ✅ Ensure DataFrame creation is safe
if isinstance(sentiments, list) and sentiments:
    sentiment_df = pd.DataFrame(sentiments)  # Convert to DataFrame safely
else:
    sentiment_df = pd.DataFrame(columns=["label", "count"])  # Prevent crash

# ✅ Check if DataFrame is valid before plotting
if not sentiment_df.empty and 'label' in sentiment_df.columns and 'count' in sentiment_df.columns:
    fig = px.bar(sentiment_df, x="label", y="count", title="Sentiment Analysis Results")
    st.plotly_chart(fig)
else:
    st.write("⚠️ No reviews available for this product.")


# ✅ Convert "date" column safely & drop NaN values
competitor_data_filtered["date"] = pd.to_datetime(competitor_data_filtered["date"], errors="coerce")
competitor_data_filtered = competitor_data_filtered.dropna(subset=["date"])  # Drop NaN dates
competitor_data_filtered.set_index("date", inplace=True)

# ✅ Ensure Data is Not Empty Before Forecasting
if competitor_data_filtered.empty:
    st.error("⚠️ Competitor data is empty. ARIMA forecasting cannot be performed.")
    competitor_data_with_predictions = pd.DataFrame()  # Prevent crash
else:
    try:
        competitor_data_with_predictions = forecast_discounts_arima(competitor_data_filtered)
        st.write("Debug: ARIMA Predictions", competitor_data_with_predictions)
    except Exception as e:
        st.error(f"⚠️ Error in ARIMA Forecasting: {str(e)}")
        competitor_data_with_predictions = pd.DataFrame()  # Prevent crash

# ✅ Display Competitor Discounts
st.subheader("Competitor Current and Predicted Discounts")
if competitor_data_with_predictions.empty:
    st.write("⚠️ No forecast data available.")
else:
    st.table(competitor_data_with_predictions.tail(10))

# ✅ Handle Empty Sentiment Values Before Using Them
if sentiments is None or not sentiments:
    sentiment_output = "No sentiment data available"
else:
    sentiment_output = sentiments

# ✅ Debugging: Print values before passing to function
st.write("Debug: Selected Product", selected_product)
st.write("Debug: Competitor Data", competitor_data_with_predictions)
st.write("Debug: Sentiment Output", sentiment_output)  # Now defined before printing

# ✅ Validate Inputs Before Generating Recommendations
if not selected_product:
    st.error("⚠️ No product selected! Please choose a product.")
    recommendations = "No recommendations available."
elif competitor_data_with_predictions.empty:
    st.error("⚠️ No competitor data available! Unable to generate recommendations.")
    recommendations = "No recommendations available."
elif not sentiment_output or sentiment_output == "No sentiment data available":
    st.warning("⚠️ No sentiment data available. Generating recommendations without sentiment insights.")
    sentiment_output = "No sentiment insights available."

# ✅ Generate Strategic Recommendations
try:
    recommendations = generate_strategy_recommendation(
        selected_product,
        competitor_data_with_predictions,
        sentiment_output
    )
    st.write("Debug: Generated Recommendations", recommendations)  # Print output before display
except Exception as e:
    recommendations = f"⚠️ Error generating recommendations: {str(e)}"
    st.error(recommendations)

# ✅ Display Recommendations
st.subheader("Strategic Recommendations")
if not recommendations or "Error" in recommendations:
    st.write("⚠️ No valid recommendations generated.")
else:
    st.write(recommendations)

# ✅ Send Recommendations to Slack (Only if Valid)
if recommendations and "Error" not in recommendations and recommendations != "No recommendations available.":
    try:
        send_to_slack(recommendations)
        st.success("✅ Recommendations sent to Slack successfully!")
    except Exception as e:
        st.error(f"⚠️ Failed to send to Slack: {str(e)}")
