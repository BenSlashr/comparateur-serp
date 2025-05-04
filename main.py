import os
import logging
import json
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import httpx
from pydantic import BaseModel
from collections import defaultdict

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("serp-comparateur")

# Load environment variables
load_dotenv()

# Initialize FastAPI app with root_path support for deployment in subdirectories
app = FastAPI(
    title="SERP Comparateur",
    # root_path will be set by the ASGI server or reverse proxy
    # This allows the app to work when deployed in a subdirectory
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize templates
templates = Jinja2Templates(directory="templates")

# API keys
VALUESERP_API_KEY = os.getenv("VALUESERP_API_KEY")
if not VALUESERP_API_KEY:
    logger.warning("ValueSERP API key not found in environment variables!")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.warning("Gemini API key not found in environment variables!")

class SerpRequest(BaseModel):
    keywords: List[str]
    country: str
    location: Optional[str] = None
    search_engine: str
    num_results: int
    language: str
    device: str

@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    logger.info("Serving index page")
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/compare-serps")
async def compare_serps(request: Request):
    form_data = await request.form()
    logger.info(f"Received form data: {form_data}")
    
    # Extract keywords (up to 4)
    keywords = []
    for i in range(1, 5):
        keyword = form_data.get(f"keyword{i}")
        if keyword and keyword.strip():
            keywords.append(keyword.strip())
    
    if not keywords:
        logger.error("No keywords provided")
        raise HTTPException(status_code=400, detail="At least one keyword is required")
    
    country = form_data.get("country", "FR")
    location = form_data.get("location", "")
    search_engine = form_data.get("search_engine", "google.fr")
    num_results = int(form_data.get("num_results", "10"))
    language = form_data.get("language", "fr")
    device = form_data.get("device", "desktop")
    
    logger.info(f"Processing SERP comparison for keywords: {keywords}")
    
    # Fetch SERP results for each keyword
    serp_results = []
    common_urls = {}
    all_urls = set()
    search_intents = {}
    error_keywords = []
    
    async with httpx.AsyncClient() as client:
        for keyword in keywords:
            logger.info(f"Fetching SERP for keyword: {keyword}")
            
            params = {
                "api_key": VALUESERP_API_KEY,
                "q": keyword,
                "location": location if location else None,
                "google_domain": search_engine,
                "gl": country,
                "hl": language,
                "num": num_results,
                "device": device
            }
            
            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}
            
            try:
                response = await client.get("https://api.valueserp.com/search", params=params, timeout=30.0)
                response.raise_for_status()
                result = response.json()
                
                # Extract organic results
                organic_results = result.get("organic_results", [])
                
                # Extract URLs from organic results
                urls = [item.get("link") for item in organic_results if item.get("link")]
                
                # Add to all URLs set
                all_urls.update(urls)
                
                # Track URLs for this keyword
                for url in urls:
                    if url in common_urls:
                        common_urls[url].append(keyword)
                    else:
                        common_urls[url] = [keyword]
                
                # Analyze search intent with Gemini if API key is available
                intent_data = {
                    "overall_intent": "Non disponible (clé API Gemini manquante)",
                    "page_intents": []
                }
                
                if GEMINI_API_KEY:
                    try:
                        intent_data = await analyze_search_intent_with_gemini(keyword, organic_results)
                        logger.info(f"Successfully analyzed search intent for keyword: {keyword}")
                    except Exception as e:
                        logger.error(f"Error analyzing search intent for keyword {keyword}: {str(e)}")
                        intent_data = {
                            "overall_intent": f"Erreur d'analyse: {str(e)[:100]}...",
                            "page_intents": [],
                            "error": str(e)
                        }
                
                # Add page intent data to organic results
                if "page_intents" in intent_data and len(intent_data["page_intents"]) > 0:
                    # Create a mapping of position to intent data
                    intent_map = {item["position"]: item for item in intent_data["page_intents"]}
                    
                    # Add intent data to each result
                    for i, result in enumerate(organic_results[:10], 1):
                        if i in intent_map:
                            result["intent"] = intent_map[i]["intent"]
                            result["intent_explanation"] = intent_map[i]["explanation"]
                        else:
                            result["intent"] = "Non analysé"
                            result["intent_explanation"] = ""
                
                serp_results.append({
                    "keyword": keyword,
                    "results": organic_results,
                    "overall_intent": intent_data.get("overall_intent", "Non disponible"),
                    "page_intents": intent_data.get("page_intents", [])
                })
                
                # Store search intent for analysis
                search_intents[keyword] = intent_data.get("overall_intent", "Non disponible")
                
                logger.info(f"Successfully fetched SERP for keyword: {keyword}")
            except Exception as e:
                error_message = str(e)
                logger.error(f"Error fetching SERP for keyword {keyword}: {error_message}")
                
                # Add placeholder results for failed keyword
                serp_results.append({
                    "keyword": keyword,
                    "results": [],
                    "search_intent": f"Erreur: Impossible de récupérer les résultats pour ce mot-clé",
                    "error": error_message[:100] + ("..." if len(error_message) > 100 else "")
                })
                
                error_keywords.append(keyword)
    
    # If all keywords failed, raise an exception
    if len(error_keywords) == len(keywords):
        raise HTTPException(status_code=500, detail=f"Error fetching SERP for all keywords: {', '.join(error_keywords)}")
    
    # If some keywords failed, log a warning
    if error_keywords:
        logger.warning(f"Some keywords failed: {', '.join(error_keywords)}. Continuing with available results.")
    
    # Analyze results in more detail
    exact_matches = defaultdict(list)  # URLs at same position across keywords
    common_urls = defaultdict(list)    # URLs appearing in multiple keywords
    common_titles = defaultdict(list)  # Similar titles across keywords
    common_snippets = defaultdict(list)  # Similar snippets across keywords
    
    position_map = {}  # Maps (url, position) to keywords
    title_map = {}     # Maps normalized titles to keywords
    snippet_map = {}   # Maps normalized snippets to keywords
    
    # Process all results
    for keyword_idx, keyword in enumerate(keywords):
        results = serp_results[keyword_idx]['results']
        
        for position, result in enumerate(results):
            url = result.get('link', '')
            title = result.get('title', '').lower()
            snippet = result.get('snippet', '').lower()
            
            # Track exact position matches
            position_key = (url, position)
            if position_key in position_map:
                position_map[position_key].append(keyword)
            else:
                position_map[position_key] = [keyword]
            
            # Track common URLs
            if url in common_urls:
                if keyword not in common_urls[url]:
                    common_urls[url].append(keyword)
            else:
                common_urls[url] = [keyword]
            
            # Track common titles (simplified - could use more sophisticated text similarity)
            if title:
                if title in title_map:
                    if keyword not in title_map[title]:
                        title_map[title].append(keyword)
                else:
                    title_map[title] = [keyword]
            
            # Track common snippets
            if snippet:
                if snippet in snippet_map:
                    if keyword not in snippet_map[snippet]:
                        snippet_map[snippet].append(keyword)
                else:
                    snippet_map[snippet] = [keyword]
    
    # Calculate statistics
    total_urls = len(common_urls)
    total_titles = len(title_map)
    total_snippets = len(snippet_map)
    
    # Count exact matches (same URL at same position)
    exact_match_count = sum(1 for keywords_list in position_map.values() if len(keywords_list) > 1)
    exact_match_percentage = exact_match_count / (len(position_map) or 1) * 100
    
    # Count common URLs (URL appears in multiple keywords)
    common_url_count = sum(1 for keywords_list in common_urls.values() if len(keywords_list) > 1)
    common_url_percentage = common_url_count / (total_urls or 1) * 100
    
    # Count common titles
    common_title_count = sum(1 for keywords_list in title_map.values() if len(keywords_list) > 1)
    common_title_percentage = common_title_count / (total_titles or 1) * 100
    
    # Count common snippets
    common_snippet_count = sum(1 for keywords_list in snippet_map.values() if len(keywords_list) > 1)
    common_snippet_percentage = common_snippet_count / (total_snippets or 1) * 100
    
    # Calculate overall similarity score (weighted average)
    similarity_score = (common_url_percentage * 0.5 + common_title_percentage * 0.3 + common_snippet_percentage * 0.2) / 100
    
    # Generate recommendation
    recommendation = ""
    if similarity_score > 0.7:
        recommendation = "Forte similarité détectée. Envisagez de créer une seule page couvrant tous les mots-clés."
    elif similarity_score > 0.4:
        recommendation = "Similarité modérée détectée. Vous pourriez créer une seule page avec des sections pour chaque mot-clé."
    else:
        recommendation = "Faible similarité détectée. Envisagez de créer des pages séparées pour chaque mot-clé."
    
    # Common URL counts by number of keywords they appear in
    common_url_counts = {}
    for url, kw_list in common_urls.items():
        count = len(kw_list)
        if count > 1:  # Only count URLs that appear in multiple keywords
            if count not in common_url_counts:
                common_url_counts[count] = 0
            common_url_counts[count] += 1
    
    analysis = {
        "total_urls": total_urls,
        "common_url_counts": common_url_counts,
        "similarity_score": similarity_score,
        "recommendation": recommendation,
        "exact_match": {
            "percentage": round(exact_match_percentage, 1),
            "count": exact_match_count
        },
        "common_urls": {
            "percentage": round(common_url_percentage, 1),
            "count": common_url_count
        },
        "common_titles": {
            "percentage": round(common_title_percentage, 1),
            "count": common_title_count
        },
        "common_snippets": {
            "percentage": round(common_snippet_percentage, 1),
            "count": common_snippet_count
        }
    }
    
    logger.info(f"Analysis complete: {json.dumps(analysis)}")
    
    return {
        "serp_results": serp_results,
        "analysis": analysis,
        "search_intents": search_intents
    }

