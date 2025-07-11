#!/usr/bin/env python3
"""Simple web interface for database queries"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import sqlite3
import os
from typing import List, Dict, Any
import uvicorn

app = FastAPI(title="IACSGraph Simple Query")

class SimpleQuery(BaseModel):
    query_type: str
    
# Predefined queries that work
QUERIES = {
    "recent_agendas": """
        SELECT 
            agenda_code,
            subject,
            date(sent_time) as sent_date,
            decision_status
        FROM agenda_chair
        ORDER BY sent_time DESC
        LIMIT 10
    """,
    "kr_response_rate": """
        WITH org_responses AS (
            SELECT 
                COUNT(CASE WHEN arc.KR IS NOT NULL AND arc.KR != '' THEN 1 END) as responded,
                COUNT(*) as total
            FROM agenda_chair ac
            JOIN agenda_responses_content arc ON ac.agenda_base_version = arc.agenda_base_version
            WHERE ac.sent_time >= datetime('now', '-90 days')
        )
        SELECT 
            'KR' as organization,
            responded,
            total,
            ROUND(CAST(responded AS FLOAT) / total * 100, 2) as response_rate
        FROM org_responses
    """,
    "all_org_response_rates": """
        SELECT 
            'ABS' as org, COUNT(CASE WHEN ABS IS NOT NULL AND ABS != '' THEN 1 END) as responded, COUNT(*) as total,
            ROUND(CAST(COUNT(CASE WHEN ABS IS NOT NULL AND ABS != '' THEN 1 END) AS FLOAT) / COUNT(*) * 100, 2) as rate
        FROM agenda_responses_content
        WHERE agenda_base_version IN (SELECT agenda_base_version FROM agenda_chair WHERE sent_time >= datetime('now', '-90 days'))
        UNION ALL
        SELECT 'BV', COUNT(CASE WHEN BV IS NOT NULL AND BV != '' THEN 1 END), COUNT(*),
            ROUND(CAST(COUNT(CASE WHEN BV IS NOT NULL AND BV != '' THEN 1 END) AS FLOAT) / COUNT(*) * 100, 2)
        FROM agenda_responses_content
        WHERE agenda_base_version IN (SELECT agenda_base_version FROM agenda_chair WHERE sent_time >= datetime('now', '-90 days'))
        UNION ALL
        SELECT 'KR', COUNT(CASE WHEN KR IS NOT NULL AND KR != '' THEN 1 END), COUNT(*),
            ROUND(CAST(COUNT(CASE WHEN KR IS NOT NULL AND KR != '' THEN 1 END) AS FLOAT) / COUNT(*) * 100, 2)
        FROM agenda_responses_content
        WHERE agenda_base_version IN (SELECT agenda_base_version FROM agenda_chair WHERE sent_time >= datetime('now', '-90 days'))
    """,
    "pending_agendas": """
        SELECT 
            agenda_code,
            subject,
            date(sent_time) as sent_date,
            decision_status
        FROM agenda_chair
        WHERE decision_status IN ('pending', '미결정', NULL, '')
        ORDER BY sent_time DESC
    """
}

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>IACSGraph Simple Query</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 1000px; margin: 0 auto; }
            button { padding: 10px 20px; margin: 5px; font-size: 16px; cursor: pointer; }
            button:hover { background-color: #ddd; }
            .results { margin-top: 20px; }
            table { width: 100%; border-collapse: collapse; margin-top: 10px; }
            th, td { padding: 8px; text-align: left; border: 1px solid #ddd; }
            th { background-color: #f2f2f2; }
            .loading { display: none; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>IACSGraph Simple Query Interface</h1>
            <p>실제로 작동하는 쿼리들입니다:</p>
            
            <div>
                <button onclick="runQuery('recent_agendas')">📋 최근 아젠다 목록</button>
                <button onclick="runQuery('kr_response_rate')">📊 KR 기관 응답률</button>
                <button onclick="runQuery('all_org_response_rates')">📈 전체 기관 응답률</button>
                <button onclick="runQuery('pending_agendas')">⏳ 미결정 아젠다</button>
            </div>
            
            <div class="loading" id="loading">⏳ 로딩중...</div>
            <div class="results" id="results"></div>
        </div>
        
        <script>
            async function runQuery(queryType) {
                const loading = document.getElementById('loading');
                const results = document.getElementById('results');
                
                loading.style.display = 'block';
                results.innerHTML = '';
                
                try {
                    const response = await fetch('/query/' + queryType);
                    const data = await response.json();
                    
                    if (data.error) {
                        results.innerHTML = '<p style="color: red;">오류: ' + data.error + '</p>';
                    } else {
                        let html = '<h3>결과 (' + data.count + '건)</h3>';
                        
                        if (data.results && data.results.length > 0) {
                            html += '<table>';
                            
                            // Headers
                            html += '<tr>';
                            Object.keys(data.results[0]).forEach(key => {
                                html += '<th>' + key + '</th>';
                            });
                            html += '</tr>';
                            
                            // Data
                            data.results.forEach(row => {
                                html += '<tr>';
                                Object.values(row).forEach(value => {
                                    html += '<td>' + (value || '') + '</td>';
                                });
                                html += '</tr>';
                            });
                            
                            html += '</table>';
                        }
                        
                        results.innerHTML = html;
                    }
                } catch (error) {
                    results.innerHTML = '<p style="color: red;">오류: ' + error.message + '</p>';
                } finally {
                    loading.style.display = 'none';
                }
            }
        </script>
    </body>
    </html>
    """

@app.get("/query/{query_type}")
async def execute_query(query_type: str):
    if query_type not in QUERIES:
        raise HTTPException(status_code=404, detail="Query not found")
    
    db_path = os.getenv("DATABASE_PATH", "./data/iacsgraph.db")
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(QUERIES[query_type])
        rows = cursor.fetchall()
        
        results = [dict(row) for row in rows]
        
        conn.close()
        
        return {
            "query_type": query_type,
            "count": len(results),
            "results": results
        }
        
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    print("🚀 Starting Simple Query Web Interface")
    print("📊 Open http://localhost:8888 in your browser")
    uvicorn.run(app, host="0.0.0.0", port=8888)