"""Analyze similarity between multiple questions"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from modules.query_assistant.similarity_calculator import SimilarityCalculator
import numpy as np
from collections import defaultdict

def analyze_questions():
    # Initialize calculator
    calc = SimilarityCalculator()
    
    # All questions
    questions = [
        "최근 모든 패널에서 진행되고 있는 의제 목록",
        "최근 모든 패널에서 완료되지 않은 의제 리스트",
        "최근 3개월 동안 논의 되었던 의제 목록",
        "최근 SDTP 에서 논의 되었던 의제 목록",
        "최근 Hull Panel 에서 논의 되고 있는 의제 목록",
        "최근 Machinery Pannel 에서 논의되고 있는 의제 목록",
        "KR에서 SDTP 에서 응답한 내역",
        "진행되고 있는 의제들 중에서 KR 이 아직 응답하지 않는 의제",
        "최근 논의된 의제들 중에 {keywords} 에 대해서 논의되고 있는 의제",
        "KR이 응답을 해야 하는 의제",
        "SDTP 에서 KR이 응답해야 하는 의제",
        "최근 SDTP 의장이 최근 보낸 메일 목록",
        "최근 SDTP 의장이 보낸 메일 중 응답이 필요한 의제 목록",
        "SDTP 의장이 보낸 메일의 키워드들 알려줘",
        "최근 회의 개최관련 해서 알림을 준 메일",
        "최근 3년간 발행한 의제 중 SDTP 패널에서 한국선급 응답율",
        "최근 1년간 발행한 의제 중 SDTP 패널에서 한국선급 응답율",
        "올해 발행한 의제 중 SDTP 패널에서 한국선급 응답율",
        "최근 SDTP 패널에서 주요 키워드 출력 해줘",
        "최근 마감되지 않거나 KR이 응답하지 않은 의제 중에서 의장에 첨부파일을 송부한 의제",
        "PL25016 의제에서 현재 진행 중인가?",
        "PL25016 의제에서 현재 종료되었는가?",
        "PL25015 의제에서 KR이 응답을 하였는가?",
        "SDTP 에서 현재  응답을 한 기관은?",
        "SDTP 에서 현재 응답을 아직 하지 않은 기관은?",
        "올해 발생한 의제 중",
        "작년 각 패널 별 의제 별 개수",
        "작년 SDTP 패널에서 의제 별 개수",
        "올해 KR이 모든 패널에서 응답한 메일을 정리해줘",
        "최근 KR이 SDTP 패널에서 응답한 메일을 정리해줘",
        "최근 SDTP 아젠다 리스트",
        "PL25015 의제 내용",
        "PL25016의 응답현황",
        "PL25018의 미응듭 기관",
        "PL20123의 마감일",
        "SDPT 패널 의제 현황",
        "최근 SDTP 아젠다 중 미완료된 의제와 각 기관별 응답 내역 요약해줘",
        "최근 CCS에서 보낸 메일 요약해줘"
    ]
    
    print("="*80)
    print("질문 유사도 분석")
    print("="*80)
    print(f"\n총 {len(questions)}개 질문 분석\n")
    
    # Calculate pairwise similarities
    print("Calculating pairwise similarities... (this may take a moment)")
    similarity_data = calc.calculate_pairwise_similarities(questions)
    
    # Group similar questions (similarity > 0.7)
    groups = defaultdict(list)
    used_indices = set()
    
    pairs = similarity_data["pairs"]
    for i, j, sim in pairs:
        if sim > 0.7 and i not in used_indices:
            if i not in groups:
                groups[i] = [i]
            groups[i].append(j)
            used_indices.add(j)
    
    # Add ungrouped questions
    for i in range(len(questions)):
        if i not in used_indices and i not in groups:
            groups[i] = [i]
    
    # Print groups
    print("\n=== 유사 질문 그룹 (유사도 > 70%) ===\n")
    group_num = 1
    for leader, members in groups.items():
        if len(members) > 1:
            print(f"그룹 {group_num}:")
            for idx in members:
                print(f"  - [{idx}] {questions[idx]}")
            
            # Show similarity scores within group
            print("  유사도:")
            for i in range(len(members)):
                for j in range(i+1, len(members)):
                    sim = similarity_data["similarity_matrix"][members[i]][members[j]]
                    print(f"    [{members[i]}] ↔ [{members[j]}]: {sim:.2%}")
            print()
            group_num += 1
    
    # Find most/least similar pairs
    print("\n=== 가장 유사한 질문 쌍 (Top 10) ===\n")
    for i, (idx1, idx2, sim) in enumerate(pairs[:10]):
        print(f"{i+1}. 유사도: {sim:.2%}")
        print(f"   [{idx1}] {questions[idx1]}")
        print(f"   [{idx2}] {questions[idx2]}")
        print()
    
    print("\n=== 가장 다른 질문 쌍 (Bottom 5) ===\n")
    for i, (idx1, idx2, sim) in enumerate(pairs[-5:]):
        print(f"{i+1}. 유사도: {sim:.2%}")
        print(f"   [{idx1}] {questions[idx1]}")
        print(f"   [{idx2}] {questions[idx2]}")
        print()
    
    # Category analysis
    print("\n=== 카테고리별 분석 ===\n")
    
    # Define categories
    categories = {
        "패널별 의제": [0, 1, 2, 3, 4, 5, 30, 26, 27, 35, 36],
        "KR 응답 관련": [6, 7, 9, 10, 22, 28, 29],
        "응답률 통계": [15, 16, 17],
        "메일 관련": [11, 12, 13, 14, 37],
        "특정 의제": [20, 21, 22, 31, 32, 33, 34],
        "키워드": [8, 13, 18],
        "기관별 응답": [23, 24, 33]
    }
    
    for cat_name, indices in categories.items():
        print(f"{cat_name}:")
        valid_indices = [i for i in indices if i < len(questions)]
        if len(valid_indices) > 1:
            # Calculate average similarity within category
            sims = []
            for i in range(len(valid_indices)):
                for j in range(i+1, len(valid_indices)):
                    sims.append(similarity_data["similarity_matrix"][valid_indices[i]][valid_indices[j]])
            if sims:
                avg_sim = np.mean(sims)
                print(f"  평균 내부 유사도: {avg_sim:.2%}")
        print(f"  질문 수: {len(valid_indices)}")
        print()

if __name__ == "__main__":
    analyze_questions()