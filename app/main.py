# api/main.py - API REST opcional para integración externa
from __future__ import annotations
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import pandas as pd
import io
import os
import logging
from datetime import datetime
from pathlib import Path

# Import app components
import sys

sys.path.append(str(Path(__file__).parent.parent))

from app.bankstatements.santander import SantanderParser
from app.ml.classifier import ExpenseClassifier
from app.kame.kame_report import KameIntegrator
from app.storage.datastore import DataStore
from app.analytics.anomaly_detector import AnomalyDetector
from app.utils.validators import DataValidator

# Initialize FastAPI
app = FastAPI(
    title="Santander Finance API",
    description="API REST para integración con sistema de análisis financiero",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()
API_KEY = os.getenv("API_KEY", "your-secret-api-key")

# Initialize components
ds = DataStore()
parser = SantanderParser()
classifier = ExpenseClassifier()
kame_integrator = KameIntegrator()
anomaly_detector = AnomalyDetector()


# Pydantic models
class TransactionModel(BaseModel):
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    description: str = Field(..., description="Transaction description")
    amount: float = Field(..., description="Transaction amount")
    debit_credit: Optional[str] = Field(None, description="CARGO or ABONO")
    category: Optional[str] = Field(None, description="Transaction category")


class ClassificationRequest(BaseModel):
    transactions: List[TransactionModel]


class ClassificationResponse(BaseModel):
    success: bool
    predictions: List[str]
    confidence_scores: Optional[List[float]]
    message: str


class AnomalyDetectionRequest(BaseModel):
    transactions: List[TransactionModel]
    fit_first: bool = Field(False, description="Fit detector with provided data first")


class ReconciliationRequest(BaseModel):
    bank_transactions: List[TransactionModel]
    kame_documents: List[Dict[str, Any]]


class APIResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]]
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)


# Authentication dependency
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return credentials


# Health check
@app.get("/health", response_model=Dict[str, str])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Santander Finance API"
    }


# Parse bank statement
@app.post("/api/v1/parse-statement", response_model=APIResponse)
async def parse_statement(
        file: UploadFile = File(...),
        credentials: HTTPAuthorizationCredentials = Depends(verify_token)
):
    """Parse uploaded bank statement file"""
    try:
        # Validate file
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(
                status_code=400,
                detail="Only Excel files (.xlsx, .xls) are supported"
            )

        # Read file
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))

        # Parse with Santander parser
        parsed_df = parser.parse(df)

        # Convert to JSON-serializable format
        result = {
            "transactions_count": len(parsed_df),
            "transactions": parsed_df.to_dict('records')
        }

        return APIResponse(
            success=True,
            data=result,
            message=f"Successfully parsed {len(parsed_df)} transactions"
        )

    except Exception as e:
        logging.error(f"Error parsing statement: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Classify expenses
@app.post("/api/v1/classify", response_model=ClassificationResponse)
async def classify_expenses(
        request: ClassificationRequest,
        credentials: HTTPAuthorizationCredentials = Depends(verify_token)
):
    """Classify expenses automatically"""
    try:
        # Convert to DataFrame
        df = pd.DataFrame([t.dict() for t in request.transactions])

        # Load labeled data and train classifier
        labeled_data = ds.load_labeled()
        if labeled_data.empty:
            raise HTTPException(
                status_code=400,
                detail="No labeled data available for training. Train the model first."
            )

        classifier.fit(labeled_data, label_col='category')

        # Make predictions
        predictions = classifier.predict(df).tolist()

        # Get confidence scores if available
        confidence_scores = None
        try:
            probabilities = classifier.predict_proba(df)
            if probabilities is not None:
                confidence_scores = probabilities.max(