async def analyze_search_intent_with_gemini(keyword: str, organic_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze search intent using Gemini API based on SERP results.
    Returns a dictionary with overall intent and per-page analysis.
    """
    logger.info(f"Analyzing search intent for keyword: {keyword}")
    
    # Format SERP results for Gemini with URLs and titles
    serp_content = f"Mot-clé: {keyword}\n\nRésultats de recherche:\n"
    
    # Limit to top 10 results
    results_to_analyze = organic_results[:10]
    
    for i, result in enumerate(results_to_analyze, 1):
        title = result.get('title', 'Sans titre')
        url = result.get('link', 'Sans URL')
        serp_content += f"\n{i}. Titre: {title}\n   URL: {url}\n"
    
    # Prepare prompt for Gemini
    prompt_text = f"""
    En tant qu'expert SEO, analyse les résultats de recherche suivants pour le mot-clé "{keyword}".
    
    {serp_content}
    
    Pour chaque résultat, détermine l'intention de la page parmi ces catégories :
    - Navigationnelle: L'utilisateur cherche un site ou une page spécifique
    - Transactionnelle: L'utilisateur veut acheter, s'inscrire ou effectuer une action
    - Informationnelle: L'utilisateur recherche des informations ou des réponses
    - Décisionnelle: L'utilisateur compare des options pour prendre une décision
    
    Ensuite, détermine l'intention globale de recherche pour ce mot-clé.
    
    Réponds au format JSON suivant (et uniquement ce format JSON, sans autre texte) :
    {{"overall_intent": "Type d'intention - Explication en 1-2 phrases",
     "page_intents": [
        {{"position": 1, "intent": "Type d'intention", "explanation": "Brève explication"}},
        {{"position": 2, "intent": "Type d'intention", "explanation": "Brève explication"}},
        ...
     ]
    }}
    """
    
    try:
        # Prepare the request payload for Gemini API
        payload = {
            "contents": [{
                "parts": [{"text": prompt_text}]
            }]
        }
        
        # Make direct API call to Gemini
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30.0
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Extract the text from the response
            if result.get("candidates") and len(result["candidates"]) > 0:
                candidate = result["candidates"][0]
                if candidate.get("content") and candidate["content"].get("parts") and len(candidate["content"]["parts"]) > 0:
                    response_text = candidate["content"]["parts"][0].get("text", "").strip()
                    
                    # Try to parse JSON response
                    try:
                        # Find JSON content in the response (in case there's extra text)
                        import re
                        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                        if json_match:
                            json_str = json_match.group(0)
                            intent_data = json.loads(json_str)
                        else:
                            intent_data = json.loads(response_text)
                            
                        logger.info(f"Successfully parsed JSON response for {keyword}")
                        return intent_data
                    except json.JSONDecodeError as json_err:
                        logger.error(f"Failed to parse JSON from Gemini response: {str(json_err)}")
                        # Return a formatted error response
                        return {
                            "overall_intent": f"Erreur de format - Impossible de parser la réponse JSON",
                            "page_intents": [],
                            "raw_response": response_text[:500] + ("..." if len(response_text) > 500 else "")
                        }
                else:
                    return {
                        "overall_intent": "Analyse non disponible (format de réponse inattendu)",
                        "page_intents": []
                    }
            else:
                return {
                    "overall_intent": "Analyse non disponible (pas de réponse)",
                    "page_intents": []
                }
        
        logger.info(f"Gemini analysis completed for: {keyword}")
    except Exception as e:
        logger.error(f"Error with Gemini API: {str(e)}")
        return {
            "overall_intent": f"Erreur - {str(e)[:100]}",
            "page_intents": [],
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
