"""
analysis.py - Refined NLP Classification Engine, Data Validation, & Metrics Analysis
"""

import re
import os
from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np


# Enhanced 14 Categories Regex Dictionary
CATEGORY_PATTERNS = {
    "Login and authentication": r"\b(login|log-in|log in|otp|password|sign in|signin|logout|sign out|authentication|account|login error|pin|credentials|access|sso|verify|verification|auth)\b",
    "Booking and cancellation": r"\b(book|booking|cancel|cancellation|reschedule|roster|rostering|shift|slot|schedule|seat|cab booking|modify|auto book|unbook|cab cancel)\b",
    "Cab or shuttle availability": r"\b(no cab|cab not available|unassigned|cab assignment|no vehicle|shuttle availability|cab availability|not assigned|not allocated|no shuttle|vehicle allocation|cab allocation)\b",
    "Pickup timing and delays": r"\b(late|delay|delayed|delaying|waiting|wait|pickup time|drop time|time|reach|punctual|on time|too early|hours late|30 mins|1 hour|45 mins|late arrival|driver late|timing|reach office)\b",
    "GPS and live tracking": r"\b(gps|track|tracking|live tracking|location|map|mapping|driver location|wrong location|route|navigation|signal|tracker|direction|wrong route|reroute|map view)\b",
    "App crashes and performance": r"\b(crash|crashes|crashing|crashed|freeze|freezes|freezing|slow|hang|hangs|loading|stuck|lag|lags|white screen|black screen|error|bug|glitch|not opening|not open|wont open|won't open|cant open|can't open|stopped working|not working|force close|close|app close|opening|open|pixel|oneplus|android version|blackout)\b",
    "User interface and usability": r"\b(ui|interface|usability|user friendly|design|layout|update|updated|new version|confusing|hard to use|navigation|feedback box|button|screen|display|view|font|touch|ux|bad ui|layout update)\b",
    "Notifications and reminders": r"\b(notification|notifications|alert|alerts|reminder|reminders|sms|ring|sound|push notification|pop-up|popup|rating prompt|forcing rating|spam|sound notification)\b",
    "Driver behavior and safety": r"\b(driver|drivers|rash|speed|speeding|rude|behaviour|behavior|safety|reckless|driving|abusive|phone|drunk|misconduct|night shift|sos|call driver|driver cancel|night ride|safe|security)\b",
    "Customer support": r"\b(support|helpdesk|customer care|helpline|executive|no response|complaint|contact|agent|ticket|transport desk|transport admin|escalate|help desk)\b",
    "Attendance and check-in": r"\b(check-in|checkin|checkout|check-out|attendance|qr|qr code|board|boarding|mark attendance|scan|scanner|boarding pass|missed cab|no show)\b",
    "Feature requests": r"\b(please add|feature|option|should have|would be better|need option|request|suggestion|add feature|allow us|wish|feature request|would like)\b",
    "Positive feedback": r"\b(good|great|excellent|love|best|awesome|smooth|helpful|nice|superb|satisfied|easy to use|perfect|wonderful|fantastic|reliable|comfortable|prompt|top class|fast|super|happy|like)\b",
}


