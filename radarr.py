import requests
import logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

def getApiKey():
    with open("config.txt", "r") as f:
        logger.info("fetching radarr api key")
        lines = f.readlines()
        return lines[1].strip()


class RadarrClient:

    def __init__(self, host="localhost", port="7878"):
        self.API_key = getApiKey()
        self.base_url = f"http://{host}:{port}/api/v3"
        self.headers = {"X-Api-Key": self.API_key}
        self.rootFolder = self._getRootFolder()
    
    def _getRootFolder(self):
        response = self._get("/rootfolder")

        if not response:
            logger.info("could not find rootfolder")
            return None
        else:
            return response[0]['path']

    def get_tags(self):
        """returns list of tags"""
        logger.info("Fetching tags!")
        return self._get("/tag")

    def post_tag(self, label: str):
        label = label.lower()
        body = {
            "label": label
        }

        #check if tag already exist
        list_tags = self.get_tags()
        if list_tags:
            for tag in list_tags:
                if tag["label"]==label:
                    logger.info(f"tag already exists")
                    return -1

        logger.info(f"adding label: {label}")
        return self._post("/tag", body)

    def edit_tag(self, id: int, new_label: str):
        body = {
            "label": new_label
        }
        logger.info("Editing tag with new label")
        return self._put(f"/tag/{id}", data=body)

    def delete_tag(self, id: int):
        """delete tag with id"""
        logger.info(f"Deleting tag with id: {id}")
        return self._delete(f"/tag/{id}")

    def _get_added_movies(self, param: str=None):
        """returns list of all added movies"""
        return self._get("/movie", param)

    def movie_isAvailable(self, tmdbId: str):
        """checks if movie is downloaded and available"""
        resp = self._get_added_movies({"tmdbId": tmdbId})
        if not resp:
            logger.info("Movie is not added: not available")
            return False
        else:
            logger.info(f"movie is added, Available:{resp[0]['isAvailable']}")
            return resp[0]['isAvailable']

    def _post(self, endpoint: str, data=None):
        """request POST method that's safe and catches most error"""
        try:
            response = requests.post(
                url= f"{self.base_url}{endpoint}",
                json= data,
                headers= self.headers
            )
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as http_err:
            try:
                error_info = response.json()
                logger.error(f"{response.status_code}: {error_info}")
            except ValueError:
                logger.info(f"HTTP error {response.status_code}: {response.text}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Unexpected error: {e}")
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
                logger.info("GET did not return any data")
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

    def _delete(self, endpoint, data=None, param=None ):
        """request DELETE method that's safe and catches most error"""
        try:
            response = requests.delete(
                url= f"{self.base_url}{endpoint}",
                json= data,
                headers= self.headers,
                params= param
            )
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as http_err:
            try:
                error_info = response.json()
                logger.error(f"{response.status_code}: {error_info}")
            except ValueError:
                logger.info(f"HTTP error {response.status_code}: {response.text}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Unexpected error: {e}")
        return None

    def _put(self, endpoint, data=None, param=None):
        """request PUT method that's safe and catches most error"""
        try:
            response = requests.put(
                url= f"{self.base_url}{endpoint}",
                json= data,
                headers= self.headers,
                params= param
            )
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as http_err:
            try:
                error_info = response.json()
                logger.error(f"{response.status_code}: {error_info}")
            except ValueError:
                logger.info(f"HTTP error {response.status_code}: {response.text}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Unexpected error: {e}")
        return None

    def search_movie(self, query: str):
        """Search for a movie by title"""
        endpoint = "/movie/lookup"
        logger.info("searching for movie %s", query)
        output = self._get(endpoint, {"term": query})
        return output

    def add_movie(self, title: str, qualityProfileId: int, tmdbId: int, rootFolderPath: str, monitored: bool=True,
     minimumAvailability: str="announced", isAvailable: bool=True ):
        """Adds movie to Radarr and starts"""

        logger.info("adding movie to radarr: %s", title)
        #create json body
        body = {
            "title": title,
            "tmdbId": tmdbId,
            "qualityProfileId": qualityProfileId,
            "monitored": monitored,
            "minimumAvailability": minimumAvailability,
            "isAvailable": isAvailable,
            "rootFolderPath": rootFolderPath,
            "addOptions": {
                "monitor": "movieOnly",
                "searchForMovie": True
            }
        }
        movie = self._get_added_movies({"tmdbId": tmdbId})
        if movie:
            logger.info("Movie is already added, aborting")
            return None

        resp = self._post("/movie", body)
        return resp

    def movie_status(self, tmdbId: str):
        logger.info("Checking status for movie: %s", tmdbId)
        movie = self._get_added_movies({"tmdbId": tmdbId})
        if not movie:
            logger.info("movie %s is not added", tmdbId)
            return "not added"
        
        has_file = movie[0]["hasFile"]
        if has_file:
            return "OK"
        
        #add logic for finding the movie in the queue?

        return "missing"

if __name__ == "__main__":
    r = RadarrClient()
    print(r.API_key)
    print(r.headers)
    resp = r.search_movie("Interstellar")
    
    movie = resp[0]
    print(r.movie_status(movie["tmdbId"]))
    r.add_movie(movie["title"], qualityProfileId= 4, tmdbId=movie["tmdbId"], rootFolderPath=r.rootFolder)
    
    resp = r.search_movie("inception")
    movie = resp[0]
    r.movie_isAvailable(movie["tmdbId"])

    tags = r.get_tags()
    if tags:
        for tag in tags:
            r.delete_tag(tag["id"])
    
    r.post_tag("Yo")
    tags = r.get_tags()
    print(tags)
    for tag in tags:
        if tag["label"]=="yo":
            id = tag["id"]
            print(f"id:{id}")
    
    r.edit_tag(id, "edited_tag_id:10")
    print(r.get_tags())

    #print(r._get_added_movies())
    #r._post("/movies", None)
    #r.add_movie("Inception",0, 54678,78954, "/movies")
    