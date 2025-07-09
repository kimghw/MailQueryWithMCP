"""
/home/kimghw/IACSGRAPH/test2.py
"""

import sys
import json
from typing import Dict, List, Any
from collections import defaultdict
from datetime import datetime

# 프로젝트 루트 경로 추가
sys.path.append("/home/kimghw/IACSGRAPH")

# 실제 모듈 import
from modules.mail_process.utilities.iacs.iacs_code_parser import IACSCodeParser


def load_test_data() -> List[str]:
    """테스트 데이터 로드 - 전체 262개"""
    return [
        "PL25016_IRa: IMO Expert Group on Data Harmonization (EGDH) 13 Session",
        "PL25015_KRa: Recommendation on Network Monitoring (2nd SDTP Meeting, Agenda Item 5, FUA 6)",
        "PL25007bTLa IMO FAL Correspondence Group (CG) on IMO Strategy on Maritime Digitalization - Round 2",
        "Multilateral New SDTP Secretary",
        "PL25015_BVa: Recommendation on Network Monitoring (2nd SDTP Meeting, Agenda Item 5, FUA 6)",
        "PL25016_BVa: IMO Expert Group on Data Harmonization (EGDH) 13 Session",
        "PL25007bPRa IMO FAL Correspondence Group (CG) on IMO Strategy on Maritime Digitalization - Round 2",
        "PL25008cILc: IMO MSC 110 7 - IACS Brief - Cybersecurity - Final",
        "PL25016_ILa: IMO Expert Group on Data Harmonization (EGDH) 13 Session",
        "PL25007bBVa IMO FAL Correspondence Group (CG) on IMO Strategy on Maritime Digitalization Round 2",
        "PL25015_CRa: Recommendation on Network Monitoring (2nd SDTP Meeting, Agenda Item 5, FUA 6)",
        "PL25016_NVa: IMO Expert Group on Data Harmonization (EGDH) 13 Session",
        "PL25017_ILa - ISO TC8 SC26 1st Plenary Meeting - Observation Report of IACS liaison",
        "PL25007bRIa IMO FAL Correspondence Group (CG) on IMO Strategy on Maritime Digitalization - Round 2",
        "PL24035_ILf: IACS Recommendation on Vessel Asset Inventory - Approved by GPG (25083)",
        "PL25018_ILa: IMO NCSR 12 Guidelines for software maintenance of shipboard computer-based navigation and communication equipment and systems",
        "PL25015_IRa: Recommendation on Network Monitoring (2nd SDTP Meeting, Agenda Item 5, FUA 6)",
        "PL25015_NVa: Recommendation on Network Monitoring (2nd SDTP Meeting, Agenda Item 5, FUA 6)",
        "PL25016_TLa: IMO Expert Group on Data Harmonization (EGDH) 13 Session",
        "PL25007bILb IMO FAL Correspondence Group (CG) on IMO Strategy on Maritime Digitalization - Round 2",
        "PL24005_TLb: Email thread dedicated to track observations on published URs (2nd SDTP Meeting, Agenda item 19, FUA 13)",
        "PL25016_CCa: IMO Expert Group on Data Harmonization (EGDH) 13 Session",
        "Re: JWG-SDT25001a: IACS Recommendation on Cybersecurity Controls for existing ships - (PL24016) (23170)",
        "PL24005_IRc: Email thread dedicated to track observations on published URs (2nd SDTP Meeting, Agenda item 19, FUA 13)",
        "PL25007bKRa IMO FAL Correspondence Group (CG) on IMO Strategy on Maritime Digitalization - Round 2",
        "PL25008dILe: IMO MSC 110 5 - IACS Brief - MASS - Final",
        "PL25015_ILa: Recommendation on Network Monitoring (2nd SDTP Meeting, Agenda Item 5, FUA 6)",
        "IACS SDTP Fw: PL25015_ILa: Recommendation on Network Monitoring (2nd SDTP Meeting, Agenda Item 5, FUA 6) (안종우)",
        "PL25015_TLa: Recommendation on Network Monitoring (2nd SDTP Meeting, Agenda Item 5, FUA 6)",
        "Re: IACS SDTP Fw: PL25015_ILa: Recommendation on Network Monitoring (2nd SDTP Meeting, Agenda Item 5, FUA 6) (안종우)",
        "PL24005_PRb: Email thread dedicated to track observations on published URs (2nd SDTP Meeting, Agenda item 19, FUA 13)",
        "PL25008dLRb: IMO MSC 110 5 -IMO MSC 110 5 - Paper 5 13 - IACS Brief",
        "PL24005_NKd: Email thread dedicated to track observations on published URs (2nd SDTP Meeting, Agenda item 19, FUA 13)",
        "PL25007bABa: IMO FAL Correspondence Group (CG) on IMO Strategy on Maritime Digitalization - Round 2",
        "Re: JWG-SDT25001a: IACS Recommendation on Cybersecurity Controls for existing ships - (PL24016) (23170)",
        "PS25003pPLa MSC 110 (18-27 June 2025) - IACS Observer Report (25100e) (PL25008e)",
        "PL25008eILa: IMO MSC 110 - IACS Observer Report",
        "PL25016_PRa: IMO Expert Group on Data Harmonization (EGDH) 13 Session",
        "PL25015_ABa: Recommendation on Network Monitoring (2nd SDTP Meeting, Agenda Item 5, FUA 6)",
        "PL25016_ABa: IMO Expert Group on Data Harmonization (EGDH) 13 Session",
        "PL25015_CCa: Recommendation on Network Monitoring (2nd SDTP Meeting, Agenda Item 5, FUA 6)",
        "PL25008dLRa: IMO MSC 110 5 -IMO MSC 110 5 - Papers 5 4, 5 9, 5 10, 5 12 - IACS Brief",
        "PL25015_NKb: Recommendation on Network Monitoring (2nd SDTP Meeting, Agenda Item 5, FUA 6)",
        "PL25016_NKa: IMO Expert Group on Data Harmonization (EGDH) 13 Session",
        "IACS SDTP PL25007bILa IMO FAL Correspondence Group (CG) on IMO Strategy on Maritime Digitalization - Round 2(안종우)",
        "Fw: IACS SDTP Fw: PL25015_ILa: Recommendation on Network Monitoring (2nd SDTP Meeting, Agenda Item 5, FUA 6) (안종우)",
        "Re: PL24033_ILf: PTPL02 - Recommendation on 3D Model Exchange - Round 1",
        "PL25016_KRa: IMO Expert Group on Data Harmonization (EGDH) 13 Session",
        "PL25015_NKa: Recommendation on Network Monitoring (2nd SDTP Meeting, Agenda Item 5, FUA 6)",
        "PL25015_PRa: Recommendation on Network Monitoring (2nd SDTP Meeting, Agenda Item 5, FUA 6)",
        "테스트 Graph API 직접 테스트",
        "PL25008cIRa: IMO MSC 110 Paper 5 7, 7 - GPG NK comments",
        "PL25008aKRd: IMO MSC 110 5 - Papers 5 15, 5 16, 5 17, 5 18, 5 21 - To Review",
        "PL25012_NVa - Equasis - 25th Anniversary - Panel on Future of Equasis",
        "PL25012_IRa Equasis - 25th Anniversary - Panel on Future of Equasis",
        "PL25012_CRa Equasis - 25th Anniversary - Panel on Future of Equasis",
        "PL25008aNKc: IMO MSC 110 5 - Papers 5 13 To Review",
        "PL25013_LRa:3rd IACS Safe Digital Transformation Panel - Meeting Dates (Fall) (2nd SDTP Meeting, FUA 14)",
        "PL24005_NVb - : Email thread dedicated to track observations on published URs (2nd SDTP Meeting, Agenda item 19, FUA 13)",
        "PL25013_IRa:3rd IACS Safe Digital Transformation Panel - Meeting Dates (Fall) (2nd SDTP Meeting, FUA 14)",
        "PL25012_PRa Equasis - 25th Anniversary - Panel on Future of Equasis",
        "PL25013_TLa:3rd IACS Safe Digital Transformation Panel - Meeting Dates (Fall) (2nd SDTP Meeting, FUA 14)",
        "PL25012_TLa Equasis - 25th Anniversary - Panel on Future of Equasis",
        "PL25013_PRa:3rd IACS Safe Digital Transformation Panel - Meeting Dates (Fall) (2nd SDTP Meeting, FUA 14)",
        "PL25008aTLd: IMO MSC 110 5 - Papers 5 15, 5 16, 5 17, 5 18, 5 21 - To Review",
        "PL25012_NKa Equasis - 25th Anniversary - Panel on Future of Equasis",
        "PL25008aNVd: IMO MSC 110 5 -Papers 5 15, 5 16, 5 17, 5 18, 5 21 - To Review",
        "PL25008cILb: IMO MSC 110 Paper 5 7, 7 - GPG NK comments (24168)",
        "PL25013_ILb: 3rd IACS Safe Digital Transformation Panel Meeting (Fall) - Final Dates",
        "Automatic reply: PL25008aKRd: IMO MSC 110 5 - Papers 5 15, 5 16, 5 17, 5 18, 5 21 - To Review",
        "PL25014_ILa Tripartite 2024 JIWG on automated Fuel Consumption Data Gathering (24063c)",
        "PL25008aBVd: IMO MSC 110 5 - Papers 5 15, 5 16, 5 17, 5 18, 5 21 - To Review",
        "PL25008aPRc: IMO MSC 110 5 - Papers 5 13 To Review",
        "PL25008aCCc: IMO MSC 110 5 - Papers 5 13 To Review",
        "PL24005_BVc: Email thread dedicated to track observations on published URs (2nd SDTP Meeting, Agenda item 19, FUA 13)",
        "RE: PL25013_RIa:3rd IACS Safe Digital Transformation Panel - Meeting Dates (Fall) (2nd SDTP Meeting, FUA 14)",
        "PL25008aCRc: IMO MSC 110 5 - Papers 5 13 To Review",
        "PL25008cPRa: IMO MSC 110 Paper 5 7, 7 - GPG NK comments",
        "PL25008dILd: IMO MSC 110 5 - Papers 5 15, 5 16, 5 17, 5 18, 5 21- IACS Brief",
        "PL25008aLRa: IMO MSC 110 5 - Papers 5 13 To Review",
        "PL25013_ABa:3rd IACS Safe Digital Transformation Panel - Meeting Dates (Fall) (2nd SDTP Meeting, FUA 14)",
        "PL25007bILa IMO FAL Correspondence Group (CG) on IMO Strategy on Maritime Digitalization - Round 2",
        "PL25008cCCa: IMO MSC 110 Paper 5 7, 7 - GPG NK comments",
        "PL25008dILc: IMO MSC 110 5 -IMO MSC 110 5 - Paper 5 13 - IACS Brief",
        "PL25008cTLa: IMO MSC 110 Paper 5 7, 7 - GPG NK comments",
        "RE: JWG-SDT25001a: IACS Recommendation on Cybersecurity Controls for existing ships - (PL24016) (23170)",
        "Re: IACS SDTP Fw: PL24005_ILc: Email thread dedicated to track observations on published URs (2nd SDTP Meeting, Agenda item 19, FUA 13) (안종우 전달)",
        "PL25008cNVa: IMO MSC 110 Paper 5 7, 7 - GPG NK comments",
        "PL25008aNKd: IMO MSC 110 5 - Papers 5 15, 5 16, 5 17, 5 18, 5 21 - To Review",
        "PL25008aCCd: IMO MSC 110 5 - Papers 5 15, 5 16, 5 17, 5 18, 5 21 - To Review",
        "PL24005_ABc: Email thread dedicated to track observations on published URs (2nd SDTP Meeting, Agenda item 19, FUA 13)",
        "PL25012_CCa Equasis - 25th Anniversary - Panel on Future of Equasis",
        "PL25008aPRd: IMO MSC 110 5 - Papers 5 15, 5 16, 5 17, 5 18, 5 21 - To Review",
        "PL25008cNKa: IMO MSC 110 Paper 5 7, 7 - GPG NK comments",
        "PL25012_ILb Equasis - 25th Anniversary - Panel on Future of Equasis",
        "PL25005_ILc: Ship Data Quality - Formation of Small Task Team",
        "PL25013_CRa:3rd IACS Safe Digital Transformation Panel - Meeting Dates (Fall) (2nd SDTP Meeting, FUA 14)",
        "PL24016_CRe: PT PC09 Recommendation on Cybersecurity Controls for existing ships - 4th Draft (PC23020) (23170) 2nd SDTP Agenda Item 5, FUA 5",
        "PL25005_NVc: Ship Data Quality (2nd SDTP Meeting, Agenda item 7, FUA 9)",
        "JWG-CS25002b: JWG Revised Terms of Reference (ToR) - Final",
        "PL25008aCRb: IMO MSC 110 5 - Papers 5 4, 5 9, 5 10 - To Review, Paper 5 12 - To Note",
        "PL25002_ILd: JWG-SDT - Terms of Reference - Final Draft - Approved by GPG",
        "PL25008aILe: IMO MSC 110 5 - Papers 5 14 To Note",
        "PL25013_NVa - :3rd IACS Safe Digital Transformation Panel - Meeting Dates (Fall) (2nd SDTP Meeting, FUA 14)",
        "PL25008aTLb: IMO MSC 110 5 - Papers 5 4, 5 9, 5 10 - To Review, Paper 5 12 - To Note",
        "PL25008aNVc:IMO MSC 110 5 - Papers 5 13 To Review",
        "PL24016_BVd: PT PC09 Recommendation on Cybersecurity Controls for existing ships - 4th Draft (PC23020) (23170) 2nd SDTP Agenda Item 5, FUA 5",
        "PL24016_CCd: PT PC09 Recommendation on Cybersecurity Controls for existing ships - 4th Draft (PC23020) (23170) 2nd SDTP Agenda Item 5, FUA 5",
        "PL25008aCRa: IMO MSC 110 5 - Papers 5 1, 5 2, 5 3, 5 5, 5 6, 5 7, 5 8 - To Review",
        "JWG-CS25001e: 28th JWG-CS Meeting - Final MoM",
        "PL25013_BVa:3rd IACS Safe Digital Transformation Panel - Meeting Dates (Fall) (2nd SDTP Meeting, FUA 14)",
        "PL24016_TLe: PT PC09 Recommendation on Cybersecurity Controls for existing ships - 4th Draft (PC23020) (23170) 2nd SDTP Agenda Item 5, FUA 5",
        "PL25008cILa: IMO MSC 110 Paper 5 7, 7 - GPG NK comments",
        "PL25008aBVb: IMO MSC 110 5 - Papers 5 4, 5 9, 5 10 - To Review, Paper 5 12 - To Note",
        "PL24016_ILh: PT PC09 Recommendation on Cybersecurity Controls for existing ships - Final Draft (PC23020) (23170) 2nd SDTP Agenda Item 5, FUA 5",
        "JWG-SDT25001a: IACS Recommendation on Cybersecurity Controls for existing ships - (PL24016) (23170)",
        "PL25008aTLc: IMO MSC 110 5 - Papers 5 13 To Review",
        "PL25013_CCa:3rd IACS Safe Digital Transformation Panel - Meeting Dates (Fall) (2nd SDTP Meeting, FUA 14)",
        "PL25008aBVa: IMO MSC 110 5 - Papers 5 1, 5 2, 5 3, 5 5, 5 6, 5 7, 5 8 - To Review",
        "PL25008aIRa: IMO MSC 110 5 - Papers 5 1, 5 2, 5 3, 5 5, 5 6, 5 7, 5 8 - To Review",
        "PL24016_NVf: PT PC09 Recommendation on Cybersecurity Controls for existing ships - 4th Draft (PC23020) (23170) 2nd SDTP Agenda Item 5, FUA 5",
        "PL24016_IRg: PT PC09 Recommendation on Cybersecurity Controls for existing ships - 4th Draft (PC23020) (23170) 2nd SDTP Agenda Item 5, FUA 5",
        "PL25008aCCb: IMO MSC 110 5 - Papers 5 4, 5 9, 5 10 - To Review, Paper 5 12 - To Note",
        "PL25008aILf: IMO MSC 110 5 - Papers 5 15, 5 16, 5 17, 5 18, 5 21 - To Review",
        "PL24016_NKe: PT PC09 Recommendation on Cybersecurity Controls for existing ships - 4th Draft (PC23020) (23170) 2nd SDTP Agenda Item 5, FUA 5",
        "PL25008aNVb: IMO MSC 110 5 - Papers 5 4, 5 9, 5 10 - To Review, Paper 5 12 - To Note",
        "PL24016_PRd: PT PC09 Recommendation on Cybersecurity Controls for existing ships - 4th Draft (PC23020) (23170) 2nd SDTP Agenda Item 5, FUA 5",
        "PL24035_ILe: IACS Recommendation on Vessel Asset Inventory - Final",
        "PL24016_NKd: PT PC09 Recommendation on Cybersecurity Controls for existing ships - 4th Draft (PC23020) (23170) 2nd SDTP Agenda Item 5, FUA 5",
        "PL25008aIRb: IMO MSC 110 5 - Papers 5 4, 5 9, 5 10 - To Review, Paper 5 12 - To Note",
        "PL25008aNVa: IMO MSC 110 5 - Papers 5 1, 5 2, 5 3, 5 5, 5 6, 5 7, 5 8 - To Review",
        "PL24016_ABd: PT PC09 Recommendation on Cybersecurity Controls for existing ships - 4th Draft (PC23020) (23170) 2nd SDTP Agenda Item 5, FUA 5",
        "PL24005_ILc: Email thread dedicated to track observations on published URs (2nd SDTP Meeting, Agenda item 19, FUA 13)",
        "PL25008aPRb: IMO MSC 110 5 - Papers 5 4, 5 9, 5 10 - To Review, Paper 5 12 - To Note",
        "PL25008aPRa: IMO MSC 110 5 - Papers 5 1, 5 2, 5 3, 5 5, 5 6, 5 7, 5 8 - To Review",
        "PL25008dILa: IMO MSC 110 5 - Papers 5 1, 5 2, 5 3, 5 5, 5 6, 5 7, 5 8 - IACS Brief",
        "PL25008aCCa: IMO MSC 110 5 - Papers 5 1, 5 2, 5 3, 5 5, 5 6, 5 7, 5 8 - To Review",
        "PL25013_ILa:3rd IACS Safe Digital Transformation Panel - Meeting Dates (Fall) (2nd SDTP Meeting, FUA 14)",
        "PL25008aNKa: IMO MSC 110 5 - Papers 5 1, 5 2, 5 3, 5 5, 5 6, 5 7, 5 8 - To Review",
        "PL25008dILb: IMO MSC 110 5 -IMO MSC 110 5 - Papers 5 4, 5 9, 5 10, 5 12 - IACS Brief",
        "PL25008aNKb: IMO MSC 110 5 - Papers 5 4, 5 9, 5 10 - To Review, Paper 5 12 - To Note",
        "RE: PL24016_ILg: PT PC09 Recommendation on Cybersecurity Controls for existing ships - 4th Draft (PC23020) (23170) 2nd SDTP Agenda Item 5, FUA 5",
        "PL25008aIRc: IMO MSC 110 5 - Papers 5 13 To Review",
        "PL25008aBVc: IMO MSC 110 5 - Papers 5 13 To Review",
        "PL24037bBVa: 2nd IACS Safe Digital Transformation Panel Meeting (Spring) Draft MoM and FUAs",
        "PL25008bILb: IMO MSC 110 7 - Papers 7 2 - To Note",
        "PL24035_IRd: IACS Recommendation on Vessel Asset Inventory - 2nd Draft",
        "PL24035_BVb: IACS Recommendation on Vessel Asset Inventory - 2nd Draft",
        "PL24037bILb: 2nd IACS Safe Digital Transformation Panel Meeting (Spring) - Final MoM and FUAs",
        "PL25007aNVa IMO FAL Correspondence Group (CG) on IMO Strategy on Maritime Digitalization - Round 1",
        "PL25005_TLb: Ship Data Quality (2nd SDTP Meeting, Agenda item 7, FUA 9)",
        "PL24037bIRa: 2nd IACS Safe Digital Transformation Panel Meeting (Spring) Draft MoM and FUAs",
        "PL25007aTLa IMO FAL Correspondence Group (CG) on IMO Strategy on Maritime Digitalization - Round 1",
        "PL25005_NKb: Ship Data Quality (2nd SDTP Meeting, Agenda item 7, FUA 9)",
        "PL25007_BVa IMO FAL Correspondence Group (CG) on IMO Strategy on Maritime Digitalization Round 1",
        "PL24042bIRb: IMO FAL 49 Observer Report and Proposed Actions (24192d)",
        "PL25007aPRa IMO FAL Correspondence Group (CG) on IMO Strategy on Maritime Digitalization - Round 1",
        "PL25007aCCa IMO FAL Correspondence Group (CG) on IMO Strategy on Maritime Digitalization - Round 1",
        "PL25009_ABa IACS Industry IUMI Meeting 2025 (25036_)",
        "PL24042bTLb: IMO FAL 49 Observer Report and Proposed Actions (24192d)",
        "PL24035_TLb: IACS Recommendation on Vessel Asset Inventory - 2nd Draft",
        "PL25005_ABb: Ship Data Quality (2nd SDTP Meeting, Agenda item 7, FUA 9)",
        "PL24037bNKa: 2nd IACS Safe Digital Transformation Panel Meeting (Spring) Draft MoM and FUAs",
        "PL25009_ILb IACS Industry IUMI Meeting 2025 (25036_)",
        "PL25007aABa IMO FAL Correspondence Group (CG) on IMO Strategy on Maritime Digitalization - Round 1",
        "PL25005_IRb: Ship Data Quality (2nd SDTP Meeting, Agenda item 7, FUA 9)",
        "PL24042bNKb: IMO FAL 49 Observer Report and Proposed Actions (24192d)",
        "PL25011_ABa: IACS Industry Meeting 2025 (25035_)",
        "PL24016_ILg: PT PC09 Recommendation on Cybersecurity Controls for existing ships - 4th Draft (PC23020) (23170) 2nd SDTP Agenda Item 5, FUA 5",
        "PL24042bPRb: IMO FAL 49 Observer Report and Proposed Actions (24192d)",
        "PL24042bILc: IMO FAL 49 Observer Report and Proposed Actions (24192d) - IACS Representative to IMO CG of FAL",
        "PL25008aTLa: IMO MSC 110 5 - Papers 5 1, 5 2, 5 3, 5 5, 5 6, 5 7, 5 8 - To Review",
        "PL25008aILb: IMO MSC 110 5 - Papers 5 4, 5 9, 5 10 - To Review, Paper 5 12 - To Note",
        "PL25011_ILa IACS Industry Meeting 2025 (25035_)",
        "PL25010_ILa Tripartite Meeting 2024 - Outcomes (2nd SDTP Meeting, FUA 2)",
        "PL25007aIRa IMO FAL Correspondence Group (CG) on IMO Strategy on Maritime Digitalization - Round 1",
        "PL24035_NKb: IACS Recommendation on Vessel Asset Inventory - 2nd Draft",
        "PL24035_ABa: IACS Recommendation on Vessel Asset Inventory - 2nd Draft",
        "PL25007aILb IMO FAL Correspondence Group (CG) on IMO Strategy on Maritime Digitalization - Round 1",
        "PL25008aILd: IMO MSC 110 5 - Papers 5 11, 5 19, INF.16, INF.17, INF.25 To Note",
        "PL24035_CCb: IACS Recommendation on Vessel Asset Inventory - 2nd Draft",
        "PL25007aKRa IMO FAL Correspondence Group (CG) on IMO Strategy on Maritime Digitalization - Round 1",
        "PL24042bCRa: IMO FAL 49 Observer Report and Proposed Actions (24192d)",
        "PL24042bBVa: IMO FAL 49 Observer Report and Proposed Actions (24192d)",
        "PL24042bILb: IMO FAL 49 Observer Report and Proposed Actions (24192d)",
        "PL24037bCRa: 2nd IACS Safe Digital Transformation Panel Meeting (Spring) Draft MoM and FUAs",
        "PL24035_NVc: IACS Recommendation on Vessel Asset Inventory - 2nd Draft",
        "PL24037bNVa: 2nd IACS Safe Digital Transformation Panel Meeting (Spring) Draft MoM and FUAs",
        "JWG-CS25001c: 28th JWG-CS Meeting - Final Agenda",
        "2nd IACS Safe Digital Transformation Panel - Day 1",
        "2nd IACS Safe Digital Transformation Panel Meeting Day - 2.",
        "PL24042bTLa: IMO FAL 49 Observer Report and Proposed Actions (24192d)",
        "PL25005_ILb: Ship Data Quality (2nd SDTP Meeting, Agenda item 7, FUA 9)",
        "PL25007aILa IMO FAL Correspondence Group (CG) on IMO Strategy on Maritime Digitalization - Round 1",
        "PL25005_NVb:Ship Data Quality (2nd SDTP Meeting, Agenda item 7, FUA 9)",
        "PL24037bILa: 2nd IACS Safe Digital Transformation Panel Meeting (Spring) Draft MoM and FUAs",
        "PL24035_ILd: IACS Recommendation on Vessel Asset Inventory - 2nd Draft",
        "PL24042bNVa: IMO FAL 49 Observer Report and Proposed Actions (24192d)",
        "JWG-CS25001d: 28th JWG-CS Meeting - Draft MoM",
        "PL25005_NKa: Ship Data Quality (1st SDTP Meeting, Agenda item 13, FUA 5)",
        "RE: PL24035_NVc: IACS Recommendation on Vessel Asset Inventory - 2nd Draft",
        "PL24005_TLa: Email thread dedicated to track observations on published URs (1st SDTP Meeting, Agenda item 7, FUA 4)",
        "PL24005_LRa: Email thread dedicated to track observations on published URs (1st SDTP Meeting, Agenda item 7, FUA 4)",
        "PL25006_PRa: Survey Engagement - JWG SDT",
        "PL25006_NKa: Survey Engagement - JWG SDT",
        "PL24031dILd: MSC 109 IACS Observer Report - Revised (24015zc, 25005_)",
        "PL25005_CRb: Ship Data Quality (2nd SDTP Meeting, Agenda item 7, FUA 9)",
        "Multilateral The Standard IACS Backdrop for IACS representatives attending external online Teams Meetings",
        "IACS SDTP Fw: PL25007aILa IMO FAL Correspondence Group (CG) on IMO Strategy on Maritime Digitalization - Round 1 (안종우)",
        "PL24005_NVa - : Interpretation of E26 4.2.1.3: Network devices to be certified to E27",
        "PL24041_ILg: PT PL04 Recommendation on Risk Assessment for MASS - Forms 1 (25003_)",
        "PL24042bPRa: IMO FAL 49 Observer Report and Proposed Actions (24192d)",
        "RE: PL24005_NVa - : Interpretation of E26 4.2.1.3: Network devices to be certified to E27",
        "PL25007aILa IMO FAL Correspondence Group (CG) on IMO Strategy on Maritime Digitalization - Round 1",
        "PL24042bCCb: IMO FAL 49 Observer Report and Proposed Actions (24192d)",
        "PL24041_ILg: PT PL04 Recommendation on Remote Connectivity and Communications for MASS - Forms 1 (25003_)",
        "PL24042bABa: IMO FAL 49 Observer Report and Proposed Actions (24192d)",
        "PL24041_ILh: PT PL04 Recommendation on Remote Connectivity and Communications for MASS - Forms 1 - Approved by GPG (25003_)",
        "PL24042bIRa: IMO FAL 49 Observer Report and Proposed Actions (24192d)",
        "RE: PL24016_ILf: PT PC09 Recommendation on Cyber Security Controls for ships in service - 3rd Draft (PC23020) (23170)",
        "JWG-CS25001b_PRa: 28th JWG-CS Meeting - Draft Agenda",
        "PL24017hCRa MSC MASS Correspondence Group (CG) - MASS Code Final Questions (23195oIGa)",
        "PL25006_BVa: Survey Engagement - JWG SDT",
        "PL25005_NVa: Ship Data Quality (1st SDTP Meeting, Agenda item 13, FUA 5)",
        "PL24017hIRa MSC MASS Correspondence Group (CG) - MASS Code Final Questions (23195oIGa)",
        "PL25005_CRa: Ship Data Quality (1st SDTP Meeting, Agenda item 13, FUA 5)",
        "PL25005_IRa: Ship Data Quality (1st SDTP Meeting, Agenda item 13, FUA 5)",
        "RE: PL24041_KRd: PT PL04 Recommendation on Remote Connectivity and Communications for MASS - Forms 1",
        "PL24017hILa MSC MASS Correspondence Group (CG) - MASS Code Final Questions (23195oIGa)",
        "PL25005_RIa: Ship Data Quality (1st SDTP Meeting, Agenda item 13, FUA 5)",
        "PL24005_BVb: Email thread dedicated to track observations on published URs (1st SDTP Meeting, Agenda item 7, FUA 4)",
        "PL24037aCRa: 2nd IACS Safe Digital Transformation Panel Meeting (Spring) Draft Agenda",
        "PL24017hNVa -MSC MASS Correspondence Group (CG) - MASS Code Final Questions (23195oIGa)",
        "PL24017hBVa MSC MASS Correspondence Group (CG) - MASS Code Final Questions (23195oIGa)",
        "PL24016_CRd: PT PC09 Recommendation on Cyber Security Controls for ships in service - 3rd Draft (PC23020) (23170)",
        "PL24016_BVc: PT PC09 Recommendation on Cyber Security Controls for ships in service - 3rd Draft (PC23020) (23170)",
        "PL24037aTLa: 2nd IACS Safe Digital Transformation Panel Meeting (Spring) Draft Agenda",
        "PL25005_TLa: Ship Data Quality (1st SDTP Meeting, Agenda item 13, FUA 5)",
        "PL24017hTLa MSC MASS Correspondence Group (CG) - MASS Code Final Questions (23195oIGa)",
        "PL25006_TLa: Survey Engagement - JWG SDT",
        "JWG-CS25001bKRa: 28th JWG-CS Meeting - Draft Agenda",
        "RE: PL24016_RIa: PT PC09 Recommendation on Cyber Security Controls for ships in service - 3rd Draft (PC23020) (23170)",
        "PL24037aIRa: 2nd IACS Safe Digital Transformation Panel Meeting (Spring) Draft Agenda",
        "PL24037aPRa: 2nd IACS Safe Digital Transformation Panel Meeting (Spring) Draft Agenda",
        "PL25005_CCa: Ship Data Quality (1st SDTP Meeting, Agenda item 13, FUA 5)",
        "JWG-CS25001bRIa: 28th JWG-CS Meeting - Draft Agenda",
        "PL24037aILb: 2nd IACS Safe Digital Transformation Panel Meeting (Spring) Final Agenda",
        "PL24037aBVa: 2nd IACS Safe Digital Transformation Panel Meeting (Spring) Draft Agenda",
        "PL24037aNVa: 2nd IACS Safe Digital Transformation Panel Meeting (Spring) Draft Agenda",
        "PL24017hILb MSC MASS Correspondence Group (CG) - MASS Report to MSC 110 (23195oIGa)",
        "PL24037aCCa: 2nd IACS Safe Digital Transformation Panel Meeting (Spring) Draft Agenda",
        "PL24017hABa: MSC MASS Correspondence Group (CG) - MASS Code Final Questions (23195oIGa)",
        "PL24016_PRc: PT PC09 Recommendation on Cyber Security Controls for ships in service - 3rd Draft (PC23020) (23170)",
        "PL25005_ABa: Ship Data Quality (1st SDTP Meeting, Agenda item 13, FUA 5)",
        "PL24017hCCa MSC MASS Correspondence Group (CG) - MASS Code Final Questions (23195oIGa)",
        "PL24016_NKc: PT PC09 Recommendation on Cyber Security Controls for ships in service - 3rd Draft (PC23020) (23170)",
        "PL24017hPRa MSC MASS Correspondence Group (CG) - MASS Code Final Questions (23195oIGa)",
        "PL24037aNKa: 2nd IACS Safe Digital Transformation Panel Meeting (Spring) Draft Agenda",
        "Re: Bilateral PL24035_ILc: IACS Recommendation on HW SW Inventory Template for CBSs onboard - 1st Draft - KR Comments",
        "PL24017hNKa MSC MASS Correspondence Group (CG) - MASS Code Final Questions (23195oIGa)",
        "PL24030_ILf: Digital Twins - White Paper - Part 1",
        "PL24005_ABa: Additional item for the Email thread dedicated to track observations on published URs (1st SDTP Meeting, Agenda item 7, FUA 4)",
    ]


def create_mock_mail(subject: str) -> Dict[str, Any]:
    """테스트용 가짜 메일 데이터 생성"""
    # 현재 시간
    current_time = datetime.now()

    # 발신자 이메일 예시 (도메인 기반으로 조직 추출)
    sender_emails = {
        "IL": "chair@iacs.org.uk",
        "KR": "member@krs.co.kr",
        "BV": "contact@bureauveritas.com",
        "NK": "info@classnk.or.jp",
        "LR": "admin@lr.org",
        "DNV": "support@dnv.com",
        "ABS": "service@eagle.org",
        "CCS": "mail@ccs.org.cn",
        "RINA": "contact@rina.org",
        "PR": "info@prs.pl",
        "TL": "admin@turkloydu.org",
        "CR": "service@crs.hr",
        "IR": "contact@irclass.org",
        "CC": "info@chinaccs.com",
        "AB": "abs@abs-group.com",
        "NV": "nv@dnv.com",
        "RI": "ri@rina.it",
        "PL": "pl@prs.pl",
    }

    # 제목에서 조직 코드 추출 시도
    org_code = None
    for code in sender_emails.keys():
        if f"_{code}" in subject or f"{code}a" in subject or f"{code}b" in subject:
            org_code = code
            break

    # 기본값: IL (Chair)
    if not org_code:
        org_code = "IL"

    sender_email = sender_emails.get(org_code, "unknown@example.com")

    return {
        "id": f"test-{hash(subject)}",
        "subject": subject,
        "from": {
            "emailAddress": {"address": sender_email, "name": f"Test User ({org_code})"}
        },
        "receivedDateTime": current_time,
        "body": {"content": f"This is a test email for: {subject}"},
    }


