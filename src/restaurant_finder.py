import os
import googlemaps
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Tuple, Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Google Maps client
api_key = os.getenv("GOOGLE_MAPS_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_MAPS_API_KEY environment variable is not set")

gmaps = googlemaps.Client(key=os.getenv("GOOGLE_MAPS_API_KEY"))

router = APIRouter(prefix="/restaurants", tags=["Restaurant Finder"])

class RestaurantSearchRequest(BaseModel):
    location: Tuple[float, float]  # (latitude, longitude)
    keyword: Optional[str] = None
    radius: int = 1000
    type: str = "restaurant"
    price_level: Optional[int] = None
    open_now: bool = False

class RestaurantResponse(BaseModel):
    name: str
    place_id: str
    address: str
    rating: Optional[float] = None
    price_level: Optional[int] = None
    distance: Optional[int] = None
    photo_url: Optional[str] = None

@router.post(
    "/search",
    response_model=List[RestaurantResponse],
    operation_id="search_restaurants"
)
async def search_restaurants_api(request: RestaurantSearchRequest):
    """
    Search for restaurants that match the criteria
    
    Parameters:
    - location: Geographic coordinates (latitude, longitude)
    - keyword: Search keyword (e.g., "vegetarian", "Japanese")
    - radius: Search radius (meters)
    - type: Place type (default is restaurant)
    - price_level: Price level (0-4)
    - open_now: Whether to show only currently open restaurants
    
    Returns:
    - A list of restaurants with name, address, rating, and other information
    """
    try:
        results = search_restaurants(vars(request))
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching for restaurants: {str(e)}")

def search_restaurants(params):
    """
    Search for restaurants using Google Maps Places API
    """
    # Prepare Google Maps API parameters
    location = params.get("location")
    api_params = {
        "location": location,
        "radius": params.get("radius", 1000),
        "type": params.get("type", "restaurant"),
        "open_now": params.get("open_now", False)
    }
    
    # Add optional parameters
    if "keyword" in params and params["keyword"]:
        api_params["keyword"] = params["keyword"]
    
    if "price_level" in params and params["price_level"] is not None:
        api_params["minprice"] = params["price_level"]
        api_params["maxprice"] = params["price_level"]
    
    # Call Google Maps Places API
    places_result = gmaps.places_nearby(**api_params)
    
    # Process results
    restaurants = []
    for place in places_result.get("results", []):
        # Calculate distance (for more accurate distance, use Distance Matrix API)
        # This is a simplified calculation method
        
        # Get photo URL (if available)
        photo_url = None
        if "photos" in place and place["photos"]:
            photo_reference = place["photos"][0]["photo_reference"]
            photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={photo_reference}&key={os.getenv('GOOGLE_MAPS_API_KEY')}"
        
        restaurant = {
            "name": place["name"],
            "place_id": place["place_id"],
            "address": place.get("vicinity", ""),
            "rating": place.get("rating"),
            "price_level": place.get("price_level"),
            "photo_url": photo_url
        }
        
        restaurants.append(restaurant)
    
    return restaurants
