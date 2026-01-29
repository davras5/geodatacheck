"""
GeoDataCheck API - FastAPI backend for geo data validation.

Run with: uvicorn main:app --reload
"""

import io
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import pandas as pd

from validation import (
    create_default_registry,
    ValidationEngine,
    ValidationResult,
)


# Session storage (in-memory, no persistence)
sessions: Dict[str, dict] = {}
SESSION_TIMEOUT_MINUTES = 30


class SessionData:
    """In-memory session data, cleared on timeout."""

    def __init__(self, df: pd.DataFrame, result: ValidationResult, config: dict):
        self.df = df
        self.result = result
        self.config = config
        self.created_at = datetime.now()
        self.expires_at = datetime.now() + timedelta(minutes=SESSION_TIMEOUT_MINUTES)

    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at

    def cleanup(self):
        """Explicitly clear data from memory."""
        self.df = None
        self.result = None
        self.config = None


def cleanup_expired_sessions():
    """Remove expired sessions."""
    expired = [
        sid for sid, data in sessions.items()
        if isinstance(data, SessionData) and data.is_expired()
    ]
    for sid in expired:
        if sid in sessions:
            sessions[sid].cleanup()
            del sessions[sid]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print("GeoDataCheck API starting...")
    yield
    # Shutdown - cleanup all sessions
    print("Cleaning up sessions...")
    for sid, data in sessions.items():
        if isinstance(data, SessionData):
            data.cleanup()
    sessions.clear()


# Initialize FastAPI app
app = FastAPI(
    title="GeoDataCheck API",
    description="Geo data validation service for Swiss building portfolios",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize validation engine
registry = create_default_registry()
engine = ValidationEngine(registry)


# Pydantic models for API
class ValidationConfig(BaseModel):
    columns: Dict[str, str] = {}
    options: Dict[str, Any] = {}
    rule_ids: Optional[List[str]] = None
    dimension_columns: Dict[str, str] = {}  # region, portfolio, responsible


class ColumnInfo(BaseModel):
    name: str
    detected_as: Optional[str] = None
    sample_values: List[str] = []


class UploadResponse(BaseModel):
    session_id: str
    columns: List[ColumnInfo]
    detected_mappings: Dict[str, str]
    row_count: int
    expires_in_minutes: int


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "GeoDataCheck API", "version": "1.0.0"}


@app.get("/api/rules")
async def get_rules():
    """Get documentation for all validation rules."""
    cleanup_expired_sessions()
    return {"rules": registry.get_documentation()}


@app.get("/api/rules/{category}")
async def get_rules_by_category(category: str):
    """Get rules by category."""
    from validation import Category
    try:
        cat = Category(category)
        rules = registry.get_rules_by_category(cat)
        return {"rules": [r.metadata.to_dict() for r in rules]}
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")


