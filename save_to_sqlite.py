import sqlite3
import json
import os

DB_NAME = 'safepitch.db'
JSON_FILE = 'crew_output.json'

def init_db(conn):
    cursor = conn.cursor()
    # Create evaluations table (main record for each pitch evaluated)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            score INTEGER,
            reasoning TEXT
        )
    ''')
    
    # Create extracted_data table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS extracted_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evaluation_id INTEGER,
            field_name TEXT,
            field_value TEXT,
            FOREIGN KEY(evaluation_id) REFERENCES evaluations(id)
        )
    ''')
    
    # Create verified_data table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS verified_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evaluation_id INTEGER,
            field_name TEXT,
            field_value TEXT,
            source_url TEXT,
            FOREIGN KEY(evaluation_id) REFERENCES evaluations(id)
        )
    ''')
    
    # Create risk_analysis table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS risk_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evaluation_id INTEGER,
            flag_type TEXT,
            flag_title TEXT,
            description TEXT,
            FOREIGN KEY(evaluation_id) REFERENCES evaluations(id)
        )
    ''')
    conn.commit()

def load_data(conn, json_data):
    cursor = conn.cursor()
    
    # First extract top-level details or fallback to within the sections
    company_name = json_data.get('extracted_deck_data', {}).get('company_name', 'Unknown')
    score = json_data.get('scoring', {}).get('score') or json_data.get('score', 0)
    reasoning = json_data.get('scoring', {}).get('reasoning') or json_data.get('reasoning', '')
    
    # Insert evaluation record
    cursor.execute('''
        INSERT INTO evaluations (company_name, score, reasoning)
        VALUES (?, ?, ?)
    ''', (company_name, score, reasoning))
    evaluation_id = cursor.lastrowid
    
    # Insert extracted data (from the deck)
    extracted_data = json_data.get('extracted_deck_data', {})
    for k, v in extracted_data.items():
        val_str = json.dumps(v) if isinstance(v, (dict, list)) else str(v)
        cursor.execute('''
            INSERT INTO extracted_data (evaluation_id, field_name, field_value)
            VALUES (?, ?, ?)
        ''', (evaluation_id, k, val_str))
        
    # Insert verified data (from the internet)
    verified_data = json_data.get('internet_verified_data', {})
    for k, v in verified_data.items():
        if isinstance(v, dict):
            field_val = v.get('value', '')
            source = v.get('source_url', '')
            cursor.execute('''
                INSERT INTO verified_data (evaluation_id, field_name, field_value, source_url)
                VALUES (?, ?, ?, ?)
            ''', (evaluation_id, k, field_val, source))
            
    # Insert risk analysis (Red vs Green flags)
    risk_analysis = json_data.get('risk_analysis', {})
    for flag in risk_analysis.get('red_flags', []):
        cursor.execute('''
            INSERT INTO risk_analysis (evaluation_id, flag_type, flag_title, description)
            VALUES (?, ?, ?, ?)
        ''', (evaluation_id, 'red_flag', flag.get('flag', ''), flag.get('description', '')))
        
    for flag in risk_analysis.get('green_flags', []):
        cursor.execute('''
            INSERT INTO risk_analysis (evaluation_id, flag_type, flag_title, description)
            VALUES (?, ?, ?, ?)
        ''', (evaluation_id, 'green_flag', flag.get('flag', ''), flag.get('description', '')))
        
    conn.commit()

if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, JSON_FILE)
    
    if not os.path.exists(file_path):
        print(f"Error: {JSON_FILE} not found.")
        exit(1)
        
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    db_path = os.path.join(script_dir, DB_NAME)
    conn = sqlite3.connect(db_path)
    init_db(conn)
    load_data(conn, data)
    conn.close()
    
    print(f"Data successfully saved to {DB_NAME}")
