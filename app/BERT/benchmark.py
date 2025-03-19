import sqlite3
import os
from app.BERT.sbert_scorer import SBERTScorer
import time

def benchmark_keyword_sqlite(keyword_id: int):
    # Get data
    start = time.time()
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.abspath(os.path.join(
        current_dir, '..', '..', 'instance', 'app.db'
    ))
    
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Get keyword text
        cursor.execute("SELECT keyword_text FROM keywords WHERE keyword_id=?", (keyword_id,))
        keyword_text = cursor.fetchone()
        if not keyword_text:
            print("Keyword not found")
            return
            
        keyword_text = keyword_text[0]
        
        # Get items
        cursor.execute("""
            SELECT i.title 
            FROM keyword_items ki
            JOIN items i ON ki.item_id = i.item_id
            WHERE ki.keyword_id=?
        """, (keyword_id,))
        titles = [row[0] for row in cursor.fetchall()]
    
    fetch_time = time.time() - start

    total_number_of_items = len(titles)
    print(f"Total number of items: {total_number_of_items}")
    
    # Score items
    scorer = SBERTScorer()
    start_score = time.time()
    scores, indices = scorer.score(keyword_text, titles)
    score_time = time.time() - start_score
    
    ordered_scores = scores  # Already sorted descending
    ordered_titles = [titles[i] for i in indices]  # Titles in score order

    print("\nTop 50:")
    for rank, (score, title) in enumerate(zip(ordered_scores[:50], ordered_titles[:50]), 1):
        print(f"#{rank:2d} {score:.3f}: {title}")

    print("\nBottom 50:")
    for rank, (score, title) in enumerate(zip(ordered_scores[-50:], ordered_titles[-50:]), len(ordered_scores)-49):
        print(f"#{rank:2d} {score:.3f}: {title}")

if __name__ == "__main__":
    keyword_id = int(input("Enter keyword ID: "))
    benchmark_keyword_sqlite(keyword_id)