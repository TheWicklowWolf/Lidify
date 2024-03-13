import json
import logging
import os
import random
import string
import threading
from flask import Flask, render_template
from flask_socketio import SocketIO
import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import musicbrainzngs
from thefuzz import fuzz
from unidecode import unidecode


class DataHandler:
    def __init__(self):
        logging.basicConfig(level=logging.INFO, format="%(message)s")
        self.lidify_logger = logging.getLogger()
        self.musicbrainzngs_logger = logging.getLogger("musicbrainzngs")
        self.musicbrainzngs_logger.setLevel("WARNING")
        self.lidarr_address = os.environ.get("lidarr_address", "http://192.168.1.2:8686")
        self.lidarr_api_key = os.environ.get("lidarr_api_key", "")
        self.root_folder_path = os.environ.get("root_folder_path", "/data/media/music/")
        self.spotify_client_id = os.environ.get("spotify_client_id", "")
        self.spotify_client_secret = os.environ.get("spotify_client_secret", "")
        self.fallback_to_top_result = os.environ.get("fallback_to_top_result", False)
        self.lidarr_api_timeout = os.environ.get("lidarr_api_timeout", 120)
        self.quality_profile_id = os.environ.get("quality_profile_id", 1)
        self.metadata_profile_id = os.environ.get("metadata_profile_id", 1)
        self.search_for_missing_albums = os.environ.get("search_for_missing_albums", False)
        self.dry_run_adding_to_lidarr = os.environ.get("dry_run_adding_to_lidarr", False)
        self.app_name = os.environ.get("app_name", "".join(random.choices(string.ascii_letters, k=10)))
        self.app_rev = os.environ.get("app_rev", "".join(random.choices(string.digits, k=3)))
        self.app_url = os.environ.get("app_url", "http://" + "".join(random.choices(string.ascii_lowercase, k=10)) + ".com")

        self.config_folder = "config"
        if not os.path.exists(self.config_folder):
            os.makedirs(self.config_folder)
        self.settings_config_file = os.path.join(self.config_folder, "settings_config.json")
        if os.path.exists(self.settings_config_file):
            self.load_settings_from_file()
        self.reset()

    def reset(self):
        self.lidarr_items = []
        self.similar_artists = []
        self.stop_event = threading.Event()

    def load_settings_from_file(self):
        try:
            with open(self.settings_config_file, "r") as json_file:
                ret = json.load(json_file)
            self.lidarr_address = ret["lidarr_address"]
            self.lidarr_api_key = ret["lidarr_api_key"]
            self.root_folder_path = ret["root_folder_path"]
            self.spotify_client_id = ret["spotify_client_id"]
            self.spotify_client_secret = ret["spotify_client_secret"]
            self.fallback_to_top_result = ret["fallback_to_top_result"]
            self.lidarr_api_timeout = float(ret["lidarr_api_timeout"])

        except Exception as e:
            self.lidify_logger.error("Error Loading Config: " + str(e))

    def save_config_to_file(self):
        try:
            with open(self.settings_config_file, "w") as json_file:
                json.dump(
                    {
                        "lidarr_address": self.lidarr_address,
                        "lidarr_api_key": self.lidarr_api_key,
                        "root_folder_path": self.root_folder_path,
                        "spotify_client_id": self.spotify_client_id,
                        "spotify_client_secret": self.spotify_client_secret,
                        "fallback_to_top_result": self.fallback_to_top_result,
                        "lidarr_api_timeout": float(self.lidarr_api_timeout),
                    },
                    json_file,
                    indent=4,
                )

        except Exception as e:
            self.lidify_logger.error("Error Saving Config: " + str(e))

    def get_artists_from_lidarr(self):
        try:
            self.stop_event.clear()
            self.lidarr_items = []
            endpoint = f"{self.lidarr_address}/api/v1/artist"
            headers = {"X-Api-Key": self.lidarr_api_key}
            response = requests.get(endpoint, headers=headers, timeout=self.lidarr_api_timeout)
            if response.status_code == 200:
                self.full_lidarr_artist_list = response.json()
                self.lidarr_items = [unidecode(artist["artistName"], replace_str=" ") for artist in self.full_lidarr_artist_list]
                self.lidarr_items.sort(key=str.lower)
                self.cleaned_lidarr_items = [item.lower() for item in self.lidarr_items]
                ret = {"Status": "Success", "Data": self.lidarr_items}
            else:
                ret = {"Status": "Error", "Code": response.status_code, "Data": response.text}

        except Exception as e:
            self.lidify_logger.error(str(e))
            ret = {"Status": "Error", "Code": 500, "Data": str(e)}

        finally:
            if self.stop_event.is_set():
                ret = {"Status": "Stopped", "Code": "", "Data": self.lidarr_items}
            socketio.emit("lidarr_status", ret)

    def find_similar_artists(self, data):
        try:
            self.stop_event.clear()
            self.similar_artists = []
            self.raw_new_artists = []
            sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=self.spotify_client_id, client_secret=self.spotify_client_secret))
            for artist_name in data["Data"]:
                if self.stop_event.is_set():
                    break
                else:
                    search_id = None
                    results = sp.search(q=artist_name, type="artist")
                    items = results.get("artists", {}).get("items", [])

                    for item in items:
                        if self.stop_event.is_set():
                            break
                        elif fuzz.ratio(artist_name.lower(), item["name"].lower()) > 90:
                            search_id = item["id"]
                            break
                    else:
                        if self.fallback_to_top_result == True:
                            search_id = item[0]["id"]

                    if search_id:
                        related_artists = sp.artist_related_artists(search_id)
                        new_artists = [artist["name"] for artist in related_artists["artists"] if unidecode(artist["name"]).lower() not in self.cleaned_lidarr_items]
                        self.raw_new_artists.extend(new_artists)

            self.similar_artists.extend([{"Name": artist, "Status": ""} for artist in set(self.raw_new_artists)])
            self.similar_artists.sort(key=lambda x: x["Name"].lower())
            ret = {
                "Status": "Stopped" if self.stop_event.is_set() else "Success",
                "Data": self.similar_artists,
                "Text": "Stopped" if self.stop_event.is_set() else "Spotify List Updated",
            }

        except Exception as e:
            self.lidify_logger.error(str(e))
            ret = {"Status": "Error", "Code": 500, "Data": str(e), "Text": "Error Searching Spotify"}

        finally:
            socketio.emit("new_artists_refresh", ret)

    def add_artists(self, data):
        try:
            self.stop_event.clear()
            musicbrainzngs.set_useragent(self.app_name, self.app_rev, self.app_url)
            for artist in data["Data"]:
                if self.stop_event.is_set():
                    break
                mbid = self.get_mbid_from_musicbrainz(artist)
                if mbid:
                    lidarr_url = f"{self.lidarr_address}/api/v1/artist"
                    headers = {"X-Api-Key": self.lidarr_api_key}
                    payload = {
                        "ArtistName": artist,
                        "qualityProfileId": self.quality_profile_id,
                        "metadataProfileId": self.metadata_profile_id,
                        "path": os.path.join(self.root_folder_path, artist, ""),
                        "rootFolderPath": self.root_folder_path,
                        "foreignArtistId": mbid,
                        "monitored": True,
                        "addOptions": {"searchForMissingAlbums": self.search_for_missing_albums},
                    }
                    if self.dry_run_adding_to_lidarr:
                        response = requests.Response()
                        response.status_code = 201
                    else:
                        response = requests.post(lidarr_url, headers=headers, json=payload)

                    if response.status_code == 201:
                        self.lidify_logger.info(f"Artist '{artist}' added successfully to Lidarr.")
                        status = "Added to Lidarr"
                        self.lidarr_items.append(artist)
                        self.cleaned_lidarr_items.append(unidecode(artist).lower())
                    else:
                        self.lidify_logger.error(f"Failed to add artist '{artist}' to Lidarr.")
                        error_data = json.loads(response.content)
                        error_messages = json.dumps(error_data[0])
                        self.lidify_logger.error(error_messages)
                        if "already been added" or "configured for an existing artist" in error_messages:
                            status = "Already in Lidarr"
                            self.lidify_logger.info(f"Artist '{artist}' is already in Lidarr.")
                        else:
                            status = "Failed to Add"

                else:
                    status = "No Matching Artist"

                for item in self.similar_artists:
                    if item["Name"] == artist:
                        item["Status"] = status
                        break

            ret = {
                "Status": "Stopped" if self.stop_event.is_set() else "Success",
                "Data": self.similar_artists,
                "Text": "Stopped" if self.stop_event.is_set() else "Lidarr Update Complete",
            }

        except Exception as e:
            self.lidify_logger.error(str(e))
            ret = {"Status": "Error", "Code": 500, "Data": str(e), "Text": "Error Adding Artists"}

        finally:
            socketio.emit("new_artists_refresh", ret)

    def get_mbid_from_musicbrainz(self, artist_name):
        result = musicbrainzngs.search_artists(artist=artist_name)
        mbid = None

        if "artist-list" in result:
            artists = result["artist-list"]

            for artist in artists:
                if fuzz.ratio(unidecode(artist["name"]).lower(), artist_name.lower()) > 90:
                    mbid = artist["id"]
                    self.lidify_logger.info(f"Artist '{artist_name}' matched '{artist['name']}' with MBID: {mbid}  Ratio: {fuzz.ratio(artist_name.lower(), artist['name'].lower())}")
                    break
            else:
                if self.fallback_to_top_result and artists:
                    mbid = artists[0]["id"]
                    self.lidify_logger.info(f"Artist '{artist_name}' matched '{artists[0]['name']}' with MBID: {mbid}  Ratio: {fuzz.ratio(artist_name.lower(), artists[0]['name'].lower())}")

        return mbid

    def load_settings(self):
        try:
            data = {
                "lidarr_address": self.lidarr_address,
                "lidarr_api_key": self.lidarr_api_key,
                "root_folder_path": self.root_folder_path,
                "spotify_client_id": self.spotify_client_id,
                "spotify_client_secret": self.spotify_client_secret,
            }
            socketio.emit("settingsLoaded", data)
        except Exception as e:
            self.lidify_logger.error(f"Failed to load settings: {str(e)}")

    def update_settings(self, data):
        try:
            self.lidarr_address = data["lidarr_address"]
            self.lidarr_api_key = data["lidarr_api_key"]
            self.root_folder_path = data["root_folder_path"]
            self.spotify_client_id = data["spotify_client_id"]
            self.spotify_client_secret = data["spotify_client_secret"]
        except Exception as e:
            self.lidify_logger.error(f"Failed to update settings: {str(e)}")


