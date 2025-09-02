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
                confidence_scores = probabilities.max(axis=1).tolist()
        except:
            pass

        return ClassificationResponse(
            success=True,
            predictions=predictions,
            confidence_scores=confidence_scores,
            message=f"Successfully classified {len(predictions)} transactions"
        )

    except Exception as e:
        logging.error(f"Error in classification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Train classifier
@app.post("/api/v1/train", response_model=APIResponse)
async def train_classifier(
        credentials: HTTPAuthorizationCredentials = Depends(verify_token)
):
    """Train the expense classifier with available labeled data"""
    try:
        labeled_data = ds.load_labeled()

        if len(labeled_data) < 10:
            raise HTTPException(
                status_code=400,
                detail="Need at least 10 labeled transactions to train the model"
            )

        # Train classifier
        classifier.fit(labeled_data, label_col='category')

        # Get training report
        report = classifier.report(labeled_data, labeled_data['category'])

        return APIResponse(
            success=True,
            data={
                "training_samples": len(labeled_data),
                "categories": labeled_data['category'].nunique(),
                "classification_report": report
            },
            message="Model trained successfully"
        )

    except Exception as e:
        logging.error(f"Error training classifier: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Detect anomalies
@app.post("/api/v1/detect-anomalies", response_model=APIResponse)
async def detect_anomalies(
        request: AnomalyDetectionRequest,
        credentials: HTTPAuthorizationCredentials = Depends(verify_token)
):
    """Detect anomalies in transactions"""
    try:
        # Convert to DataFrame
        df = pd.DataFrame([t.dict() for t in request.transactions])

        # Fit detector if requested
        if request.fit_first:
            anomaly_detector.fit(df)

        # Detect anomalies
        anomalies = anomaly_detector.detect_anomalies(df)

        # Convert to serializable format
        anomaly_data = [
            {
                "transaction_id": a.transaction_id,
                "type": a.anomaly_type,
                "severity": a.severity,
                "score": a.score,
                "description": a.description,
                "recommendations": a.recommendations
            }
            for a in anomalies
        ]

        return APIResponse(
            success=True,
            data={
                "anomalies_count": len(anomalies),
                "anomalies": anomaly_data
            },
            message=f"Detected {len(anomalies)} anomalies"
        )

    except Exception as e:
        logging.error(f"Error detecting anomalies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Reconciliation with KAME
@app.post("/api/v1/reconcile", response_model=APIResponse)
async def reconcile_with_kame(
        request: ReconciliationRequest,
        credentials: HTTPAuthorizationCredentials = Depends(verify_token)
):
    """Reconcile bank transactions with KAME documents"""
    try:
        # Convert bank transactions
        bank_df = pd.DataFrame([t.dict() for t in request.bank_transactions])

        # Convert KAME documents
        kame_df = pd.DataFrame(request.kame_documents)

        # Perform reconciliation
        unbacked_expenses = kame_integrator.find_unbacked_expenses(bank_df, kame_df)
        reconciliation_report = kame_integrator.generate_reconciliation_report(bank_df, kame_df)

        return APIResponse(
            success=True,
            data={
                "reconciliation_summary": reconciliation_report['summary'],
                "unbacked_expenses": unbacked_expenses.to_dict('records') if not unbacked_expenses.empty else [],
                "risk_analysis": reconciliation_report.get('risk_analysis', {})
            },
            message=f"Reconciliation completed. Found {len(unbacked_expenses)} unbacked expenses."
        )

    except Exception as e:
        logging.error(f"Error in reconciliation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Get financial summary
@app.get("/api/v1/summary", response_model=APIResponse)
async def get_financial_summary(
        credentials: HTTPAuthorizationCredentials = Depends(verify_token)
):
    """Get financial summary from stored data"""
    try:
        summary = ds.get_financial_summary()

        return APIResponse(
            success=True,
            data=summary,
            message="Financial summary retrieved successfully"
        )

    except Exception as e:
        logging.error(f"Error getting summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Validate data
@app.post("/api/v1/validate", response_model=APIResponse)
async def validate_data(
        request: ClassificationRequest,
        credentials: HTTPAuthorizationCredentials = Depends(verify_token)
):
    """Validate transaction data quality"""
    try:
        # Convert to DataFrame
        df = pd.DataFrame([t.dict() for t in request.transactions])

        # Validate data
        validation_result = DataValidator.validate_bank_dataframe(df)

        return APIResponse(
            success=validation_result['valid'],
            data=validation_result,
            message="Data validation completed"
        )

    except Exception as e:
        logging.error(f"Error validating data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Export data
@app.get("/api/v1/export/{format}")
async def export_data(
        format: str,
        credentials: HTTPAuthorizationCredentials = Depends(verify_token)
):
    """Export data in specified format"""
    try:
        if format not in ['csv', 'excel', 'json']:
            raise HTTPException(status_code=400, detail="Supported formats: csv, excel, json")

        # Get all labeled data
        data = ds.load_labeled()

        if data.empty:
            raise HTTPException(status_code=404, detail="No data available for export")

        # Create temporary file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if format == 'csv':
            filename = f"financial_data_{timestamp}.csv"
            filepath = f"/tmp/{filename}"
            data.to_csv(filepath, index=False)
            return FileResponse(
                path=filepath,
                filename=filename,
                media_type='application/octet-stream'
            )

        elif format == 'excel':
            filename = f"financial_data_{timestamp}.xlsx"
            filepath = f"/tmp/{filename}"
            data.to_excel(filepath, index=False)
            return FileResponse(
                path=filepath,
                filename=filename,
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

        elif format == 'json':
            return JSONResponse(content=data.to_dict('records'))

    except Exception as e:
        logging.error(f"Error exporting data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Get API documentation
@app.get("/api/v1/info", response_model=Dict[str, Any])
async def get_api_info():
    """Get API information and endpoints"""
    return {
        "name": "Santander Finance API",
        "version": "1.0.0",
        "description": "REST API for financial data processing and analysis",
        "endpoints": {
            "POST /api/v1/parse-statement": "Parse bank statement file",
            "POST /api/v1/classify": "Classify transactions",
            "POST /api/v1/train": "Train ML classifier",
            "POST /api/v1/detect-anomalies": "Detect anomalies",
            "POST /api/v1/reconcile": "Reconcile with KAME",
            "GET /api/v1/summary": "Get financial summary",
            "POST /api/v1/validate": "Validate data",
            "GET /api/v1/export/{format}": "Export data"
        },
        "authentication": "Bearer token required",
        "formats_supported": ["xlsx", "xls", "csv", "json"]
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )