import requests
import logging

logger = logging.getLogger(__name__)

def getApiKey():
    with open("sacredtexts.txt", "r") as f:
        logger.info("fetching radarr api key")
        lines = f.readlines()
        return lines[1]


class RadarrClient:

    base_url = "http://localhost:7878/api/v3"
    API_key = ""
    headers = {}

    def __init__(self, host="localhost"):
        self.API_key = getApiKey()
        self.base_url = f"http://{host}:7878/api/v3"
        self.headers = {"X-Api-Key": self.API_key}

    def _check_response(self, response: requests.Response):
        try:
            response.raise_for_status()
            data = response.json()

            if not data:
                logger.error("response Empty")
                return None
            return data
        
        except requests.exceptions.RequestException as e:
            logger.error("response is invalid/failed")
            return None
    
    def _get(self, endpoint: str, params=None):
        """request get method that is safe and catches most errors"""

        try:
            response = requests.get(
                f"{self.base_url}{endpoint}",
                params=params,
                headers = self.headers,
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            if not data:
                logger.error("GET did not return any data")
                return None
            return data
        
        except requests.exceptions.ConnectionError:
            logger.error(f"Could not connect to Radarr at {self.base_url}{endpoint}")
        except requests.exceptions.Timeout:
            logger.error("Connection timed out")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"unexpected error: {e}")
        return None


    def search_movie(self, query: str):
        """Search for a movie by title"""
        endpoint = "/movie/lookup"
        logger.info("searching for movie %s", query)
        output = self._get(endpoint, {"term": query})
        return output

if __name__ == "__main__":
    r = RadarrClient()
    print(r.API_key)
    print(r.headers)
    r.search_movie("inception")