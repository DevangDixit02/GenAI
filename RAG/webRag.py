# Correct uploader.py
from langchain_community.document_loaders import WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Qdrant  # ✅ updated import
import os
import requests
from dotenv import load_dotenv

load_dotenv()

# requests session with headers
requests.adapters.DEFAULT_RETRIES = 5
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/123.0.0.0 Safari/537.36"
})

# Loaders
html_loader = WebBaseLoader([
    "https://chaidocs.vercel.app/youtube/chai-aur-html/introduction/",
    "https://chaidocs.vercel.app/youtube/chai-aur-html/emmit-crash-course/",
    "https://chaidocs.vercel.app/youtube/chai-aur-html/html-tags/",
], session=session)

django_loader = WebBaseLoader([
    "https://chaidocs.vercel.app/youtube/chai-aur-django/getting-started/",
    "https://chaidocs.vercel.app/youtube/chai-aur-django/jinja-templates/",
    "https://chaidocs.vercel.app/youtube/chai-aur-django/tailwind/",
    "https://chaidocs.vercel.app/youtube/chai-aur-django/models/",
    "https://chaidocs.vercel.app/youtube/chai-aur-django/relationships-and-forms/",
], session=session)

sql_loader = WebBaseLoader([
    "https://chaidocs.vercel.app/youtube/chai-aur-sql/postgres/",
    "https://chaidocs.vercel.app/youtube/chai-aur-sql/normalization/",
    "https://chaidocs.vercel.app/youtube/chai-aur-sql/database-design-exercise/",
    "https://chaidocs.vercel.app/youtube/chai-aur-sql/joins-and-keys/",
], session=session)

html_docs = html_loader.load()
django_docs = django_loader.load()
sql_docs = sql_loader.load()
print(f"✅ Loaded {len(html_docs)} HTML docs, {len(django_docs)} Django docs, {len(sql_docs)} SQL docs")

splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
html_splits = splitter.split_documents(html_docs)
django_splits = splitter.split_documents(django_docs)
sql_splits = splitter.split_documents(sql_docs)
print(f"✅ Split into {len(html_splits)} HTML chunks, {len(django_splits)} Django chunks, {len(sql_splits)} SQL chunks")

embedder = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=os.getenv("GEMINI_API_KEY"),
)

# Upload to Qdrant using only url
Qdrant.from_documents(
    documents=html_splits,
    embedding=embedder,
    collection_name="html_docs",
    url="http://localhost:6333",  # ✅ Pass url, not client
)

Qdrant.from_documents(
    documents=django_splits,
    embedding=embedder,
    collection_name="django_docs",
    url="http://localhost:6333",
)

Qdrant.from_documents(
    documents=sql_splits,
    embedding=embedder,
    collection_name="sql_docs",
    url="http://localhost:6333",
)

print("🎉 Successfully uploaded all collections!")
