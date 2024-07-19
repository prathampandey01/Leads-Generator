import streamlit as st
import spacy
import time
from datetime import datetime
import feedparser
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Load spaCy model
@st.cache_resource
def load_spacy_model():
    return spacy.load("en_core_web_sm")

nlp = load_spacy_model()

# Function to send email using SMTP
def send_email(subject, body, to_email, smtp_server, smtp_port, smtp_user, smtp_password):
    try:
        # Create a multipart message
        message = MIMEMultipart()
        message['From'] = smtp_user
        message['To'] = to_email
        message['Subject'] = subject

        # Attach the email body
        message.attach(MIMEText(body, 'html'))

        # Connect to the SMTP server
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Upgrade the connection to a secure encrypted SSL/TLS connection
            server.login(smtp_user, smtp_password)  # Log in to the SMTP server
            server.send_message(message)  # Send the email

        st.success("Email sent successfully!")
        return True
    except Exception as e:
        st.error(f"Failed to send email: {e}")
        return False

# Function to process content and check for keywords
def process_content(content, keywords):
    doc = nlp(content.lower())
    tokens = [token.lemma_ for token in doc if not token.is_stop]
    return any(keyword in tokens for keyword in keywords)

# Function to generate summary with highlighted keywords
def generate_summary(text, keywords, num_sentences=3):
    doc = nlp(text)
    sentences = [sent.text.strip() for sent in doc.sents]
    summary = " ".join(sentences[:num_sentences])

    # Highlight keywords in summary
    for keyword in keywords:
        pattern = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)
        summary = pattern.sub(f'<span style="background-color: yellow;">{keyword}</span>', summary)

    return summary

# Function to fetch and process RSS feed
def fetch_and_process_rss(url, keywords):
    filtered_articles = []
    feed = feedparser.parse(url)

    for entry in feed.entries:
        title = entry.title
        content = entry.summary if 'summary' in entry else entry.description if 'description' in entry else ""
        link = entry.link

        if process_content(title + " " + content, keywords):
            summary = generate_summary(content, keywords)
            filtered_articles.append({
                'title': title,
                'link': link,
                'summary': summary,
                'content': content[:500] + "..."  # Truncate content for display
            })
    return filtered_articles

# Streamlit UI
st.title("RSS Feed Analyzer")

# Input for SMTP settings
smtp_server = st.text_input("SMTP Server (e.g., smtp.gmail.com)", "smtp.gmail.com")
smtp_port = st.number_input("SMTP Port (e.g., 587)", value=587)
smtp_user = st.text_input("enter your email")
smtp_password = st.text_input("password", type="password")

# Input for RSS feed URL
rss_url = st.text_input("Enter RSS feed URL", "https://example.com/rss")

# Input for keywords
keywords_input = st.text_input("Enter keywords (comma-separated)", "python, data science, machine learning")
keywords = [keyword.strip().lower() for keyword in keywords_input.split(',')]

# Input for client email
client_email = st.text_input("Enter client email address")

# Initialize session state for filtered articles and last update time
if 'filtered_articles' not in st.session_state:
    st.session_state.filtered_articles = []
if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.now()

# Counter and refresh logic
refresh_interval = 30  # 30 seconds
time_since_update = (datetime.now() - st.session_state.last_update).total_seconds()

if time_since_update >= refresh_interval:
    st.session_state.filtered_articles = fetch_and_process_rss(rss_url, keywords)
    st.session_state.last_update = datetime.now()

# Display counter
st.write(f"Time until next refresh: {max(0, refresh_interval - time_since_update):.0f} seconds")

# Display filtered articles and prepare email body
st.subheader("Filtered Articles")
email_body = "<h2>Filtered Articles</h2>"
for article in st.session_state.filtered_articles:
    st.markdown(f"**[{article['title']}]({article['link']})**")
    st.write("Summary:")
    st.markdown(article['summary'], unsafe_allow_html=True)
    st.write("Article Preview:")
    st.write(article['content'])
    st.markdown("---")

    # Add to email body
    email_body += f"<h3><a href='{article['link']}'>{article['title']}</a></h3>"
    email_body += f"<p><strong>Summary:</strong> {article['summary']}</p>"
    email_body += "<hr>"

# Add a refresh button
if st.button("Refresh Now"):
    st.session_state.filtered_articles = fetch_and_process_rss(rss_url, keywords)
    st.session_state.last_update = datetime.now()
    st.rerun()

# Add a send email button
if st.button("Send Email to Client"):
    if client_email and st.session_state.filtered_articles:
        if send_email("RSS Feed Analysis Results", email_body, client_email, smtp_server, smtp_port, smtp_user, smtp_password):
            st.success("Email sent successfully!")
        else:
            st.error("Failed to send email. Please check the error message above.")
    elif not client_email:
        st.warning("Please enter a client email address.")
    elif not st.session_state.filtered_articles:
        st.warning("No articles to send. Please refresh or adjust your search criteria.")

# Auto-refresh the app every 5 seconds to update the counter
time.sleep(5)
st.rerun()