app = Flask(__name__)
app.secret_key = "secret_key"
socketio = SocketIO(app)
data_handler = DataHandler()


@app.route("/")
def home():
    return render_template("base.html")


@socketio.on("getLidarrArtists")
def getLidarrArtists():
    thread = threading.Thread(target=data_handler.get_artists_from_lidarr, name="Lidarr_Thread")
    thread.daemon = True
    thread.start()


@socketio.on("finder")
def find_similar_artists(data):
    thread = threading.Thread(target=data_handler.find_similar_artists, args=(data,), name="Find_Similar_Thread")
    thread.daemon = True
    thread.start()


@socketio.on("adder")
def add_artists(data):
    thread = threading.Thread(target=data_handler.add_artists, args=(data,), name="Add_Artists_Thread")
    thread.daemon = True
    thread.start()


@socketio.on("connect")
def connection():
    if data_handler.similar_artists:
        ret = {"Status": "Success", "Data": data_handler.similar_artists, "Text": "Reloaded"}
        socketio.emit("new_artists_refresh", ret)


@socketio.on("loadSettings")
def loadSettings():
    data_handler.load_settings()


@socketio.on("updateSettings")
def updateSettings(data):
    data_handler.update_settings(data)
    data_handler.save_config_to_file()


@socketio.on("stopper")
def stopper():
    data_handler.stop_event.set()


@socketio.on("reset")
def reset():
    stopper()
    data_handler.reset()
    socketio.emit("reset")


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