def analyze_parsing_results(
    parser: IACSCodeParser, test_subjects: List[str]
) -> Dict[str, Any]:
    """파싱 결과 분석 - extracted_info 형식"""
    results = {
        "total": len(test_subjects),
        "parsed": 0,
        "failed": 0,
        "special": 0,
        "by_type": defaultdict(int),
        "by_panel": defaultdict(int),
        "by_organization": defaultdict(int),
        "by_parsing_method": defaultdict(int),
        "failed_subjects": [],
        "extracted_info_list": [],  # extracted_info 형식으로 저장
    }

    # Chair 이메일 설정 (IL은 보통 Chair)
    parser.set_chair_emails(["chair@iacs.org.uk", "chair@iscsmaritime.com"])

    # 멤버 이메일 설정 예시
    parser.set_member_emails("KR", ["member@krs.co.kr", "admin@krs.co.kr"])
    parser.set_member_emails("BV", ["contact@bureauveritas.com"])

    for subject in test_subjects:
        # 가짜 메일 생성
        mail = create_mock_mail(subject)

        # extract_all_patterns 호출
        patterns = parser.extract_all_patterns(subject, "", mail)

        if "extracted_info" in patterns:
            results["parsed"] += 1
            extracted_info = patterns["extracted_info"]

            # 파싱 성공/실패 체크
            if extracted_info.get("parsing_method") != "failed":
                # 타입별 집계
                if "iacs_code" in patterns:
                    parsed = patterns["iacs_code"]
                    results["by_type"][parsed.document_type] += 1
                    results["by_panel"][parsed.panel] += 1
                    if parsed.organization:
                        results["by_organization"][parsed.organization] += 1
                    if parsed.is_special:
                        results["special"] += 1

                # parsing_method 집계
                if extracted_info.get("parsing_method"):
                    results["by_parsing_method"][extracted_info["parsing_method"]] += 1

            # extracted_info 리스트에 추가
            results["extracted_info_list"].append(extracted_info)
        else:
            results["failed"] += 1
            results["failed_subjects"].append(subject)

            # 파싱 실패한 경우도 기본 정보 포함
            failed_info = {
                "parsing_method": "failed",
                "agenda_code": None,
                "agenda_base": None,
                "agenda_panel": None,
                "sent_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
                "sender_type": "OTHER",
                "sender_organization": None,
            }
            results["extracted_info_list"].append(failed_info)

    return results


