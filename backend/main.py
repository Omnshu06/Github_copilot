# main.py
from fastapi import FastAPI, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import hashlib
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import local modules
import database
from ai_chain import get_chain

app = FastAPI(
    title="CodeWhiz AI Backend",
    description="AI-powered coding assistant with LangChain & OpenAI",
    version="1.0"
)

# ✅ Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------ Pydantic Models ------------------
class UserCreate(BaseModel):
    name: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class CodeRequest(BaseModel):
    code: str
    lang: str = "python"
    query: Optional[str] = None

class ChatRequest(BaseModel):
    query: str
    code: Optional[str] = None
    lang: str = "python"

class GenerateRequest(BaseModel):
    query: str
    lang: str = "python"

class TranslateRequest(BaseModel):
    code: str
    source_lang: str
    target_lang: str

class HistorySaveRequest(BaseModel):
    query: str
    response: dict
    lang: str = "python"

# Utility: Hash password
def hash_pwd(pwd: str):
    return hashlib.sha256(pwd.encode()).hexdigest()

# ------------------ Auth Endpoints ------------------
@app.post("/auth/signup")
def signup(user: UserCreate):
    success = database.add_user(user.name, user.email, hash_pwd(user.password))
    if not success:
        raise HTTPException(status_code=400, detail="User already exists")
    return {"msg": "User created successfully"}

@app.post("/auth/login")
def login(credentials: UserLogin):
    user = database.verify_user(credentials.email, hash_pwd(credentials.password))
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {
        "msg": "Login successful",
        "user": {"name": user[0], "email": user[1]}
    }

# ------------------ AI Endpoints ------------------

@app.post("/ai/generate")
def ai_generate(request: GenerateRequest):
    print(f"🚀 /ai/generate: Received query='{request.query}', lang='{request.lang}'")
    try:
        chain = get_chain("generate")
        input_data = {"query": request.query.strip(), "lang": request.lang}
        print(f"📦 Input to chain: {input_data}")
        
        result = chain.invoke(input_data)
        
        print("✅ Successfully parsed LLM response")
        return {
            "response": {
                "explanation": result.explanation.strip(),
                "code": result.code.strip()
            }
        }
    except Exception as e:
        print(f"❌ /ai/generate failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"AI generation failed: {str(e)}. Check server logs."
        )

@app.post("/ai/chat")
def ai_chat_endpoint(request: ChatRequest):
    try:
        chain = get_chain("chat")
        input_data = {
            "query": request.query.strip(),
            "code": request.code.strip() if request.code else "",
            "lang": request.lang
        }
        result = chain.invoke(input_data)
        return {
            "response": {
                "explanation": result.explanation.strip(),
                "code": result.code.strip()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

@app.post("/ai/translate")
def ai_translate(request: TranslateRequest):
    try:
        chain = get_chain("translate")
        input_data = {
            "code": request.code,
            "source_lang": request.source_lang,
            "target_lang": request.target_lang
        }
        result = chain.invoke(input_data)
        return {
            "response": {
                "explanation": result.explanation.strip(),
                "code": result.code.strip()
            }
        }
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Translate failed: {str(e)}")

@app.post("/ai/{feature}")
def ai_feature(
    feature: str = Path(..., description="AI feature: explain, refactor, fix, doc, test"),
    request: CodeRequest = None
):
    allowed_features = ["explain", "refactor", "fix", "doc", "test"]
    if feature not in allowed_features:
        raise HTTPException(status_code=400, detail="Invalid AI feature")

    try:
        chain = get_chain(feature)
        input_data = {
            "code": request.code,
            "lang": request.lang,
            "query": request.query or ""
        }
        print(f"🎯 Invoking {feature} with: {input_data}")
        result = chain.invoke(input_data)
        return {
            "response": {
                "explanation": result.explanation.strip(),
                "code": result.code.strip()
            }
        }
    except Exception as e:
        print(f"❌ Error in {feature}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI processing failed: {str(e)}")

# ------------------ History Endpoints ------------------
@app.post("/history/save/{email}/{feature}")
def save_history(email: str, feature: str, request: HistorySaveRequest):
    try:
        response_dict = {
            "explanation": request.response.get("explanation", ""),
            "code": request.response.get("code", "")
        }
        response_json = json.dumps(response_dict)
        database.save_chat(
            user_email=email,
            query=request.query,
            response=response_json,
            lang=request.lang
        )
        return {"msg": f"Chat saved for feature={feature}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving history: {str(e)}")

@app.get("/history/{email}")
def get_history(email: str, limit: int = 20):
    try:
        history = database.get_chat_history(email, limit)
        return [
            {
                "query": h["query"],
                "response": json.loads(h["response"]) if isinstance(h["response"], str) else h["response"],
                "lang": h["lang"]
            }
            for h in history
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading history: {str(e)}")