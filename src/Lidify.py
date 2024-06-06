import json
import time
import logging
import os
import random
import string
import threading
import urllib.parse
from flask import Flask, render_template, request
from flask_socketio import SocketIO
import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import musicbrainzngs
from thefuzz import fuzz
from unidecode import unidecode
import pylast


class DataHandler:
    def __init__(self):
        logging.basicConfig(level=logging.INFO, format="%(message)s")
        self.lidify_logger = logging.getLogger()
        self.musicbrainzngs_logger = logging.getLogger("musicbrainzngs")
        self.musicbrainzngs_logger.setLevel("WARNING")
        self.pylast_logger = logging.getLogger("pylast")
        self.pylast_logger.setLevel("WARNING")
        self.search_in_progress_flag = False
        self.new_found_artists_counter = 0
        self.clients_connected_counter = 0
        self.config_folder = "config"
        self.similar_artists = []
        self.lidarr_items = []
        self.cleaned_lidarr_items = []
        self.stop_event = threading.Event()
        self.stop_event.set()
        if not os.path.exists(self.config_folder):
            os.makedirs(self.config_folder)
        self.load_environ_or_config_settings()

    def load_environ_or_config_settings(self):
        # Defaults
        default_settings = {
            "lidarr_address": "http://192.168.1.2:8686",
            "lidarr_api_key": "",
            "root_folder_path": "/data/media/music/",
            "spotify_client_id": "",
            "spotify_client_secret": "",
            "fallback_to_top_result": False,
            "lidarr_api_timeout": 120.0,
            "quality_profile_id": 1,
            "metadata_profile_id": 1,
            "search_for_missing_albums": False,
            "dry_run_adding_to_lidarr": False,
            "app_name": "Lidify",
            "app_rev": "0.10",
            "app_url": "http://" + "".join(random.choices(string.ascii_lowercase, k=10)) + ".com",
            "last_fm_api_key": "",
            "last_fm_api_secret": "",
            "mode": "Spotify",
            "auto_start": False,
            "auto_start_delay": 60,
        }

        # Load settings from environmental variables (which take precedence) over the configuration file.
        self.lidarr_address = os.environ.get("lidarr_address", "")
        self.lidarr_api_key = os.environ.get("lidarr_api_key", "")
        self.root_folder_path = os.environ.get("root_folder_path", "")
        self.spotify_client_id = os.environ.get("spotify_client_id", "")
        self.spotify_client_secret = os.environ.get("spotify_client_secret", "")
        fallback_to_top_result = os.environ.get("fallback_to_top_result", "")
        self.fallback_to_top_result = fallback_to_top_result.lower() == "true" if fallback_to_top_result != "" else ""
        lidarr_api_timeout = os.environ.get("lidarr_api_timeout", "")
        self.lidarr_api_timeout = float(lidarr_api_timeout) if lidarr_api_timeout else ""
        quality_profile_id = os.environ.get("quality_profile_id", "")
        self.quality_profile_id = int(quality_profile_id) if quality_profile_id else ""
        metadata_profile_id = os.environ.get("metadata_profile_id", "")
        self.metadata_profile_id = int(metadata_profile_id) if metadata_profile_id else ""
        search_for_missing_albums = os.environ.get("search_for_missing_albums", "")
        self.search_for_missing_albums = search_for_missing_albums.lower() == "true" if search_for_missing_albums != "" else ""
        dry_run_adding_to_lidarr = os.environ.get("dry_run_adding_to_lidarr", "")
        self.dry_run_adding_to_lidarr = dry_run_adding_to_lidarr.lower() == "true" if dry_run_adding_to_lidarr != "" else ""
        self.app_name = os.environ.get("app_name", "")
        self.app_rev = os.environ.get("app_rev", "")
        self.app_url = os.environ.get("app_url", "")
        self.last_fm_api_key = os.environ.get("last_fm_api_key", "")
        self.last_fm_api_secret = os.environ.get("last_fm_api_secret", "")
        self.mode = os.environ.get("mode", "")
        auto_start = os.environ.get("auto_start", "")
        self.auto_start = auto_start.lower() == "true" if auto_start != "" else ""
        auto_start_delay = os.environ.get("auto_start_delay", "")
        self.auto_start_delay = float(auto_start_delay) if auto_start_delay else ""

        # Load variables from the configuration file if not set by environmental variables.
        try:
            self.settings_config_file = os.path.join(self.config_folder, "settings_config.json")
            if os.path.exists(self.settings_config_file):
                self.lidify_logger.info(f"Loading Config via file")
                with open(self.settings_config_file, "r") as json_file:
                    ret = json.load(json_file)
                    for key in ret:
                        if getattr(self, key) == "":
                            setattr(self, key, ret[key])
        except Exception as e:
            self.lidify_logger.error(f"Error Loading Config: {str(e)}")

        # Load defaults if not set by an environmental variable or configuration file.
        for key, value in default_settings.items():
            if getattr(self, key) == "":
                setattr(self, key, value)

        # Save config.
        self.save_config_to_file()

        if self.auto_start:
            try:
                auto_start_thread = threading.Timer(self.auto_start_delay, self.automated_startup)
                auto_start_thread.daemon = True
                auto_start_thread.start()

            except Exception as e:
                self.lidify_logger.error(f"Auto Start Error: {str(e)}")

    def automated_startup(self):
        self.get_artists_from_lidarr(checked=True)
        artists = [x["name"] for x in self.lidarr_items]
        self.start(artists)

    def connection(self):
        if self.similar_artists:
            if self.clients_connected_counter == 0:
                if len(self.similar_artists) > 15:
                    self.similar_artists = random.sample(self.similar_artists, 15)
                else:
                    self.lidify_logger.info(f"Shuffling Artists")
                    random.shuffle(self.similar_artists)
                self.raw_new_artists = []
            socketio.emit("more_artists_loaded", self.similar_artists)

        self.clients_connected_counter += 1

    def disconnection(self):
        self.clients_connected_counter = max(0, self.clients_connected_counter - 1)

    def start(self, data):
        try:
            socketio.emit("clear")
            self.new_found_artists_counter = 1
            self.raw_new_artists = []
            self.artists_to_use_in_search = []
            self.similar_artists = []

            for item in self.lidarr_items:
                item_name = item["name"]
                if item_name in data:
                    item["checked"] = True
                    self.artists_to_use_in_search.append(item_name)
                else:
                    item["checked"] = False

            if self.artists_to_use_in_search:
                self.stop_event.clear()
            else:
                self.stop_event.set()
                raise Exception("No Lidarr Artists Selected")

        except Exception as e:
            self.lidify_logger.error(f"Statup Error: {str(e)}")
            self.stop_event.set()
            ret = {"Status": "Error", "Code": str(e), "Data": self.lidarr_items, "Running": not self.stop_event.is_set()}
            socketio.emit("lidarr_sidebar_update", ret)

        else:
            self.find_similar_artists()

    def get_artists_from_lidarr(self, checked=False):
        try:
            self.lidify_logger.info(f"Getting Artists from Lidarr")
            self.lidarr_items = []
            endpoint = f"{self.lidarr_address}/api/v1/artist"
            headers = {"X-Api-Key": self.lidarr_api_key}
            response = requests.get(endpoint, headers=headers, timeout=self.lidarr_api_timeout)

            if response.status_code == 200:
                self.full_lidarr_artist_list = response.json()
                self.lidarr_items = [{"name": unidecode(artist["artistName"], replace_str=" "), "checked": checked} for artist in self.full_lidarr_artist_list]
                self.lidarr_items.sort(key=lambda x: x["name"].lower())
                self.cleaned_lidarr_items = [item["name"].lower() for item in self.lidarr_items]
                status = "Success"
                data = self.lidarr_items
            else:
                status = "Error"
                data = response.text

            ret = {"Status": status, "Code": response.status_code if status == "Error" else None, "Data": data, "Running": not self.stop_event.is_set()}

        except Exception as e:
            self.lidify_logger.error(f"Getting Artist Error: {str(e)}")
            ret = {"Status": "Error", "Code": 500, "Data": str(e), "Running": not self.stop_event.is_set()}

        finally:
            socketio.emit("lidarr_sidebar_update", ret)

    def find_similar_artists(self):
        if self.stop_event.is_set() or self.search_in_progress_flag:
            return
        elif self.mode == "Spotify" and self.new_found_artists_counter > 0:
            try:
                self.lidify_logger.info(f"Searching for new artists via {self.mode}")
                self.new_found_artists_counter = 0
                self.search_in_progress_flag = True
                random_artists = random.sample(self.artists_to_use_in_search, min(5, len(self.artists_to_use_in_search)))

                sp = spotipy.Spotify(retries=0, auth_manager=SpotifyClientCredentials(client_id=self.spotify_client_id, client_secret=self.spotify_client_secret))

                for artist_name in random_artists:
                    if self.stop_event.is_set():
                        break
                    search_id = None
                    results = sp.search(q=artist_name, type="artist")
                    items = results.get("artists", {}).get("items", [])
                    search_id = items[0]["id"]
                    related_artists = sp.artist_related_artists(search_id)
                    for artist in related_artists["artists"]:
                        if self.stop_event.is_set():
                            break
                        cleaned_artist = unidecode(artist["name"]).lower()
                        if cleaned_artist not in self.cleaned_lidarr_items and not any(artist["name"] == item["Name"] for item in self.raw_new_artists):
                            genres = ", ".join([genre.title() for genre in artist.get("genres", [])]) if artist.get("genres") else "Unknown Genre"
                            followers = self.format_numbers(artist.get("followers", {}).get("total", 0))
                            pop = artist.get("popularity", "0")
                            img_link = artist.get("images")[0]["url"] if artist.get("images") else None
                            exclusive_artist = {
                                "Name": artist["name"],
                                "Genre": genres,
                                "Status": "",
                                "Img_Link": img_link,
                                "Popularity": f"Popularity: {pop}/100",
                                "Followers": f"Followers: {followers}",
                            }
                            self.raw_new_artists.append(exclusive_artist)
                            socketio.emit("more_artists_loaded", [exclusive_artist])
                            self.new_found_artists_counter += 1

                if self.new_found_artists_counter == 0:
                    self.lidify_logger.info("Search Exhausted - Try selecting more artists from existing Lidarr library")
                    socketio.emit("new_toast_msg", {"title": "Search Exhausted", "message": "Try selecting more artists from existing Lidarr library"})
                else:
                    self.similar_artists.extend(self.raw_new_artists)

            except Exception as e:
                self.lidify_logger.error(f"Spotify Error: {str(e)}")

            finally:
                self.search_in_progress_flag = False

        elif self.mode == "LastFM" and self.new_found_artists_counter > 0:
            try:
                self.lidify_logger.info(f"Searching for new artists via {self.mode}")
                self.new_found_artists_counter = 0
                self.search_in_progress_flag = True
                random_artists = random.sample(self.artists_to_use_in_search, min(5, len(self.artists_to_use_in_search)))

                lfm = pylast.LastFMNetwork(api_key=self.last_fm_api_key, api_secret=self.last_fm_api_secret)
                for artist_name in random_artists:
                    if self.stop_event.is_set():
                        break
                    search_id = None
                    artist = lfm.get_artist(artist_name)
                    related_artists = artist.get_similar()
                    random_related_artists = random.sample(related_artists, min(10, len(related_artists)))
                    for artist in random_related_artists:
                        if self.stop_event.is_set():
                            break
                        cleaned_artist = unidecode(artist.item.name).lower()
                        if cleaned_artist not in self.cleaned_lidarr_items and not any(artist.item.name == item["Name"] for item in self.raw_new_artists):
                            artist_obj = lfm.get_artist(artist.item.name)
                            genres = ", ".join([tag.item.get_name().title() for tag in artist_obj.get_top_tags()[:5]]) or "Unknown Genre"
                            listeners = artist_obj.get_listener_count() or 0
                            play_count = artist_obj.get_playcount() or 0
                            try:
                                img_link = None
                                endpoint = "https://api.deezer.com/search/artist"
                                params = {"q": artist.item.name}
                                response = requests.get(endpoint, params=params)
                                data = response.json()
                                if "data" in data and data["data"]:
                                    artist_info = data["data"][0]
                                    img_link = artist_info.get("picture_xl", artist_info.get("picture_large", artist_info.get("picture_medium", artist_info.get("picture", ""))))

                            except Exception as e:
                                self.lidify_logger.error(f"Deezer Error: {str(e)}")

                            exclusive_artist = {
                                "Name": artist.item.name,
                                "Genre": genres,
                                "Status": "",
                                "Img_Link": img_link if img_link else "https://via.placeholder.com/300x200",
                                "Popularity": f"Play Count: {self.format_numbers(play_count)}",
                                "Followers": f"Listeners: {self.format_numbers(listeners)}",
                            }
                            self.raw_new_artists.append(exclusive_artist)
                            socketio.emit("more_artists_loaded", [exclusive_artist])
                            self.new_found_artists_counter += 1

                if self.new_found_artists_counter == 0:
                    self.lidify_logger.info("Search Exhausted - Try selecting more artists from existing Lidarr library")
                    socketio.emit("new_toast_msg", {"title": "Search Exhausted", "message": "Try selecting more artists from existing Lidarr library"})
                else:
                    self.similar_artists.extend(self.raw_new_artists)

            except Exception as e:
                self.lidify_logger.error(f"LastFM Error: {str(e)}")

            finally:
                self.search_in_progress_flag = False

        elif self.new_found_artists_counter == 0:
            try:
                self.search_in_progress_flag = True
                self.lidify_logger.info("Search Exhausted - Try selecting more artists from existing Lidarr library")
                socketio.emit("new_toast_msg", {"title": "Search Exhausted", "message": "Try selecting more artists from existing Lidarr library"})
                time.sleep(2)

            except Exception as e:
                self.lidify_logger.error(f"Search Exhausted Error: {str(e)}")

            finally:
                self.search_in_progress_flag = False

    def add_artists(self, raw_artist_name):
        try:
            artist_name = urllib.parse.unquote(raw_artist_name)
            artist_folder = artist_name.replace("/", " ")
            musicbrainzngs.set_useragent(self.app_name, self.app_rev, self.app_url)
            mbid = self.get_mbid_from_musicbrainz(artist_name)
            if mbid:
                lidarr_url = f"{self.lidarr_address}/api/v1/artist"
                headers = {"X-Api-Key": self.lidarr_api_key}
                payload = {
                    "ArtistName": artist_name,
                    "qualityProfileId": self.quality_profile_id,
                    "metadataProfileId": self.metadata_profile_id,
                    "path": os.path.join(self.root_folder_path, artist_folder, ""),
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
                    self.lidify_logger.info(f"Artist '{artist_name}' added successfully to Lidarr.")
                    status = "Added"
                    self.lidarr_items.append({"name": artist_name, "checked": False})
                    self.cleaned_lidarr_items.append(unidecode(artist_name).lower())
                else:
                    self.lidify_logger.error(f"Failed to add artist '{artist_name}' to Lidarr.")
                    error_data = json.loads(response.content)
                    error_message = error_data[0].get("errorMessage", "No Error Message Returned") if error_data else "Error Unknown"
                    self.lidify_logger.error(error_message)
                    if "already been added" in error_message:
                        status = "Already in Lidarr"
                        self.lidify_logger.info(f"Artist '{artist_name}' is already in Lidarr.")
                    elif "configured for an existing artist" in error_message:
                        status = "Already in Lidarr"
                        self.lidify_logger.info(f"'{artist_folder}' folder already configured for an existing artist.")
                    elif "Invalid Path" in error_message:
                        status = "Invalid Path"
                        self.lidify_logger.info(f"Path: {os.path.join(self.root_folder_path, artist_folder, '')} not valid.")
                    else:
                        status = "Failed to Add"

            else:
                status = "Failed to Add"
                self.lidify_logger.info(f"No Matching Artist for: '{artist_name}' in MusicBrainz.")
                socketio.emit("new_toast_msg", {"title": "Failed to add Artist", "message": f"No Matching Artist for: '{artist_name}' in MusicBrainz."})

            for item in self.similar_artists:
                if item["Name"] == artist_name:
                    item["Status"] = status
                    socketio.emit("refresh_artist", item)
                    break

        except Exception as e:
            self.lidify_logger.error(f"Adding Artist Error: {str(e)}")

    def get_mbid_from_musicbrainz(self, artist_name):
        result = musicbrainzngs.search_artists(artist=artist_name)
        mbid = None

        if "artist-list" in result:
            artists = result["artist-list"]

            for artist in artists:
                match_ratio = fuzz.ratio(artist_name.lower(), artist["name"].lower())
                decoded_match_ratio = fuzz.ratio(unidecode(artist_name.lower()), unidecode(artist["name"].lower()))
                if match_ratio > 90 or decoded_match_ratio > 90:
                    mbid = artist["id"]
                    self.lidify_logger.info(f"Artist '{artist_name}' matched '{artist['name']}' with MBID: {mbid}  Match Ratio: {max(match_ratio, decoded_match_ratio)}")
                    break
            else:
                if self.fallback_to_top_result and artists:
                    mbid = artists[0]["id"]
                    self.lidify_logger.info(f"Artist '{artist_name}' matched '{artists[0]['name']}' with MBID: {mbid}  Match Ratio: {max(match_ratio, decoded_match_ratio)}")

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

    def format_numbers(self, count):
        if count >= 1000000:
            return f"{count / 1000000:.1f}M"
        elif count >= 1000:
            return f"{count / 1000:.1f}K"
        else:
            return count

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
                        "quality_profile_id": self.quality_profile_id,
                        "metadata_profile_id": self.metadata_profile_id,
                        "search_for_missing_albums": self.search_for_missing_albums,
                        "dry_run_adding_to_lidarr": self.dry_run_adding_to_lidarr,
                        "app_name": self.app_name,
                        "app_rev": self.app_rev,
                        "app_url": self.app_url,
                        "last_fm_api_key": self.last_fm_api_key,
                        "last_fm_api_secret": self.last_fm_api_secret,
                        "mode": self.mode,
                        "auto_start": self.auto_start,
                        "auto_start_delay": self.auto_start_delay,
                    },
                    json_file,
                    indent=4,
                )

        except Exception as e:
            self.lidify_logger.error(f"Error Saving Config: {str(e)}")

    def preview(self, raw_artist_name):
        artist_name = urllib.parse.unquote(raw_artist_name)
        if self.mode == "Spotify":
            try:
                preview_info = None
                sp = spotipy.Spotify(retries=0, auth_manager=SpotifyClientCredentials(client_id=self.spotify_client_id, client_secret=self.spotify_client_secret))
                results = sp.search(q=artist_name, type="artist")
                items = results.get("artists", {}).get("items", [])
                cleaned_artist_name = unidecode(artist_name).lower()
                for item in items:
                    match_ratio = fuzz.ratio(cleaned_artist_name, item.get("name", "").lower())
                    decoded_match_ratio = fuzz.ratio(unidecode(cleaned_artist_name), unidecode(item.get("name", "").lower()))
                    if match_ratio > 90 or decoded_match_ratio > 90:
                        artist_id = item.get("id", "")
                        top_tracks = sp.artist_top_tracks(artist_id)
                        random.shuffle(top_tracks["tracks"])
                        for track in top_tracks["tracks"]:
                            if track.get("preview_url"):
                                preview_info = {"artist": track["artists"][0]["name"], "song": track["name"], "preview_url": track["preview_url"]}
                                break
                        else:
                            preview_info = f"No preview tracks available for artist: {artist_name}"
                            self.lidify_logger.error(preview_info)
                        break
                else:
                    preview_info = f"No Artist match for: {artist_name}"
                    self.lidify_logger.error(preview_info)

            except Exception as e:
                preview_info = f"Error retrieving artist previews: {str(e)}"
                self.lidify_logger.error(preview_info)

            finally:
                socketio.emit("spotify_preview", preview_info, room=request.sid)

        elif self.mode == "LastFM":
            try:
                preview_info = {}
                biography = None
                lfm = pylast.LastFMNetwork(api_key=self.last_fm_api_key, api_secret=self.last_fm_api_secret)
                search_results = lfm.search_for_artist(artist_name)
                artists = search_results.get_next_page()
                cleaned_artist_name = unidecode(artist_name).lower()
                for artist_obj in artists:
                    match_ratio = fuzz.ratio(cleaned_artist_name, artist_obj.name.lower())
                    decoded_match_ratio = fuzz.ratio(unidecode(cleaned_artist_name), unidecode(artist_obj.name.lower()))
                    if match_ratio > 90 or decoded_match_ratio > 90:
                        biography = artist_obj.get_bio_content()
                        preview_info["artist_name"] = artist_obj.name
                        preview_info["biography"] = biography
                        break
                else:
                    preview_info = f"No Artist match for: {artist_name}"
                    self.lidify_logger.error(preview_info)

                if biography is None:
                    preview_info = f"No Biography available for: {artist_name}"
                    self.lidify_logger.error(preview_info)

            except Exception as e:
                preview_info = {"error": f"Error retrieving artist bio: {str(e)}"}
                self.lidify_logger.error(preview_info)

            finally:
                socketio.emit("lastfm_preview", preview_info, room=request.sid)


