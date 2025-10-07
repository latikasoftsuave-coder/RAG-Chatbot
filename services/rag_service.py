from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.schema import HumanMessage
from utils.vectorstore_utils import save_vectorstore, load_vectorstore

VECTORSTORE_PATH = ".vectorstore"

class RAGService:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.fallback_llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)

    def create_vectorstore(self, chunks):
        vectorstore = FAISS.from_texts(chunks, self.embeddings)
        save_vectorstore(vectorstore, VECTORSTORE_PATH)

    def load_rag(self):
        vectorstore = load_vectorstore(VECTORSTORE_PATH, self.embeddings)
        retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 3})
        qa = RetrievalQA.from_chain_type(
            llm=ChatOpenAI(model_name="gpt-4o-mini", temperature=0),
            chain_type="stuff",
            retriever=retriever
        )
        return qa, retriever

    def get_answer(self, query: str):
        try:
            qa, retriever = self.load_rag()
            docs = retriever.invoke(query)
            if not docs:
                fallback_response = self.fallback_llm.invoke([HumanMessage(content=query)])
                answer = fallback_response.content.strip()
            else:
                response = qa.invoke({"query": query})
                answer = response["result"].strip()
                if len(answer) < 15 or "I don't know" in answer.lower():
                    fallback_response = self.fallback_llm.invoke([HumanMessage(content=query)])
                    answer = fallback_response.content.strip()
        except Exception as e:
            answer = f"❌ Something went wrong: {e}"
        return {"query": query, "answer": answer}