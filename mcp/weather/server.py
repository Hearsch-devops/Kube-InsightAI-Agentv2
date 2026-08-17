import requests

from mcp.server import MCPServer


mcp = MCPServer("Weather MCP Server")


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"


@mcp.tool()
def get_weather(city: str) -> dict:
    """
    Get the current weather for a city.
    """

    # Step 1: Convert city name to latitude/longitude
    geocoding_response = requests.get(
        GEOCODING_URL,
        params={
            "name": city,
            "count": 1,
            "language": "en",
            "format": "json",
        },
        timeout=10,
    )

    geocoding_response.raise_for_status()

    locations = geocoding_response.json().get("results", [])

    if not locations:
        return {
            "error": f"Could not find city: {city}"
        }

    location = locations[0]

    latitude = location["latitude"]
    longitude = location["longitude"]

    # Step 2: Get current weather
    weather_response = requests.get(
        WEATHER_URL,
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": (
                "temperature_2m,"
                "relative_humidity_2m,"
                "apparent_temperature,"
                "precipitation,"
                "weather_code,"
                "wind_speed_10m"
            ),
            "timezone": "auto",
        },
        timeout=10,
    )

    weather_response.raise_for_status()

    weather = weather_response.json()
    current = weather["current"]

    return {
        "city": location["name"],
        "country": location.get("country"),
        "temperature_c": current["temperature_2m"],
        "relative_humidity": current["relative_humidity_2m"],
        "apparent_temperature_c": current["apparent_temperature"],
        "precipitation_mm": current["precipitation"],
        "weather_code": current["weather_code"],
        "wind_speed_kmh": current["wind_speed_10m"],
        "time": current["time"],
    }


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8002,
        json_response=True,
    )