app = Flask(__name__)
app.secret_key = "secret_key"
socketio = SocketIO(app)
data_handler = DataHandler()


@app.route("/")
def home():
    return render_template("base.html")


@socketio.on("side_bar_opened")
def side_bar_opened():
    if data_handler.lidarr_items:
        ret = {"Status": "Success", "Data": data_handler.lidarr_items, "Running": not data_handler.stop_event.is_set()}
        socketio.emit("lidarr_sidebar_update", ret)


@socketio.on("get_lidarr_artists")
def get_lidarr_artists():
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
    data_handler.connection()


@socketio.on("disconnect")
def disconnection():
    data_handler.disconnection()


@socketio.on("load_settings")
def load_settings():
    data_handler.load_settings()


@socketio.on("update_settings")
def update_settings(data):
    data_handler.update_settings(data)
    data_handler.save_config_to_file()


@socketio.on("start_req")
def starter(data):
    data_handler.start(data)


@socketio.on("stop_req")
def stopper():
    data_handler.stop_event.set()


@socketio.on("load_more_artists")
def load_more_artists():
    thread = threading.Thread(target=data_handler.find_similar_artists, name="FindSimilar")
    thread.daemon = True
    thread.start()


@socketio.on("preview_req")
def preview(artist):
    data_handler.preview(artist)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