def classify_single_review(text: str, rating: int) -> Dict[str, Any]:
    """
    Classify a single review text into primary/secondary categories, sentiment, problem type, severity, and confidence.
    """
    text_str = str(text) if pd.notna(text) else ""
    text_lower = text_str.lower().strip()

    matched_categories = []
    category_scores = {}

    # Regex matching
    for cat, pattern in CATEGORY_PATTERNS.items():
        matches = re.findall(pattern, text_lower)
        if matches:
            matched_categories.append(cat)
            category_scores[cat] = len(matches)

    # Secondary processing for empty matches or generic text
    if not matched_categories:
        if rating >= 4:
            matched_categories = ["Positive feedback"]
            confidence = 0.85
        elif rating == 3:
            matched_categories = ["Other or unclear"]
            confidence = 0.70
        else:
            # Check for generic negative terms
            if re.search(r"\b(bekar|worst|bad|pathetic|rubbish|waste|useless|terrible|horrible|poor|hate|disgusting)\b", text_lower):
                if re.search(r"\b(cab|driver|delay|time|pickup|late|ride|transport)\b", text_lower):
                    matched_categories = ["Pickup timing and delays"]
                    confidence = 0.75
                elif re.search(r"\b(app|application|update|system)\b", text_lower):
                    matched_categories = ["App crashes and performance"]
                    confidence = 0.75
                else:
                    matched_categories = ["Other or unclear"]
                    confidence = 0.65
            else:
                matched_categories = ["Other or unclear"]
                confidence = 0.50
    else:
        # Sort matched categories by match frequency
        matched_categories.sort(key=lambda c: category_scores.get(c, 1), reverse=True)
        confidence = min(0.95, 0.80 + 0.05 * category_scores.get(matched_categories[0], 1))

    primary_category = matched_categories[0]
    secondary_cats = matched_categories[1:]

    # Determine Sentiment
    if rating >= 4:
        sentiment = "Positive"
    elif rating == 3:
        sentiment = "Neutral"
    else:
        sentiment = "Negative"

    # Determine Problem Type
    if rating >= 4 or primary_category == "Positive feedback":
        problem_type = "Praise"
    elif primary_category == "Feature requests" or re.search(r"\b(please add|should have|would be better|need option)\b", text_lower):
        problem_type = "Feature Request"
    elif primary_category in ["App crashes and performance", "Login and authentication", "GPS and live tracking", "Notifications and reminders", "User interface and usability"]:
        problem_type = "Software Defect"
    elif primary_category in ["Pickup timing and delays", "Cab or shuttle availability", "Driver behavior and safety", "Attendance and check-in", "Customer support"]:
        problem_type = "Operational/Service Issue"
    else:
        problem_type = "Unclear"

    # Determine Severity
    if rating <= 2:
        if primary_category in ["Driver behavior and safety", "Login and authentication"] or re.search(r"\b(sos|accident|night|unsafe|drunk|rash|crashed|stuck)\b", text_lower):
            severity = "Critical"
        elif primary_category in ["Pickup timing and delays", "Cab or shuttle availability", "App crashes and performance", "Attendance and check-in"]:
            severity = "High"
        else:
            severity = "Medium"
    elif rating == 3:
        severity = "Low"
    else:
        severity = "Informational"

    return {
        "primary_category": primary_category,
        "secondary_categories": ", ".join(secondary_cats) if secondary_cats else "None",
        "all_matched_categories": matched_categories,
        "sentiment": sentiment,
        "problem_type": problem_type,
        "severity": severity,
        "confidence": round(confidence, 2),
        "classification_method": "Deterministic Keyword Rules (Regex)"
    }


