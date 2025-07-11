"""Web API for Query Assistant

FastAPI-based REST API for natural language SQL queries.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import os
import json

from fastapi import FastAPI, HTTPException, Query as QueryParam
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import uvicorn
from dotenv import load_dotenv

from .query_assistant import QueryAssistant
from .schema import QueryResult

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="IACSGraph Query Assistant API",
    description="Natural language to SQL query interface",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global query assistant instance
query_assistant: Optional[QueryAssistant] = None


class QueryRequest(BaseModel):
    """Request model for query endpoint"""
    query: str = Field(..., description="Natural language query", example="최근 7일 주요 아젠다는?")
    category: Optional[str] = Field(None, description="Query category filter")
    execute: bool = Field(True, description="Whether to execute SQL")
    limit: Optional[int] = Field(None, description="Result limit", ge=1, le=1000)
    use_defaults: bool = Field(False, description="Use default values for missing parameters")


class QueryResponse(BaseModel):
    """Response model for query endpoint"""
    success: bool
    query_id: str
    executed_sql: str
    parameters: Dict[str, Any]
    results: List[Dict[str, Any]]
    execution_time: float
    error: Optional[str] = None
    result_count: int
    validation_info: Optional[Dict[str, Any]] = None
    requires_clarification: bool = False


class AnalyzeResponse(BaseModel):
    """Response model for analyze endpoint"""
    original_query: str
    extracted_keywords: List[str]
    expanded_keywords: List[str]
    confidence: float
    missing_info: List[str]
    suggestions: List[str]
    matching_templates: List[Dict[str, Any]]


class SuggestionResponse(BaseModel):
    """Response model for suggestions"""
    suggestions: List[Dict[str, Any]]


@app.on_event("startup")
async def startup_event():
    """Initialize Query Assistant on startup"""
    global query_assistant
    
    # Load database configuration
    db_config_json = os.environ.get("IACSGRAPH_DB_CONFIG")
    
    if db_config_json:
        try:
            db_config = json.loads(db_config_json)
        except json.JSONDecodeError:
            db_path = os.environ.get("DATABASE_PATH", "./data/iacsgraph.db")
            db_config = {"type": "sqlite", "path": db_path}
    else:
        db_path = os.environ.get("DATABASE_PATH", "./data/iacsgraph.db")
        db_config = {"type": "sqlite", "path": db_path}
    
    # Initialize Query Assistant
    try:
        query_assistant = QueryAssistant(
            db_config=db_config,
            qdrant_url=os.environ.get("QDRANT_URL", "localhost"),
            qdrant_port=int(os.environ.get("QDRANT_PORT", "6333")),
            openai_api_key=os.environ.get("OPENAI_API_KEY")
        )
        logger.info("Query Assistant initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Query Assistant: {e}")
        raise


@app.get("/", response_class=HTMLResponse)
async def root():
    """Simple web interface"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>IACSGraph Query Assistant</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #333; }
            .query-box { margin: 20px 0; }
            input[type="text"] { width: 70%; padding: 10px; font-size: 16px; border: 1px solid #ddd; border-radius: 5px; }
            button { padding: 10px 20px; font-size: 16px; background-color: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; }
            button:hover { background-color: #0056b3; }
            .results { margin-top: 30px; }
            .error { color: red; }
            .success { color: green; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background-color: #f8f9fa; font-weight: bold; }
            .examples { margin-top: 30px; padding: 20px; background-color: #f8f9fa; border-radius: 5px; }
            .example { margin: 5px 0; cursor: pointer; color: #007bff; }
            .example:hover { text-decoration: underline; }
            .loading { display: none; color: #666; }
            pre { background-color: #f8f9fa; padding: 10px; border-radius: 5px; overflow-x: auto; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔍 IACSGraph Query Assistant</h1>
            <p>자연어로 데이터베이스를 검색하세요!</p>
            
            <div class="query-box">
                <input type="text" id="query" placeholder="예: 최근 7일 주요 아젠다는?" />
                <button onclick="executeQuery()">검색</button>
                <span class="loading" id="loading">⏳ 처리 중...</span>
            </div>
            
            <div id="results" class="results"></div>
            
            <div class="examples">
                <h3>💡 예시 쿼리</h3>
                <div class="example" onclick="setQuery('최근 7일 주요 아젠다는 무엇인가?')">최근 7일 주요 아젠다는 무엇인가?</div>
                <div class="example" onclick="setQuery('KRSDTP 기관의 응답률은?')">KRSDTP 기관의 응답률은?</div>
                <div class="example" onclick="setQuery('미결정 아젠다 목록')">미결정 아젠다 목록</div>
                <div class="example" onclick="setQuery('승인된 아젠다만 보여주세요')">승인된 아젠다만 보여주세요</div>
                <div class="example" onclick="setQuery('기관별 응답률 비교')">기관별 응답률 비교</div>
            </div>
        </div>
        
        <script>
            function setQuery(text) {
                document.getElementById('query').value = text;
                executeQuery();
            }
            
            async function executeQuery() {
                const query = document.getElementById('query').value;
                if (!query) return;
                
                const loading = document.getElementById('loading');
                const results = document.getElementById('results');
                
                loading.style.display = 'inline';
                results.innerHTML = '';
                
                try {
                    const response = await fetch('/api/query', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ query: query })
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        let html = '<h3 class="success">✅ 검색 완료</h3>';
                        html += `<p>실행 시간: ${data.execution_time.toFixed(2)}초</p>`;
                        html += `<p>결과: ${data.result_count}건</p>`;
                        
                        if (data.executed_sql) {
                            html += '<h4>SQL 쿼리:</h4>';
                            html += `<pre>${data.executed_sql}</pre>`;
                        }
                        
                        if (data.results && data.results.length > 0) {
                            html += '<h4>결과 데이터:</h4>';
                            html += '<table>';
                            
                            // Headers
                            html += '<tr>';
                            Object.keys(data.results[0]).forEach(key => {
                                html += `<th>${key}</th>`;
                            });
                            html += '</tr>';
                            
                            // Data rows
                            data.results.slice(0, 20).forEach(row => {
                                html += '<tr>';
                                Object.values(row).forEach(value => {
                                    html += `<td>${value || ''}</td>`;
                                });
                                html += '</tr>';
                            });
                            
                            html += '</table>';
                            
                            if (data.results.length > 20) {
                                html += `<p>... 외 ${data.results.length - 20}건</p>`;
                            }
                        }
                        
                        results.innerHTML = html;
                    } else if (data.requires_clarification && data.validation_info) {
                        // Show parameter validation info
                        let html = '<h3 class="error">❓ 추가 정보가 필요합니다</h3>';
                        html += '<div style="background-color: #fff3cd; border: 1px solid #ffeeba; padding: 15px; border-radius: 5px; margin: 10px 0;">';
                        html += '<pre style="white-space: pre-wrap; margin: 0;">' + data.error + '</pre>';
                        html += '</div>';
                        
                        // Show missing parameters
                        if (data.validation_info.missing_params && data.validation_info.missing_params.length > 0) {
                            html += '<h4>필요한 파라미터:</h4>';
                            html += '<ul>';
                            data.validation_info.missing_params.forEach(param => {
                                html += `<li><strong>${param}</strong>`;
                                if (data.validation_info.suggestions[param]) {
                                    html += ' - 예시: ' + data.validation_info.suggestions[param].slice(0, 3).join(', ');
                                }
                                html += '</li>';
                            });
                            html += '</ul>';
                        }
                        
                        results.innerHTML = html;
                    } else {
                        results.innerHTML = `<h3 class="error">❌ 오류</h3><p>${data.error}</p>`;
                    }
                } catch (error) {
                    results.innerHTML = `<h3 class="error">❌ 오류</h3><p>${error.message}</p>`;
                } finally {
                    loading.style.display = 'none';
                }
            }
            
            // Enter key support
            document.getElementById('query').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') executeQuery();
            });
        </script>
    </body>
    </html>
    """


@app.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Execute natural language query"""
    if not query_assistant:
        raise HTTPException(status_code=500, detail="Query Assistant not initialized")
    
    try:
        # Process query
        result = query_assistant.process_query(
            user_query=request.query,
            category=request.category,
            execute=request.execute,
            use_defaults=request.use_defaults
        )
        
        # Apply limit if specified
        if request.limit and result.results:
            result.results = result.results[:request.limit]
        
        # Check if validation info exists
        requires_clarification = False
        validation_info = None
        
        if hasattr(result, 'validation_info') and result.validation_info:
            validation_info = result.validation_info
            requires_clarification = not validation_info.get("is_valid", True)
        
        return QueryResponse(
            success=not bool(result.error),
            query_id=result.query_id,
            executed_sql=result.executed_sql,
            parameters=result.parameters,
            results=result.results,
            execution_time=result.execution_time,
            error=result.error,
            result_count=len(result.results),
            validation_info=validation_info,
            requires_clarification=requires_clarification
        )
        
    except Exception as e:
        logger.error(f"Query error: {e}")
        return QueryResponse(
            success=False,
            query_id="",
            executed_sql="",
            parameters={},
            results=[],
            execution_time=0.0,
            error=str(e),
            result_count=0
        )


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(query: str = QueryParam(..., description="Query to analyze")):
    """Analyze query without executing"""
    if not query_assistant:
        raise HTTPException(status_code=500, detail="Query Assistant not initialized")
    
    try:
        analysis = query_assistant.analyze_query(query)
        
        return AnalyzeResponse(
            original_query=analysis["original_query"],
            extracted_keywords=analysis["extracted_keywords"],
            expanded_keywords=analysis["expanded_keywords"],
            confidence=analysis["confidence"],
            missing_info=analysis["missing_info"],
            suggestions=analysis["suggestions"],
            matching_templates=analysis["matching_templates"]
        )
        
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/suggestions", response_model=SuggestionResponse)
async def suggestions(
    partial: str = QueryParam(..., description="Partial query"),
    limit: int = QueryParam(5, ge=1, le=20)
):
    """Get query suggestions"""
    if not query_assistant:
        raise HTTPException(status_code=500, detail="Query Assistant not initialized")
    
    try:
        suggestions = query_assistant.get_suggestions(partial)[:limit]
        
        return SuggestionResponse(
            suggestions=[
                {"query": query, "score": score}
                for query, score in suggestions
            ]
        )
        
    except Exception as e:
        logger.error(f"Suggestion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/popular", response_model=List[Dict[str, Any]])
async def popular_queries(limit: int = QueryParam(10, ge=1, le=50)):
    """Get popular queries"""
    if not query_assistant:
        raise HTTPException(status_code=500, detail="Query Assistant not initialized")
    
    try:
        templates = query_assistant.get_popular_queries(limit)
        
        return [
            {
                "query": t.natural_query,
                "category": t.category,
                "usage_count": t.usage_count,
                "last_used": t.last_used.isoformat() if t.last_used else None
            }
            for t in templates
        ]
        
    except Exception as e:
        logger.error(f"Popular queries error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "query-assistant",
        "timestamp": datetime.now().isoformat()
    }


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the web server"""
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run server
    run_server()