def print_results(results: Dict[str, Any]):
    """결과 출력"""
    print("=" * 80)
    print("IACS 코드 파서 테스트 결과 (extracted_info 형식)")
    print("=" * 80)

    # 전체 통계
    print(f"\n[전체 통계]")
    print(f"총 테스트: {results['total']}개")
    print(
        f"파싱 성공: {results['parsed']}개 ({results['parsed']/results['total']*100:.1f}%)"
    )
    print(
        f"파싱 실패: {results['failed']}개 ({results['failed']/results['total']*100:.1f}%)"
    )
    if results["special"] > 0:
        print(f"특수 케이스: {results['special']}개")

    # 문서 타입별 통계
    print(f"\n[문서 타입별]")
    for doc_type, count in sorted(results["by_type"].items()):
        print(f"  {doc_type}: {count}개")

    # 패널별 통계
    print(f"\n[패널별]")
    for panel, count in sorted(results["by_panel"].items()):
        print(f"  {panel}: {count}개")

    # 기관별 통계
    if results["by_organization"]:
        print(f"\n[기관별 응답]")
        for org, count in sorted(results["by_organization"].items()):
            print(f"  {org}: {count}개")

    # extracted_info 예시 (처음 10개)
    print(f"\n[extracted_info 예시] (처음 10개)")
    for i, info in enumerate(results["extracted_info_list"][:10]):
        print(f"\n{i+1}. extracted_info:")
        print(json.dumps(info, indent=4, ensure_ascii=False))


