import streamlit as st

from ignis.rag import load_index, search

st.title("Ask the NASA documents (retrieval only - every answer is a quoted passage)")
chunks, bm25 = load_index()
question = st.text_input("Question", "Why does a droplet flame go out at a large diameter?")
if question:
    for hit in search(question, chunks, bm25, k=5):
        with st.expander(f"{hit['title']} - page {hit['page']} (score {hit['score']:.1f})"):
            st.write(hit["text"])
            st.markdown(f"[Open source document]({hit['url']})")