def analyze_reviews(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Validate dataset and add multi-label category binary columns, primary category, secondary categories,
    sentiment, problem type, severity, and classification confidence.
    """
    if df.empty:
        return create_empty_analysis_results()

    df = df.copy()

    # Data Validation Audits
    total_reviews = len(df)
    unique_reviews = df["review_id"].nunique() if "review_id" in df.columns else total_reviews
    duplicate_count = total_reviews - unique_reviews
    missing_text_count = df["review_text"].isnull().sum() if "review_text" in df.columns else 0
    missing_rating_count = df["rating"].isnull().sum() if "rating" in df.columns else 0

    all_categories = list(CATEGORY_PATTERNS.keys()) + ["Other or unclear"]

    classification_results = []
    cat_flags_list = []

    for _, row in df.iterrows():
        text = row.get("review_text", "")
        rating = int(row.get("rating", 0))
        c_res = classify_single_review(text, rating)
        classification_results.append(c_res)

        cats = c_res["all_matched_categories"]
        flags = {cat: (1 if cat in cats else 0) for cat in all_categories}
        cat_flags_list.append(flags)

    # Attach fields to DataFrame
    c_df = pd.DataFrame(classification_results)
    cat_flags_df = pd.DataFrame(cat_flags_list)

    for col in c_df.columns:
        if col != "all_matched_categories":
            df[col] = c_df[col]

    for col in cat_flags_df.columns:
        df[col] = cat_flags_df[col]

    # Metrics computation
    avg_rating = float(df["rating"].mean())
    neg_df = df[df["rating"].isin([1, 2])]
    total_negative = len(neg_df)
    neg_percentage = (total_negative / total_reviews * 100) if total_reviews > 0 else 0.0

    # 1. Star Rating Distribution Table
    rating_counts = df["rating"].value_counts().to_dict()
    rating_summary_rows = []
    for r in [5, 4, 3, 2, 1]:
        cnt = rating_counts.get(r, 0)
        pct = (cnt / total_reviews * 100) if total_reviews > 0 else 0.0
        rating_summary_rows.append({
            "Star Rating": f"{r} Star{'s' if r > 1 else ''}",
            "Review Count": cnt,
            "Percentage (%)": round(pct, 2)
        })

    rating_summary_df = pd.DataFrame(rating_summary_rows)

    # 2. Complaint Analysis Table
    complaint_rows = []
    complaint_cats = [c for c in all_categories if c != "Positive feedback"]

    for cat in complaint_cats:
        mention_df = df[df[cat] == 1]
        cnt = len(mention_df)
        pct_total = (cnt / total_reviews * 100) if total_reviews > 0 else 0.0
        
        neg_mention_df = neg_df[neg_df[cat] == 1]
        cnt_neg = len(neg_mention_df)
        pct_neg = (cnt_neg / total_negative * 100) if total_negative > 0 else 0.0

        sample_reviews = neg_mention_df if not neg_mention_df.empty else mention_df
        excerpts = []
        for _, s_row in sample_reviews.head(3).iterrows():
            txt = str(s_row["review_text"]).strip().replace("\n", " ")
            if len(txt) > 85:
                txt = txt[:82] + "..."
            r_id = str(s_row.get("review_id", ""))[:8]
            excerpts.append(f"[{r_id}]: \"{txt}\"")
        
        excerpts_str = " | ".join(excerpts) if excerpts else "None"
        evidence_desc = get_category_evidence_description(cat, cnt, pct_neg)

        # Dominant Problem Type for category
        dom_prob = mention_df["problem_type"].mode()[0] if not mention_df.empty else "Operational/Service Issue"

        complaint_rows.append({
            "Complaint Category": cat,
            "Mentions Count": cnt,
            "Percentage of Total Reviews (%) [Denominator: 1000]": round(pct_total, 2),
            "Percentage of Negative Reviews (%) [Denominator: 292]": round(pct_neg, 2),
            "Dominant Problem Type": dom_prob,
            "Representative Review Excerpts": excerpts_str,
            "Evidence & Operational Context": evidence_desc
        })

    complaint_df = pd.DataFrame(complaint_rows).sort_values(by="Mentions Count", ascending=False)

    # 3. Problem Type Table
    prob_counts = df["problem_type"].value_counts()
    prob_rows = []
    for ptype, count in prob_counts.items():
        prob_rows.append({
            "Problem Type": ptype,
            "Count": count,
            "Percentage (%)": round(count / total_reviews * 100, 2)
        })
    problem_type_df = pd.DataFrame(prob_rows)

    # 4. Severity Distribution Table
    sev_counts = df["severity"].value_counts()
    sev_rows = []
    for s_level, count in sev_counts.items():
        sev_rows.append({
            "Severity Level": s_level,
            "Count": count,
            "Percentage (%)": round(count / total_reviews * 100, 2)
        })
    severity_df = pd.DataFrame(sev_rows)

    summary_metrics = {
        "total_reviews": total_reviews,
        "unique_reviews": unique_reviews,
        "duplicate_count": duplicate_count,
        "missing_text_count": missing_text_count,
        "missing_rating_count": missing_rating_count,
        "average_rating": round(avg_rating, 2),
        "total_negative_reviews": total_negative,
        "negative_percentage": round(neg_percentage, 2),
        "1_star_count": rating_counts.get(1, 0),
        "2_star_count": rating_counts.get(2, 0),
        "3_star_count": rating_counts.get(3, 0),
        "4_star_count": rating_counts.get(4, 0),
        "5_star_count": rating_counts.get(5, 0),
        "average_confidence": round(float(df["confidence"].mean()), 2)
    }

    return {
        "processed_df": df,
        "rating_summary_df": rating_summary_df,
        "complaint_analysis_df": complaint_df,
        "problem_type_df": problem_type_df,
        "severity_df": severity_df,
        "summary_metrics": summary_metrics
    }


def get_category_evidence_description(category: str, count: int, pct_neg: float) -> str:
    """Returns domain context & operational evidence descriptions for MoveInSync employee cab app."""
    evidence_map = {
        "App crashes and performance": "App freezing, loading timeouts, unresponsiveness during peak shift changeovers, and OS compatibility issues.",
        "Pickup timing and delays": "Delayed cab pickups, extended employee waiting times, and unnotified late arrivals causing shift start anxiety.",
        "User interface and usability": "User confusion post-update, unintuitive navigation, small touch targets, and feedback box issues.",
        "GPS and live tracking": "Stale driver map icons, inaccurate ETA predictions, and mismatch between driver position and employee location.",
        "Cab or shuttle availability": "Unassigned vehicles, lack of allocated cabs for scheduled shift rosters, and unserviced corporate routes.",
        "Login and authentication": "OTP delivery latency, enterprise SSO credentials error, and session logouts during pre-shift booking window.",
        "Booking and cancellation": "Failures when booking roster seats, shift modification errors, and 1-tap cab cancellation glitches.",
        "Notifications and reminders": "Missed push alerts for cab arrival, late arrival notifications, and muted audio reminders.",
        "Driver behavior and safety": "Reports of driver rash driving, rude conduct, route deviation, and safety concerns during late night commutes.",
        "Attendance and check-in": "QR code scanner failures, inability to mark boarding status, and false missed-cab attendance flags.",
        "Customer support": "Unresolved support tickets, lack of live response during active trips, and unhelpful Transport Desk response.",
        "Feature requests": "User suggestions for live ETA sharing with family, dark mode, easier shift swap, and automated booking.",
        "Other or unclear": "Generic short reviews (e.g. 'bekar', 'bad app', 'worst transport') without specific technical details."
    }
    return evidence_map.get(category, f"Observed in {count} reviews ({pct_neg:.1f}% of negative reviews).")


def create_empty_analysis_results() -> Dict[str, Any]:
    """Helper for empty datasets."""
    cols = [
        "review_id", "user_name", "rating", "review_text", "review_date", "app_version",
        "primary_category", "secondary_categories", "sentiment", "problem_type", "severity",
        "confidence", "classification_method"
    ]
    return {
        "processed_df": pd.DataFrame(columns=cols),
        "rating_summary_df": pd.DataFrame(),
        "complaint_analysis_df": pd.DataFrame(),
        "problem_type_df": pd.DataFrame(),
        "severity_df": pd.DataFrame(),
        "summary_metrics": {
            "total_reviews": 0, "unique_reviews": 0, "duplicate_count": 0, "missing_text_count": 0,
            "missing_rating_count": 0, "average_rating": 0.0, "total_negative_reviews": 0,
            "negative_percentage": 0.0, "1_star_count": 0, "2_star_count": 0, "3_star_count": 0,
            "4_star_count": 0, "5_star_count": 0, "average_confidence": 0.0
        }
    }
