
import logging

logger = logging.getLogger(__name__)

LEGAL_MONITOR_ENUM = [
    "all",
    "future",
    "firstSeason",
    "lastSeason",
    "latestSeason",
    "skip",
    "none",
    "existing"
]


class SerieManager:

    def __init__(self, resource: dict):
        self.resource = resource

    def build_add_payload(self, QualityprofileId: int, Path: str, 
                          RootFolderPath: str, 
                          monitor: str = "All", 
                          tags = [],
                          seasons_to_add: list = []) -> dict:
        """Uses a Serie resource and adding neccesary items to be able to add to sonarr"""
        if monitor not in LEGAL_MONITOR_ENUM: 
            return -1                                  #I should maybe throw somee error here?
        payload = self.resource

        if seasons_to_add:
            self.build_monitor_seasons(seasons_to_add)

        payload["addOptions"] = {
            "ignoreEpisodesWithFiles": False,
            "ignoreEpisodesWithoutFiles": False,
            "monitor": monitor,
            "searchForMissingEpisodes": True
        }

        body = {
            "QualityProfileId": QualityprofileId,
            "Path": Path,
            "RootFolderPath": RootFolderPath,
            "SeasonFolder": True,
            "tags": tags
        }
        payload.update(body)
        return payload

    def build_monitor_seasons(self, seasons_to_monitor: list):
        """build wanted season monitor settings maybe??"""
        seasons = self.resource["seasons"]
        for s, season in enumerate(seasons,1):
            season["monitored"] = s in seasons_to_monitor

    def number_of_seasons(self) -> int:
        """Return number of seasons"""
        return self.resource["statistics"]["seasonCount"]

    def get_status(self) -> str:
        """returns serie status"""
        return self.resource["status"]
    