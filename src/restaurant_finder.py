import os
import googlemaps
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Tuple, Dict, Any, Optional, Union
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
    location: Union[Tuple[float, float], Dict[str, float]]  # (latitude, longitude) or {"lat": lat, "lng": lng}
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
    # Debug log to help diagnose issues
    print(f"Search params received: {params}")
    
    # Prepare Google Maps API parameters
    location = params.get("location")
    
    # Validate location parameter
    if not location:
        raise ValueError("Location parameter is required and cannot be None")
    
    # Convert location to the correct format if needed
    if isinstance(location, (tuple, list)) and len(location) == 2:
        # Format: (lat, lng) tuple or list
        location = {"lat": float(location[0]), "lng": float(location[1])}
        print(f"Converted tuple location to: {location}")
    elif isinstance(location, dict):
        # If location is a dict but doesn't have lat/lng, check for latitude/longitude keys
        if 'lat' not in location or 'lng' not in location:
            if 'latitude' in location and 'longitude' in location:
                location = {"lat": float(location['latitude']), "lng": float(location['longitude'])}
                print(f"Converted dictionary with latitude/longitude to: {location}")
            else:
                raise ValueError(f"Invalid location dictionary format: {location}. Must contain 'lat' and 'lng' keys or 'latitude' and 'longitude' keys")
        else:
            # Ensure values are float type
            location = {"lat": float(location['lat']), "lng": float(location['lng'])}
            print(f"Using location: {location}")
    else:
        raise ValueError(f"Invalid location format: {location} (type: {type(location)}). Must be (lat, lng) tuple or {{lat, lng}} dict")
        
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
        api_params["min_price"] = params["price_level"]
        api_params["max_price"] = params["price_level"]
    
    # Debug log for API call
    print(f"Calling Google Maps API with params: {api_params}")
    
    # Call Google Maps Places API
    places_result = gmaps.places_nearby(**api_params)
    
    # Debug log for results
    print(f"Got {len(places_result.get('results', []))} results from Google Maps API")
    
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
