![Build Status](https://github.com/TheWicklowWolf/Lidify/actions/workflows/main.yml/badge.svg)
![Docker Pulls](https://img.shields.io/docker/pulls/thewicklowwolf/lidify.svg)


<p align="center">
  <img src="/src/static/lidify.png" alt="image">
</p>

Web GUI for finding similar artists to selected Lidarr artists.


## Run using docker-compose

```yaml
version: "2.1"
services:
  lidify:
    image: thewicklowwolf/lidify:latest
    container_name: lidify
    volumes:
      - /path/to/config:/lidify/config
      - /etc/localtime:/etc/localtime:ro
    ports:
      - 6868:6868
    restart: unless-stopped
```

## Configuration via environment variables

Certain values can be set via environment variables.

* __fallback_to_top_result__: use top result if no match is found. Defaults to `False`.
* __lidarr_api_timeout__: seconds for Lidarr API call timeout. Defaults to `120`.
* __quality_profile_id__: qualityProfileId in Lidarr. Defaults to `1`.
* __metadata_profile_id__: metadataProfileId in Lidarr. Defaults to `1`
* __search_for_missing_albums__: start seaching for albums when adding artists in Lidarr. Defaults to `False`
* __dry_run_adding_to_lidarr__: run without adding artists in Lidarr. Defaults to `False`
* __app_name__: app name. Defaults to `Random Letters`.
* __app_rev__: app rev. Defaults to `Random Numbers`.
* __app_url__: app url. Defaults to `Random URL`.

---

<p align="center">
  <img src="/src/static/light.png" alt="image">
</p>

<p align="center">
  <img src="/src/static/dark.png" alt="image">
</p>

---

https://hub.docker.com/r/thewicklowwolf/lidify
