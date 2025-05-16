import os
import googlemaps
from fastapi import APIRouter, HTTPException, Depends, Response
from pydantic import BaseModel
from typing import List, Tuple, Dict, Any, Optional, Union
from dotenv import load_dotenv
import requests

from src.security import verify_api_key

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
    type: Optional[str] = None  # Made optional to support different establishment types
    price_level: Optional[int] = None
    open_now: bool = False
    language: Optional[str] = None

class RestaurantResponse(BaseModel):
    name: str
    place_id: str
    address: str
    rating: Optional[float] = None
    user_ratings_total: Optional[int] = None
    price_level: Optional[int] = None
    distance: Optional[int] = None
    photo_reference: Optional[str] = None  # Store photo reference instead of URL

@router.post(
    "/search",
    response_model=List[RestaurantResponse],
    operation_id="search_restaurants",
    dependencies=[Depends(verify_api_key)]  # Add API key verification
)
async def search_restaurants_api(request: RestaurantSearchRequest):
    """
    Search for food and drink establishments that match the criteria
    
    Parameters:
    - location: Geographic coordinates (latitude, longitude)
    - keyword: Search keyword (e.g., "vegetarian", "Japanese", "bubble tea")
    - radius: Search radius (meters)
    - type: Place type (can be restaurant, cafe, bar, bakery, etc.)
    - price_level: Price level (0-4)
    - open_now: Whether to show only currently open establishments
    - language: Language for the search
    
    Returns:
    - A list of food and drink establishments with name, address, rating, and other information
    
    Security:
    - Requires valid API key in X-API-Key header
    """
    try:
        results = search_restaurants(vars(request))
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching for restaurants: {str(e)}")

@router.get(
    "/photo/{photo_reference}",
    operation_id="get_place_photo",
    dependencies=[Depends(verify_api_key)]
)
async def get_place_photo(photo_reference: str, maxwidth: int = 400):
    """
    Proxy endpoint for Google Maps Place Photos API
    
    This endpoint securely retrieves a photo from Google Maps without exposing the API key
    
    Parameters:
    - photo_reference: The photo reference string from Google Maps API
    - maxwidth: Maximum width of the photo (default: 400)
    
    Returns:
    - The photo as a binary response
    
    Security:
    - Requires valid API key in X-API-Key header
    """
    try:
        # Construct the Google Maps photo URL with our API key
        url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth={maxwidth}&photoreference={photo_reference}&key={api_key}"
        
        # Make the request to Google Maps
        response = requests.get(url, stream=True)
        
        # Return the image with appropriate content type
        return Response(
            content=response.content,
            media_type=response.headers.get("content-type", "image/jpeg"),
            headers={
                "Cache-Control": "public, max-age=86400"  # Cache for 1 day
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving photo: {str(e)}")

def search_restaurants(params):
    """
    Search for food and drink establishments using Google Maps Places API
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
        "open_now": params.get("open_now", False)
    }
    
    # Add type parameter if provided, otherwise use keyword to find any food/drink establishment
    establishment_type = params.get("type")
    if establishment_type:
        api_params["type"] = establishment_type
    
    # Always add keyword parameter if provided
    if "keyword" in params and params["keyword"]:
        api_params["keyword"] = params["keyword"]
    # If no keyword provided and no type specified, default to food-related search
    elif "type" not in api_params:
        api_params["keyword"] = "food"
    
    if "price_level" in params and params["price_level"] is not None:
        api_params["min_price"] = params["price_level"]
        api_params["max_price"] = params["price_level"]
    
    # Add language parameter if provided
    if "language" in params and params["language"]:
        api_params["language"] = params["language"]
    
    # Debug log for API call
    print(f"Calling Google Maps API with params: {api_params}")
    
    # Call Google Maps Places API
    places_result = gmaps.places_nearby(**api_params)
    
    # Debug log for results
    print(f"Got {len(places_result.get('results', []))} results from Google Maps API")
    
    # Process results
    restaurants = []
    for place in places_result.get("results", []):
        # Get photo reference (if available)
        photo_reference = None
        if "photos" in place and place["photos"]:
            photo_reference = place["photos"][0]["photo_reference"]
        
        restaurant = {
            "name": place["name"],
            "place_id": place["place_id"],
            "address": place.get("vicinity", ""),
            "rating": place.get("rating"),
            "user_ratings_total": place.get("user_ratings_total"),
            "price_level": place.get("price_level"),
            "photo_reference": photo_reference  # Store photo reference instead of URL
        }
        
        restaurants.append(restaurant)
    
    return restaurants