@app.post("/api/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload an Excel file for validation.

    Returns session ID and detected column information.
    """
    cleanup_expired_sessions()

    # Validate file type
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Please upload an Excel file (.xlsx or .xls)"
        )

    try:
        # Read file into memory (no disk storage)
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))

        if len(df) == 0:
            raise HTTPException(status_code=400, detail="File is empty")

        # Detect column mappings
        detected = engine.detect_columns(df)

        # Build column info with samples
        columns_info = []
        for col in df.columns:
            sample_values = df[col].dropna().head(3).astype(str).tolist()
            detected_as = None
            for logical, actual in detected.items():
                if actual == col:
                    detected_as = logical
                    break
            columns_info.append(ColumnInfo(
                name=col,
                detected_as=detected_as,
                sample_values=sample_values,
            ))

        # Create session (store DataFrame temporarily)
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            'df': df,
            'filename': file.filename,
            'created_at': datetime.now(),
        }

        return UploadResponse(
            session_id=session_id,
            columns=columns_info,
            detected_mappings=detected,
            row_count=len(df),
            expires_in_minutes=SESSION_TIMEOUT_MINUTES,
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")


@app.post("/api/validate/{session_id}")
async def validate_data(session_id: str, config: ValidationConfig):
    """
    Run validation on previously uploaded data.

    Returns validation results with dimensional breakdowns.
    """
    cleanup_expired_sessions()

    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    session = sessions[session_id]
    df = session.get('df')

    if df is None:
        raise HTTPException(status_code=404, detail="Session data not available")

    # Build config
    validation_config = {
        'columns': config.columns or engine.detect_columns(df),
        'options': config.options,
    }

    # Run validation
    result = engine.validate(df, validation_config, config.rule_ids)

    # Add dimensional analysis
    result_dict = result.to_dict()

    # Add dimension breakdowns if columns specified
    for dim_name, dim_col in config.dimension_columns.items():
        if dim_col and dim_col in df.columns:
            result_dict[f'by_{dim_name}'] = result.get_errors_by_dimension(df, dim_col)

    # Store result in session for later download
    session['result'] = result
    session['config'] = validation_config

    return result_dict


@app.get("/api/session/{session_id}/download/report")
async def download_report(session_id: str):
    """
    Download validation error report as Excel.
    """
    cleanup_expired_sessions()

    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    session = sessions[session_id]
    result = session.get('result')

    if result is None:
        raise HTTPException(status_code=400, detail="No validation results. Run validation first.")

    # Create Excel report
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Summary sheet
        summary_data = {
            'Metrik': ['Total Zeilen', 'Fehler', 'Warnungen', 'Bestanden', 'Erfolgsquote'],
            'Wert': [
                result.total_rows,
                result.error_count,
                result.warning_count,
                result.passed_rows,
                f"{round(result.passed_rows / result.total_rows * 100, 1)}%"
            ]
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='Zusammenfassung', index=False)

        # Errors sheet
        if result.errors:
            error_data = [e.to_dict() for e in result.errors]
            errors_df = pd.DataFrame(error_data)
            errors_df = errors_df.rename(columns={
                'row_number': 'Zeile',
                'column': 'Spalte',
                'rule_id': 'Regel-ID',
                'rule_name': 'Regel',
                'severity': 'Schweregrad',
                'message': 'Meldung',
                'value': 'Wert',
                'suggestion': 'Vorschlag',
            })
            errors_df = errors_df[['Zeile', 'Spalte', 'Regel', 'Schweregrad', 'Meldung', 'Wert', 'Vorschlag']]
            errors_df.to_excel(writer, sheet_name='Fehler', index=False)

    output.seek(0)

    filename = session.get('filename', 'data').replace('.xlsx', '').replace('.xls', '')

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={filename}_fehler.xlsx"
        }
    )


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """
    Explicitly delete a session and all associated data.
    """
    if session_id in sessions:
        session = sessions[session_id]
        if isinstance(session, SessionData):
            session.cleanup()
        elif isinstance(session, dict):
            session.clear()
        del sessions[session_id]

    return {"status": "ok", "message": "Session deleted"}


# ============================================================================
# Checkers (Workflow configurations)
# ============================================================================

CHECKERS = [
    {
        'id': 'address-checker',
        'name': 'Adress-Checker',
        'description': 'Prüft Schweizer Adressen auf Format, PLZ-Format und Kantone.',
        'description_long': 'Dieser Checker validiert PLZ-Format (4-stellig), Kantonsabkürzungen und Strassenformate.',
        'category': 'QUALITÄTSSICHERUNG',
        'required_columns': ['plz', 'ort', 'strasse'],
        'rule_ids': ['R-ADDR-01', 'R-ADDR-02', 'R-ADDR-04', 'R-ADDR-05'],
    },
    {
        'id': 'coordinate-checker',
        'name': 'Koordinaten-Checker',
        'description': 'Prüft ob Koordinaten innerhalb der Schweiz liegen (LV95/WGS84).',
        'description_long': 'Validiert E/N-Koordinaten gegen Schweizer Grenzen, erkennt automatisch LV95 oder WGS84.',
        'category': 'KOORDINATEN',
        'required_columns': ['easting', 'northing'],
        'rule_ids': ['R-COORD-01', 'R-COORD-02', 'R-COORD-04'],
    },
    {
        'id': 'egid-checker',
        'name': 'EGID/GWR Checker',
        'description': 'Validiert EGID-Nummern auf Format und Eindeutigkeit.',
        'description_long': 'Prüft Eidgenössische Gebäudeidentifikatoren (EGID) auf korrektes Format und Duplikate.',
        'category': 'EGID',
        'required_columns': ['egid'],
        'rule_ids': ['R-EGID-01', 'R-EGID-02', 'R-EGID-03'],
    },
    {
        'id': 'quality-checker',
        'name': 'Datenqualitäts-Check',
        'description': 'Erkennt doppelte Zeilen, leere Einträge und Kodierungsprobleme.',
        'description_long': 'Allgemeine Datenqualitätsprüfungen: Duplikate, leere Zeilen, Datentyp-Konsistenz, Zeichenkodierung.',
        'category': 'QUALITÄTSSICHERUNG',
        'required_columns': [],
        'rule_ids': ['R-GEN-01', 'R-GEN-02', 'R-GEN-03', 'R-GEN-04'],
    },
    {
        'id': 'full-checker',
        'name': 'Portfolio Vollständigkeits-Check',
        'description': 'Führt alle Prüfungen durch: Adressen, Koordinaten, EGID und Qualität.',
        'description_long': 'Umfassende Validierung mit allen verfügbaren Regeln für eine vollständige Portfolioprüfung.',
        'category': 'QUALITÄTSSICHERUNG',
        'required_columns': [],
        'rule_ids': None,  # All rules
    },
]


@app.get("/api/checkers")
async def get_checkers():
    """Get all available checker configurations."""
    return {"checkers": CHECKERS}


@app.get("/api/checkers/{checker_id}")
async def get_checker(checker_id: str):
    """Get a specific checker configuration."""
    for checker in CHECKERS:
        if checker['id'] == checker_id:
            return checker
    raise HTTPException(status_code=404, detail=f"Checker not found: {checker_id}")


# ============================================================================
# Run server (development)
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
