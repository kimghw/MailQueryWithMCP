#!/usr/bin/env python3
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import random

def create_test_data():
    db_path = Path("data/iacsgraph.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create agendas table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agendas (
            agenda_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'pending',
            organization_code TEXT,
            response_status TEXT DEFAULT 'pending',
            response_required BOOLEAN DEFAULT 0,
            priority TEXT DEFAULT 'medium',
            deadline DATE,
            keywords TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_discussed DATE
        )
    """)
    
    # Create comments table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            agenda_id INTEGER,
            comment_text TEXT,
            organization TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (agenda_id) REFERENCES agendas(agenda_id)
        )
    """)
    
    # Create responses table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS responses (
            response_id INTEGER PRIMARY KEY AUTOINCREMENT,
            agenda_id INTEGER,
            organization_code TEXT,
            response_keywords TEXT,
            importance TEXT DEFAULT 'medium',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (agenda_id) REFERENCES agendas(agenda_id)
        )
    """)
    
    # Sample data
    statuses = ['ongoing', 'completed', 'pending', 'in_review']
    organizations = ['KR', 'US', 'JP', 'EU', 'CN']
    priorities = ['high', 'medium', 'low']
    keywords_pool = ['보안', 'AI', '클라우드', '데이터', 'IoT', '5G', '블록체인', '사이버보안', '개인정보', '암호화']
    
    # Insert test agendas
    for i in range(50):
        days_ago = random.randint(0, 120)
        created_date = datetime.now() - timedelta(days=days_ago)
        
        title = f"의제 {i+1}: {random.choice(keywords_pool)} 관련 정책 논의"
        status = random.choice(statuses)
        org_code = random.choice(organizations)
        
        # KR 관련 의제는 응답 필요 설정
        response_required = 1 if org_code == 'KR' and random.random() > 0.3 else 0
        response_status = 'pending' if response_required else random.choice(['pending', 'responded', 'not_required'])
        
        cursor.execute("""
            INSERT INTO agendas (
                title, description, status, organization_code,
                response_status, response_required, priority,
                deadline, keywords, created_at, last_updated, last_discussed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            title,
            f"{title}에 대한 상세 설명입니다.",
            status,
            org_code,
            response_status,
            response_required,
            random.choice(priorities),
            (datetime.now() + timedelta(days=random.randint(7, 60))).strftime('%Y-%m-%d'),
            ','.join(random.sample(keywords_pool, k=random.randint(1, 3))),
            created_date.strftime('%Y-%m-%d %H:%M:%S'),
            created_date.strftime('%Y-%m-%d %H:%M:%S'),
            (created_date + timedelta(days=random.randint(0, 7))).strftime('%Y-%m-%d') if status != 'pending' else None
        ))
        
        agenda_id = cursor.lastrowid
        
        # Add comments for some agendas
        if random.random() > 0.5:
            for _ in range(random.randint(1, 3)):
                cursor.execute("""
                    INSERT INTO comments (agenda_id, comment_text, organization)
                    VALUES (?, ?, ?)
                """, (
                    agenda_id,
                    f"{random.choice(organizations)} 기관의 의견입니다.",
                    random.choice([o for o in organizations if o != org_code])
                ))
        
        # Add responses for some KR agendas
        if org_code == 'KR' and response_status == 'responded':
            cursor.execute("""
                INSERT INTO responses (agenda_id, organization_code, response_keywords, importance)
                VALUES (?, ?, ?, ?)
            """, (
                agenda_id,
                'KR',
                ','.join(random.sample(keywords_pool, k=random.randint(1, 2))),
                random.choice(['high', 'medium', 'low'])
            ))
    
    conn.commit()
    
    # Show statistics
    cursor.execute("SELECT COUNT(*) FROM agendas")
    total_agendas = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM agendas WHERE status = 'ongoing'")
    ongoing = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM agendas WHERE organization_code = 'KR' AND response_required = 1")
    kr_required = cursor.fetchone()[0]
    
    print("Test data created successfully!")
    print(f"- Total agendas: {total_agendas}")
    print(f"- Ongoing agendas: {ongoing}")
    print(f"- KR response required: {kr_required}")
    
    conn.close()

if __name__ == "__main__":
    create_test_data()