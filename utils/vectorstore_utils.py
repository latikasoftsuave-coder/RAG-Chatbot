from langchain_community.vectorstores import FAISS

def save_vectorstore(vectorstore, path):
    vectorstore.save_local(path)

def load_vectorstore(path, embeddings):
    return FAISS.load_local(path, embeddings, allow_dangerous_deserialization=True)