def save_results_to_json(
    results: Dict[str, Any],
    filename: str = "/home/kimghw/IACSGRAPH/data/result/iacs_parser_extracted_info_results.json",
):
    """결과를 JSON 파일로 저장 - extracted_info 형식만"""
    # extracted_info 리스트만 저장
    output_data = {
        "total": results["total"],
        "parsed": results["parsed"],
        "failed": results["failed"],
        "extracted_info_list": results["extracted_info_list"],
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\n결과가 {filename} 파일로 저장되었습니다.")
    print(f"저장된 extracted_info 개수: {len(results['extracted_info_list'])}개")


def main():
    """메인 함수"""
    print("IACS 코드 파서 테스트 시작 (extracted_info 형식)")
    print(f"모듈 경로: /home/kimghw/IACSGRAPH/modules/mail_process/utilities/iacs/")

    try:
        # 파서 초기화
        parser = IACSCodeParser()
        print("✓ 파서 초기화 성공")

        # 테스트 데이터 로드
        test_subjects = load_test_data()
        print(f"✓ 테스트 데이터 로드: {len(test_subjects)}개")

        # 파싱 결과 분석
        results = analyze_parsing_results(parser, test_subjects)

        # 결과 출력
        print_results(results)

        # 결과 저장
        save_results_to_json(results)

        # 파싱 방법별 통계
        print("\n[파싱 방법별 통계]")
        for method, count in sorted(results["by_parsing_method"].items()):
            print(f"  {method}: {count}개")

    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
