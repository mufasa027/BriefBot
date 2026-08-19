import json
from ai.client import get_ai_client
from ai.ranker import calculate_freshness_score
from services.logging_service import log_event

def evaluate_story_v1_1(story, force=False):
    """
    V1.1 Advanced Editorial Scoring.
    Only evaluates if story.editorial_score is None, unless force=True.
    """
    if story.editorial_score is not None and not force:
        return  # Already scored
        
    client = get_ai_client()
    if not client:
        log_event("V1.1_SCORE_ERROR", "No AI client available", article_uuid=story.story_id, level="ERROR")
        return

    # 1. Deterministic Freshness
    freshness = calculate_freshness_score(story.latest_update or story.first_published)
    story.freshness_score = freshness

    # Prepare story context for LLM
    articles_context = []
    for a in story.articles:
        articles_context.append(f"Source: {a.get('source')}\nTitle: {a.get('title')}\nSummary: {a.get('summary')}")
    
    context_text = "\n\n".join(articles_context)
    
    # Base V1 Score (to use as a fallback/context)
    v1_score = story.overall_story_score

    # Prompt for Impact, Virality, Credibility, Audience Relevance
    prompt = f"""
    You are the Executive Editor of an AI-assisted Newsroom.
    Evaluate the following clustered news story for editorial prioritization.
    
    STORY CONTEXT:
    {context_text}
    
    Score the following dimensions from 0 to 100:
    - impact: Global significance, geopolitical/economic weight, long-term consequences.
    - virality: Potential for high social media engagement, shock value, or trending interest.
    - credibility: Reliability of the claims. Are there multiple verified sources or official statements?
    - audience_relevance: How much this affects the daily lives or interests of a broad global audience.
    
    Also provide:
    - editorial_reason: A 3-4 bullet point concise explanation of "WHY THIS STORY?" (e.g. "• Major geopolitical implications\\n• Rapidly developing situation")
    - editorial_recommendation: Exactly one of: [PUBLISH NOW, REVIEW, WATCH, LOW PRIORITY, DO NOT PUBLISH]
    
    Return EXACTLY valid JSON with these keys:
    {{"impact": 0, "virality": 0, "credibility": 0, "audience_relevance": 0, "editorial_reason": "", "editorial_recommendation": ""}}
    """
    
    try:
        response = client.chat.completions.create(
            model="openrouter/auto", # using auto or whatever is default
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        result = json.loads(response.choices[0].message.content)
        
        story.impact_score = int(result.get("impact", 50))
        story.virality_score = int(result.get("virality", 50))
        story.credibility_score = int(result.get("credibility", 50))
        story.audience_relevance_score = int(result.get("audience_relevance", 50))
        story.editorial_reason = str(result.get("editorial_reason", ""))
        story.editorial_recommendation = str(result.get("editorial_recommendation", "REVIEW"))
        
        # Calculate Weighted Editorial Score
        # impact * 0.30 + freshness * 0.20 + credibility * 0.20 + virality * 0.15 + audience_relevance * 0.15
        weighted = (story.impact_score * 0.30) + (story.freshness_score * 0.20) + \
                   (story.credibility_score * 0.20) + (story.virality_score * 0.15) + \
                   (story.audience_relevance_score * 0.15)
        story.editorial_score = int(max(0, min(100, weighted)))
        
        # Determine basic confidence WITHOUT extra LLM call if possible
        # Or with LLM if gated
        
        num_sources = story.num_sources
        
        # Gating source agreement LLM call: Only if >= 2 sources and editorial_score >= 65
        if num_sources >= 2 and story.editorial_score >= 65:
            agreement_prompt = f"""
            Analyze the following news articles from different sources about the same event.
            {context_text}
            
            Determine if the sources broadly agree on the facts, partially agree (some discrepancies in numbers/details), or have conflicting claims.
            
            Return EXACTLY valid JSON:
            {{"source_agreement": "HIGH" | "PARTIAL" | "CONFLICTING", "conflict_summary": "Describe any conflicts briefly, or None"}}
            """
            ag_response = client.chat.completions.create(
                model="openrouter/auto",
                messages=[{"role": "user", "content": agreement_prompt}],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            ag_result = json.loads(ag_response.choices[0].message.content)
            story.source_agreement = ag_result.get("source_agreement", "HIGH")
            # Phase 2 will utilize conflict_summary properly, but we can store it or just use agreement for now.
        else:
            story.source_agreement = "N/A (Single Source or Low Priority)"
            
        # Basic confidence calculation (deterministic based on credibility, sources, and agreement)
        base_conf = story.credibility_score
        if num_sources >= 3:
            base_conf += 15
        elif num_sources == 2:
            base_conf += 5
            
        if story.source_agreement == "CONFLICTING":
            base_conf -= 20
        elif story.source_agreement == "PARTIAL":
            base_conf -= 10
            
        story.confidence_score = int(max(0, min(100, base_conf)))
        if story.confidence_score >= 80:
            story.confidence_level = "HIGH"
        elif story.confidence_score >= 60:
            story.confidence_level = "MEDIUM"
        else:
            story.confidence_level = "LOW"
            
        log_event("V1.1_SCORE_SUCCESS", f"Scored story {story.story_id}: {story.editorial_score}", article_uuid=story.story_id)

    except Exception as e:
        log_event("V1.1_SCORE_ERROR", f"LLM Scoring Failed: {e}", article_uuid=story.story_id, level="ERROR")
        # Do not fabricate scores on failure. Leave them as None so they can be retried later.
        pass
