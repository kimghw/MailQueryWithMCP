"""Examples of using similarity calculator and vector store"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from modules.query_assistant.similarity_calculator import SimilarityCalculator, VectorStoreManager
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def example_two_sentence_similarity():
    """Example: Calculate similarity between two sentences"""
    print("\n" + "="*80)
    print("EXAMPLE 1: Two Sentence Similarity")
    print("="*80 + "\n")
    
    # Initialize calculator
    calc = SimilarityCalculator()
    
    # Define two sentences
    sentence1 = "최근 SDTP 패널에서 논의된 주요 아젠다는 무엇인가요?"
    sentence2 = "SDTP 패널의 최근 주요 의제들을 알려주세요."
    
    # Calculate similarity
    similarity = calc.calculate_similarity(sentence1, sentence2)
    
    print(f"Sentence 1: {sentence1}")
    print(f"Sentence 2: {sentence2}")
    print(f"\nCosine Similarity: {similarity:.4f}")
    print(f"Percentage: {similarity * 100:.2f}%")
    
    # Try with different sentences
    sentence3 = "KR의 응답률은 얼마나 되나요?"
    similarity2 = calc.calculate_similarity(sentence1, sentence3)
    
    print(f"\nSentence 1: {sentence1}")
    print(f"Sentence 3: {sentence3}")
    print(f"\nCosine Similarity: {similarity2:.4f}")
    print(f"Percentage: {similarity2 * 100:.2f}%")


def example_vector_store():
    """Example: Store texts in vector DB and search"""
    print("\n" + "="*80)
    print("EXAMPLE 2: Vector Store - Save and Search")
    print("="*80 + "\n")
    
    # Initialize vector store
    store = VectorStoreManager(collection_name="example_texts")
    
    # Sample texts to store
    texts = [
        "최근 SDTP 패널에서 논의된 주요 아젠다는 무엇인가요?",
        "KR의 응답률은 얼마나 되나요?",
        "미결정 상태의 아젠다 목록을 보여주세요.",
        "Hull Panel에서 진행 중인 의제를 확인하고 싶습니다.",
        "최근 3개월간 발행된 모든 의제를 조회해주세요.",
        "SDTP 의장이 보낸 메일 중 응답이 필요한 것들은?",
        "PL25016 의제의 현재 진행 상황은 어떻게 되나요?",
        "각 기관별 응답률을 비교해서 보여주세요.",
        "마감일이 지난 미완료 아젠다는 무엇인가요?",
        "올해 발생한 긴급 우선순위 의제들을 찾아주세요."
    ]
    
    # Add texts to vector store
    print("Adding texts to vector store...")
    text_ids = store.add_texts_batch(
        texts, 
        metadatas=[{"index": i, "category": "query"} for i in range(len(texts))]
    )
    print(f"Added {len(text_ids)} texts")
    
    # Get collection info
    info = store.get_collection_info()
    print(f"\nCollection info: {info}")
    
    # Search for similar texts
    query = "SDTP 패널의 최근 의제들이 궁금합니다."
    print(f"\nSearching for texts similar to: '{query}'")
    
    results = store.search_similar(query, limit=5, score_threshold=0.5)
    
    print(f"\nTop {len(results)} similar texts:")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. Score: {result['score']:.4f}")
        print(f"   Text: {result['text']}")
        print(f"   Metadata: {result['metadata']}")


def example_pairwise_similarity():
    """Example: Calculate pairwise similarities for 10 sentences"""
    print("\n" + "="*80)
    print("EXAMPLE 3: Pairwise Similarity Matrix (10 sentences)")
    print("="*80 + "\n")
    
    # Initialize calculator
    calc = SimilarityCalculator()
    
    # 10 sample sentences
    sentences = [
        "최근 SDTP 패널에서 논의된 주요 아젠다는?",
        "SDTP 패널의 최근 주요 의제들을 알려주세요.",
        "KR의 응답률은 얼마나 되나요?",
        "한국선급의 응답 비율을 확인하고 싶습니다.",
        "미결정 상태의 아젠다 목록을 보여주세요.",
        "아직 결정되지 않은 의제들은 무엇인가요?",
        "Hull Panel에서 진행 중인 의제는?",
        "Machinery Panel의 현재 논의 사항은?",
        "PL25016 의제의 진행 상황은?",
        "최근 3개월간 발행된 모든 의제 조회"
    ]
    
    # Calculate pairwise similarities
    print("Calculating pairwise similarities...")
    similarity_data = calc.calculate_pairwise_similarities(sentences)
    
    # Print similarity matrix
    calc.print_similarity_matrix(similarity_data, max_text_length=40)
    
    # Additional analysis
    print("\n=== Similarity Statistics ===\n")
    matrix = similarity_data["similarity_matrix"]
    
    # Exclude diagonal (self-similarities)
    off_diagonal = []
    n = len(sentences)
    for i in range(n):
        for j in range(n):
            if i != j:
                off_diagonal.append(matrix[i][j])
    
    import numpy as np
    print(f"Average similarity: {np.mean(off_diagonal):.4f}")
    print(f"Min similarity: {np.min(off_diagonal):.4f}")
    print(f"Max similarity: {np.max(off_diagonal):.4f}")
    print(f"Std deviation: {np.std(off_diagonal):.4f}")


def example_find_most_similar():
    """Example: Find most similar texts from a list"""
    print("\n" + "="*80)
    print("EXAMPLE 4: Find Most Similar Texts")
    print("="*80 + "\n")
    
    # Initialize calculator
    calc = SimilarityCalculator()
    
    # Query text
    query = "SDTP 패널에서 KR이 응답해야 하는 의제"
    
    # Candidate texts
    candidates = [
        "최근 SDTP 패널에서 논의된 주요 아젠다는 무엇인가요?",
        "KR의 응답률은 얼마나 되나요?",
        "SDTP에서 KR이 아직 응답하지 않은 의제 목록",
        "Hull Panel에서 진행 중인 의제를 확인하고 싶습니다.",
        "SDTP 의장이 보낸 메일 중 KR 응답이 필요한 것들",
        "각 기관별 응답률을 비교해서 보여주세요.",
        "PL25016 의제에 대한 KR의 응답 상태",
        "최근 3개월간 발행된 모든 의제를 조회해주세요.",
        "SDTP 패널의 미완료 의제 중 KR 관련 사항",
        "올해 발생한 긴급 우선순위 의제들을 찾아주세요."
    ]
    
    print(f"Query: {query}\n")
    print(f"Finding most similar from {len(candidates)} candidates...\n")
    
    # Find top 5 most similar
    results = calc.find_most_similar(query, candidates, top_k=5)
    
    print("Top 5 most similar texts:")
    for i, (idx, text, score) in enumerate(results, 1):
        print(f"\n{i}. Similarity: {score:.4f}")
        print(f"   Index: [{idx}]")
        print(f"   Text: {text}")


def main():
    """Run all examples"""
    # Check if API key is set
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Please set it using: export OPENAI_API_KEY='your-api-key'")
        return
    
    try:
        # Run examples
        example_two_sentence_similarity()
        example_vector_store()
        example_pairwise_similarity()
        example_find_most_similar()
        
        print("\n" + "="*80)
        print("All examples completed successfully!")
        print("="*80)
        
    except Exception as e:
        logger.error(f"Error running examples: {e}", exc_info=True)


if __name__ == "__main__":
    main()