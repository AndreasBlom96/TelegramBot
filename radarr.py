import requests

base_url = "whattf?"

def getApiKey():
    with open("sacredtexts.txt", "r") as f:
        lines = f.readlines()
        return lines[1]

#search for movie!
def searchMovie(search_str: str):
    url = "/api/v3/movie/lookup"

if __name__ == "__main__":
    API_key = getApiKey()
    print(API_key)