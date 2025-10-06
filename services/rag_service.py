from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from utils.vectorstore_utils import save_vectorstore, load_vectorstore

VECTORSTORE_PATH = "vectorstore"

class RAGService:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    def create_vectorstore(self, chunks):
        vectorstore = FAISS.from_texts(chunks, self.embeddings)
        save_vectorstore(vectorstore, VECTORSTORE_PATH)

    def load_rag(self):
        vectorstore = load_vectorstore(VECTORSTORE_PATH, self.embeddings)
        retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k":3})
        qa = RetrievalQA.from_chain_type(
            llm=ChatOpenAI(model_name="gpt-4o-mini", temperature=0),
            chain_type="stuff",
            retriever=retriever
        )
        return qa

    def get_answer(self, query: str):
        qa = self.load_rag()
        answer = qa.run(query)
        return {"query": query, "answer": answer}
