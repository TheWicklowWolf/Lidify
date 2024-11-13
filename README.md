![Build Status](https://github.com/TheWicklowWolf/Lidify/actions/workflows/main.yml/badge.svg)
![Docker Pulls](https://img.shields.io/docker/pulls/thewicklowwolf/lidify.svg)


<p align="center">
  <img src="/src/static/lidify.png" alt="image">
</p>

Music discovery tool that provides recommendations based on selected Lidarr artists. 

## Run using docker-compose

```yaml
services:
  lidify:
    image: thewicklowwolf/lidify:latest
    container_name: lidify
    volumes:
      - /path/to/config:/lidify/config
      - /etc/localtime:/etc/localtime:ro
    ports:
      - 5000:5000
    restart: unless-stopped
```

## Configuration via environment variables

Certain values can be set via environment variables:

* __PUID__: The user ID to run the app with. Defaults to `1000`. 
* __PGID__: The group ID to run the app with. Defaults to `1000`.
* __lidarr_address__: The URL for Lidarr. Defaults to `http://192.168.1.2:8686`.
* __lidarr_api_key__: The API key for Lidarr. Defaults to ``.
* __root_folder_path__: The root folder path for music. Defaults to `/data/media/music/`.
* __spotify_client_id__: The Client ID for Spotify. Defaults to ``.
* __spotify_client_secret__: The Client Secret for Spotify. Defaults to ``.
* __fallback_to_top_result__: Whether to use the top result if no match is found. Defaults to `False`.
* __lidarr_api_timeout__: Timeout duration for Lidarr API calls. Defaults to `120`.
* __quality_profile_id__: Quality profile ID in Lidarr. Defaults to `1`.
* __metadata_profile_id__: Metadata profile ID in Lidarr. Defaults to `1`
* __search_for_missing_albums__: Whether to start searching for albums when adding artists. Defaults to `False`
* __dry_run_adding_to_lidarr__: Whether to run without adding artists in Lidarr. Defaults to `False`
* __app_name__: Name of the application. Defaults to `Lidify`.
* __app_rev__: Application revision. Defaults to `0.01`.
* __app_url__: URL of the application. Defaults to `Random URL`.
* __last_fm_api_key__: The API key for LastFM. Defaults to ``.
* __last_fm_api_secret__: The API secret for LastFM. Defaults to ``.
* __mode__: Mode for discovery (Spotify or LastFM). Defaults to `Spotify`.
* __auto_start__: Whether to run automatically at startup. Defaults to `False`.
* __auto_start_delay__: Delay duration for Auto Start in Seconds (if enabled). Defaults to `60`.

---

<p align="center">
  <img src="/src/static/light.png" alt="image">
</p>

<p align="center">
  <img src="/src/static/dark.png" alt="image">
</p>

---

https://hub.docker.com/r/thewicklowwolf/lidify
