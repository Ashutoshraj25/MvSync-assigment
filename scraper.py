"""
scraper.py - Google Play Store Review Scraper for MoveInSync Analysis
"""

import time
import datetime
from typing import Callable, Optional, Dict, Any, List, Tuple
import pandas as pd
from google_play_scraper import reviews, Sort


SORT_MAPPING = {
    "newest": Sort.NEWEST,
    "most_relevant": Sort.MOST_RELEVANT,
}


def fetch_reviews(
    app_id: str = "com.moveinsync.ets",
    lang: str = "en",
    country: str = "in",
    sort_order: str = "newest",
    max_count: Optional[int] = 1000,
    progress_callback: Optional[Callable[[int, Optional[int], str], None]] = None,
    delay_seconds: float = 0.5,
    max_retries: int = 3
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Fetch public Google Play reviews with pagination, deduplication, retry logic, and error tracking.

    Args:
        app_id: Package ID (e.g., 'com.moveinsync.ets')
        lang: Language code ('en')
        country: Country code ('in', 'us')
        sort_order: 'newest' or 'most_relevant'
        max_count: Target review limit, or None / 0 / float('inf') for max available
        progress_callback: Callback function(current_count, target_max, status_msg)
        delay_seconds: Pause between requests to respect rate limits
        max_retries: Retry attempts on network/scraping errors

    Returns:
        Tuple of (DataFrame of reviews, Metadata dictionary)
    """
    start_time = datetime.datetime.now()
    sort_enum = SORT_MAPPING.get(sort_order.lower(), Sort.NEWEST)
    
    # Standardize target count
    target_max = None if (max_count is None or max_count <= 0 or max_count == float('inf')) else int(max_count)
    
    collected_reviews: List[Dict[str, Any]] = []
    seen_ids = set()
    duplicate_count = 0
    continuation_token = None
    errors: List[str] = []
    
    batch_size = 100 if (target_max is None or target_max > 100) else max(20, target_max)
    
    status_msg = f"Starting review extraction for package '{app_id}'..."
    if progress_callback:
        progress_callback(0, target_max, status_msg)

    keep_fetching = True
    consecutive_empty = 0

    while keep_fetching:
        # Determine batch count to ask for
        if target_max:
            remaining = target_max - len(collected_reviews)
            if remaining <= 0:
                break
            current_batch_size = min(batch_size, remaining)
        else:
            current_batch_size = batch_size

        batch_result = None
        new_token = None
        
        # Retry loop for batch request
        for retry in range(1, max_retries + 1):
            try:
                if continuation_token is None:
                    batch_result, new_token = reviews(
                        app_id,
                        lang=lang,
                        country=country,
                        sort=sort_enum,
                        count=current_batch_size,
                    )
                else:
                    batch_result, new_token = reviews(
                        app_id,
                        continuation_token=continuation_token,
                    )
                break  # Success
            except Exception as e:
                err_msg = f"Batch fetch attempt {retry}/{max_retries} failed: {str(e)}"
                if retry == max_retries:
                    errors.append(err_msg)
                    keep_fetching = False
                time.sleep(1.5 * retry)

        if not batch_result:
            consecutive_empty += 1
            if consecutive_empty >= 2:
                # No more data returned by Google Play
                break
            continuation_token = new_token
            continue

        consecutive_empty = 0
        new_items_in_batch = 0

        for r in batch_result:
            r_id = r.get("reviewId")
            if not r_id:
                # Fallback id if reviewId missing
                r_id = f"{r.get('userName', 'anon')}_{r.get('at', '')}"

            if r_id in seen_ids:
                duplicate_count += 1
                continue

            seen_ids.add(r_id)
            new_items_in_batch += 1

            # Standardize review record
            rev_date = r.get("at")
            reply_date = r.get("repliedAt")

            collected_reviews.append({
                "review_id": r_id,
                "user_name": r.get("userName", ""),
                "rating": r.get("score", 0),
                "review_text": r.get("content", ""),
                "review_date": rev_date,
                "last_updated_date": rev_date,  # Play store scraper uses 'at' as review timestamp
                "app_version": r.get("reviewCreatedVersion") or r.get("appVersion") or "Unknown",
                "helpful_votes": r.get("thumbsUpCount", 0),
                "developer_response": r.get("replyContent") or "",
                "developer_response_date": reply_date,
            })

            if target_max and len(collected_reviews) >= target_max:
                keep_fetching = False
                break

        # Progress callback update
        count_so_far = len(collected_reviews)
        msg = f"Fetched {count_so_far} unique reviews (Batch duplicates skipped: {len(batch_result) - new_items_in_batch})."
        if progress_callback:
            progress_callback(count_so_far, target_max, msg)

        # Check pagination continuation
        if not new_token or new_token == continuation_token or new_items_in_batch == 0:
            # End of pagination stream
            break
            
        continuation_token = new_token
        time.sleep(delay_seconds)

    end_time = datetime.datetime.now()

    # Convert to DataFrame
    if collected_reviews:
        df = pd.DataFrame(collected_reviews)
        # Ensure date columns are formatted properly
        df["review_date"] = pd.to_datetime(df["review_date"])
        if "developer_response_date" in df.columns:
            df["developer_response_date"] = pd.to_datetime(df["developer_response_date"])
        min_date = df["review_date"].min()
        max_date = df["review_date"].max()
        date_range_str = f"{min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}"
    else:
        df = pd.DataFrame(columns=[
            "review_id", "user_name", "rating", "review_text", "review_date",
            "last_updated_date", "app_version", "helpful_votes",
            "developer_response", "developer_response_date"
        ])
        date_range_str = "N/A"

    metadata = {
        "collection_timestamp": start_time.strftime("%Y-%m-%d %H:%M:%S"),
        "execution_duration_sec": round((end_time - start_time).total_seconds(), 2),
        "package_id": app_id,
        "selected_country": country,
        "selected_language": lang,
        "sort_order": sort_order,
        "requested_limit": target_max if target_max else "Maximum Available",
        "actual_unique_reviews": len(collected_reviews),
        "date_range": date_range_str,
        "duplicate_count": duplicate_count,
        "errors": errors if errors else ["None"],
        "is_mock_data": False
    }

    return df, metadata
