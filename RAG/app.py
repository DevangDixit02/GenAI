import streamlit as st
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import Qdrant
from langchain_qdrant import QdrantVectorStore
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Embeddings
embedder = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=os.getenv("GEMINI_API_KEY"),
)

# Load existing collections
html_qdrant = QdrantVectorStore.from_existing_collection(
    url="http://localhost:6333",
    collection_name="html_docs",
    embedding=embedder,
)
django_qdrant = QdrantVectorStore.from_existing_collection(
    url="http://localhost:6333",
    collection_name="django_docs",
    embedding=embedder,
)
sql_qdrant = QdrantVectorStore.from_existing_collection(
    url="http://localhost:6333",
    collection_name="sql_docs",
    embedding=embedder,
)

st.title("CHAI DOCS RAG ☕")

st.sidebar.header("About")
st.sidebar.text("This is a CHAI Docs RAG system built using LangChain and Qdrant.\n\nYou can ask questions about HTML, Django, or SQL, and the system will retrieve relevant answers based on documentation.")

query = st.text_input("💬 Enter your query:")


if query:
    def handle_query(query):
        retrieved_html_docs = html_qdrant.similarity_search_with_score(query, k=3)
        retrieved_django_docs = django_qdrant.similarity_search_with_score(query, k=3)
        retrieved_sql_docs = sql_qdrant.similarity_search_with_score(query, k=3)

        context_html = "\n".join([doc.page_content for doc, _ in retrieved_html_docs])
        context_django = "\n".join([doc.page_content for doc, _ in retrieved_django_docs])
        context_sql = "\n".join([doc.page_content for doc, _ in retrieved_sql_docs])

        prompt = f"""
        You are an expert assistant answering questions based on documentation.
        Use the correct section based on the question.

        You retrieve the answer from the right context. For example: if the question is related to HTML, you will retrieve the answer from the HTML context.

        You retrieve the answer from the right context and then think about the answer and respond to the question as a human would. Explain content in 200 words.

        HTML Context:
        {context_html}

        Django Context:
        {context_django}

        SQL Context:
        {context_sql}

        Question: {query}

        Answer:
        """

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-001",
            temperature=0.2,
            google_api_key=os.getenv("GEMINI_API_KEY"),
        )

        response = llm.invoke(prompt)
        answer = response.content

        sources_html = [(doc.metadata.get("source", "Unknown URL"), score) for doc, score in retrieved_html_docs if doc.metadata.get("source")]
        sources_django = [(doc.metadata.get("source", "Unknown URL"), score) for doc, score in retrieved_django_docs if doc.metadata.get("source")]
        sources_sql = [(doc.metadata.get("source", "Unknown URL"), score) for doc, score in retrieved_sql_docs if doc.metadata.get("source")]

        all_sources = sources_html + sources_django + sources_sql

        all_sources = sorted(all_sources, key=lambda x: x[1], reverse=True)

        most_relevant_source = all_sources[0][0] if all_sources else "No relevant source found"

        return answer, most_relevant_source

    answer, source = handle_query(query)

    st.subheader("🧠 Answer:")
    st.write(answer)

    st.subheader("📚 Most Relevant Source:")
    st.write(f"- {source}")

    st.markdown("<hr>", unsafe_allow_html=True)
else:
    st.text("💬 Enter a query to get started.")
