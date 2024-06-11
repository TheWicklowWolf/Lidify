var return_to_top = document.getElementById("return-to-top");

var lidarr_get_artists_button = document.getElementById('lidarr-get-artists-button');
var start_stop_button = document.getElementById('start-stop-button');
var lidarr_status = document.getElementById('lidarr-status');
var lidarr_spinner = document.getElementById('lidarr-spinner');

var lidarr_item_list = document.getElementById("lidarr-item-list");
var lidarr_select_all_checkbox = document.getElementById("lidarr-select-all");
var lidarr_select_all_container = document.getElementById("lidarr-select-all-container");

var config_modal = document.getElementById('config-modal');
var lidarr_sidebar = document.getElementById('lidarr-sidebar');

var save_message = document.getElementById("save-message");
var save_changes_button = document.getElementById("save-changes-button");
const lidarr_address = document.getElementById("lidarr-address");
const lidarr_api_key = document.getElementById("lidarr-api-key");
const root_folder_path = document.getElementById("root-folder-path");
const spotify_client_id = document.getElementById("spotify-client-id");
const spotify_client_secret = document.getElementById("spotify-client-secret");

var lidarr_items = [];
var socket = io();

function check_if_all_selected() {
    var checkboxes = document.querySelectorAll('input[name="lidarr-item"]');
    var all_checked = true;
    for (var i = 0; i < checkboxes.length; i++) {
        if (!checkboxes[i].checked) {
            all_checked = false;
            break;
        }
    }
    lidarr_select_all_checkbox.checked = all_checked;
}

function load_lidarr_data(response) {
    var every_check_box = document.querySelectorAll('input[name="lidarr-item"]');
    if (response.Running) {
        start_stop_button.classList.remove('btn-success');
        start_stop_button.classList.add('btn-warning');
        start_stop_button.textContent = "Stop";
        every_check_box.forEach(item => {
            item.disabled = true;
        });
        lidarr_select_all_checkbox.disabled = true;
        lidarr_get_artists_button.disabled = true;
    } else {
        start_stop_button.classList.add('btn-success');
        start_stop_button.classList.remove('btn-warning');
        start_stop_button.textContent = "Start";
        every_check_box.forEach(item => {
            item.disabled = false;
        });
        lidarr_select_all_checkbox.disabled = false;
        lidarr_get_artists_button.disabled = false;
    }
    check_if_all_selected();
}

function append_artists(artists) {
    var artist_row = document.getElementById('artist-row');
    var template = document.getElementById('artist-template');

    artists.forEach(function (artist) {
        var clone = document.importNode(template.content, true);
        var artist_col = clone.querySelector('#artist-column');

        artist_col.querySelector('.card-title').textContent = artist.Name;
        artist_col.querySelector('.genre').textContent = artist.Genre;
        if (artist.Img_Link) {
            artist_col.querySelector('.card-img-top').src = artist.Img_Link;
            artist_col.querySelector('.card-img-top').alt = artist.Name;
        } else {
            artist_col.querySelector('.artist-img-container').removeChild(artist_col.querySelector('.card-img-top'));
        }
        artist_col.querySelector('.add-to-lidarr-btn').addEventListener('click', function () {
            add_to_lidarr(artist.Name);
        });
        artist_col.querySelector('.get-preview-btn').addEventListener('click', function () {
            preview_req(artist.Name);
        });
        artist_col.querySelector('.followers').textContent = artist.Followers;
        artist_col.querySelector('.popularity').textContent = artist.Popularity;

        var add_button = artist_col.querySelector('.add-to-lidarr-btn');
        if (artist.Status === "Added" || artist.Status === "Already in Lidarr") {
            artist_col.querySelector('.card-body').classList.add('status-green');
            add_button.classList.remove('btn-primary');
            add_button.classList.add('btn-secondary');
            add_button.disabled = true;
            add_button.textContent = artist.Status;
        } else if (artist.Status === "Failed to Add" || artist.Status === "Invalid Path") {
            artist_col.querySelector('.card-body').classList.add('status-red');
            add_button.classList.remove('btn-primary');
            add_button.classList.add('btn-danger');
            add_button.disabled = true;
            add_button.textContent = artist.Status;
        } else {
            artist_col.querySelector('.card-body').classList.add('status-blue');
        }
        artist_row.appendChild(clone);
    });
}

function add_to_lidarr(artist_name) {
    if (socket.connected) {
        socket.emit('adder', encodeURIComponent(artist_name));
    }
    else {
        show_toast("Connection Lost", "Please reload to continue.");
    }
}

function show_toast(header, message) {
    var toast_container = document.querySelector('.toast-container');
    var toast_template = document.getElementById('toast-template').cloneNode(true);
    toast_template.classList.remove('d-none');

    toast_template.querySelector('.toast-header strong').textContent = header;
    toast_template.querySelector('.toast-body').textContent = message;
    toast_template.querySelector('.text-muted').textContent = new Date().toLocaleString();

    toast_container.appendChild(toast_template);

    var toast = new bootstrap.Toast(toast_template);
    toast.show();

    toast_template.addEventListener('hidden.bs.toast', function () {
        toast_template.remove();
    });
}

return_to_top.addEventListener("click", function () {
    window.scrollTo({ top: 0, behavior: "smooth" });
});

lidarr_select_all_checkbox.addEventListener("change", function () {
    var is_checked = this.checked;
    var checkboxes = document.querySelectorAll('input[name="lidarr-item"]');
    checkboxes.forEach(function (checkbox) {
        checkbox.checked = is_checked;
    });
});

lidarr_get_artists_button.addEventListener('click', function () {
    lidarr_get_artists_button.disabled = true;
    lidarr_spinner.classList.remove('d-none');
    lidarr_status.textContent = "Accessing Lidarr API";
    lidarr_item_list.innerHTML = '';
    socket.emit("get_lidarr_artists");
});

start_stop_button.addEventListener('click', function () {
    var running_state = start_stop_button.textContent.trim() === "Start" ? true : false;
    if (running_state) {
        start_stop_button.classList.remove('btn-success');
        start_stop_button.classList.add('btn-warning');
        start_stop_button.textContent = "Stop";
        var checked_items = Array.from(document.querySelectorAll('input[name="lidarr-item"]:checked'))
            .map(item => item.value);
        document.querySelectorAll('input[name="lidarr-item"]').forEach(item => {
            item.disabled = true;
        });
        lidarr_get_artists_button.disabled = true;
        lidarr_select_all_checkbox.disabled = true;
        socket.emit("start_req", checked_items);
        if (checked_items.length > 0) {
            show_toast("Loading new artists");
        }
    }
    else {
        start_stop_button.classList.add('btn-success');
        start_stop_button.classList.remove('btn-warning');
        start_stop_button.textContent = "Start";
        document.querySelectorAll('input[name="lidarr-item"]').forEach(item => {
            item.disabled = false;
        });
        lidarr_get_artists_button.disabled = false;
        lidarr_select_all_checkbox.disabled = false;
        socket.emit("stop_req");
    }
});

save_changes_button.addEventListener("click", () => {
    socket.emit("update_settings", {
        "lidarr_address": lidarr_address.value,
        "lidarr_api_key": lidarr_api_key.value,
        "root_folder_path": root_folder_path.value,
        "spotify_client_id": spotify_client_id.value,
        "spotify_client_secret": spotify_client_secret.value,
    });
    save_message.style.display = "block";
    setTimeout(function () {
        save_message.style.display = "none";
    }, 1000);
});

config_modal.addEventListener('show.bs.modal', function (event) {
    socket.emit("load_settings");

    function handle_settings_loaded(settings) {
        lidarr_address.value = settings.lidarr_address;
        lidarr_api_key.value = settings.lidarr_api_key;
        root_folder_path.value = settings.root_folder_path;
        spotify_client_id.value = settings.spotify_client_id;
        spotify_client_secret.value = settings.spotify_client_secret;
        socket.off("settingsLoaded", handle_settings_loaded);
    }
    socket.on("settingsLoaded", handle_settings_loaded);
});

lidarr_sidebar.addEventListener('show.bs.offcanvas', function (event) {
    socket.emit("side_bar_opened");
});

window.addEventListener('scroll', function () {
    if (window.innerHeight + window.scrollY >= document.body.offsetHeight) {
        socket.emit('load_more_artists');
    }
});

window.addEventListener('touchmove', function () {
    if (window.innerHeight + window.scrollY >= document.body.offsetHeight) {
        socket.emit('load_more_artists');
    }
});

window.addEventListener('touchend', () => {
    const { scrollHeight, scrollTop, clientHeight } = document.documentElement;
    if (Math.abs(scrollHeight - clientHeight - scrollTop) < 1) {
        socket.emit('load_more_artists');
    }
});

socket.on("lidarr_sidebar_update", (response) => {
    if (response.Status == "Success") {
        lidarr_status.textContent = "Lidarr List Retrieved";
        lidarr_items = response.Data;
        lidarr_item_list.innerHTML = '';
        lidarr_select_all_container.classList.remove('d-none');

        for (var i = 0; i < lidarr_items.length; i++) {
            var item = lidarr_items[i];

            var div = document.createElement("div");
            div.className = "form-check";

            var input = document.createElement("input");
            input.type = "checkbox";
            input.className = "form-check-input";
            input.id = "lidarr-" + i;
            input.name = "lidarr-item";
            input.value = item.name;

            if (item.checked) {
                input.checked = true;
            }

            var label = document.createElement("label");
            label.className = "form-check-label";
            label.htmlFor = "lidarr-" + i;
            label.textContent = item.name;

            input.addEventListener("change", function () {
                check_if_all_selected();
            });

            div.appendChild(input);
            div.appendChild(label);

            lidarr_item_list.appendChild(div);
        }
    }
    else {
        lidarr_status.textContent = response.Code;
    }
    lidarr_get_artists_button.disabled = false;
    lidarr_spinner.classList.add('d-none');
    load_lidarr_data(response);
});

socket.on("refresh_artist", (artist) => {
    var artist_cards = document.querySelectorAll('#artist-column');
    artist_cards.forEach(function (card) {
        var card_body = card.querySelector('.card-body');
        var card_artist_name = card_body.querySelector('.card-title').textContent.trim();

        if (card_artist_name === artist.Name) {
            card_body.classList.remove('status-green', 'status-red', 'status-blue');

            var add_button = card_body.querySelector('.add-to-lidarr-btn');

            if (artist.Status === "Added" || artist.Status === "Already in Lidarr") {
                card_body.classList.add('status-green');
                add_button.classList.remove('btn-primary');
                add_button.classList.add('btn-secondary');
                add_button.disabled = true;
                add_button.textContent = artist.Status;
            } else if (artist.Status === "Failed to Add" || artist.Status === "Invalid Path") {
                card_body.classList.add('status-red');
                add_button.classList.remove('btn-primary');
                add_button.classList.add('btn-danger');
                add_button.disabled = true;
                add_button.textContent = artist.Status;
            } else {
                card_body.classList.add('status-blue');
                add_button.disabled = false;
            }
            return;
        }
    });
});

socket.on('more_artists_loaded', function (data) {
    append_artists(data);
});

socket.on('clear', function () {
    clear_all();
});

socket.on("new_toast_msg", function (data) {
    show_toast(data.title, data.message);
});

socket.on("disconnect", function () {
    show_toast("Connection Lost", "Please reconnect to continue.");
    clear_all();
});

function clear_all() {
    var artist_row = document.getElementById('artist-row');
    var artist_cards = artist_row.querySelectorAll('#artist-column');
    artist_cards.forEach(function (card) {
        card.remove();
    });
}

var preview_modal;
let preview_request_flag = false;

function preview_req(artist_name) {
    if (!preview_request_flag) {
        preview_request_flag = true;
        socket.emit("preview_req", encodeURIComponent(artist_name));
        setTimeout(() => {
            preview_request_flag = false;
        }, 1500);
    }
}

function show_audio_player_modal(artist, song) {
    preview_modal = new bootstrap.Modal(document.getElementById('audio-player-modal'));
    const scrollbar_width = window.innerWidth - document.documentElement.clientWidth;
    document.body.style.overflow = 'hidden';
    document.body.style.paddingRight = `${scrollbar_width}px`;
    preview_modal.show();
    preview_modal._element.addEventListener('hidden.bs.modal', function () {
        stop_audio();
        document.body.style.overflow = 'auto';
        document.body.style.paddingRight = '0';
    });

    var modal_title_label = document.getElementById('audio-player-modal-label');
    if (modal_title_label) {
        modal_title_label.textContent = `${artist} - ${song}`;
    }
}

function play_audio(audio_url) {
    var audio_player = document.getElementById('audio-player');
    audio_player.src = audio_url;
    audio_player.play();
}

function stop_audio() {
    var audio_player = document.getElementById('audio-player');
    audio_player.pause();
    audio_player.currentTime = 0;
    audio_player.removeAttribute('src');
    preview_modal = null;
}

socket.on("spotify_preview", function (preview_info) {
    if (typeof preview_info === 'string') {
        show_toast("Error Retrieving Preview", preview_info);
    } else {
        var artist = preview_info.artist;
        var song = preview_info.song;
        show_audio_player_modal(artist, song);
        play_audio(preview_info.preview_url);
    }
});

socket.on("lastfm_preview", function (preview_info) {
    if (typeof preview_info === 'string') {
        show_toast("Error Retrieving Bio", preview_info);
    }
    else {
        const scrollbar_width = window.innerWidth - document.documentElement.clientWidth;
        document.body.style.overflow = 'hidden';
        document.body.style.paddingRight = `${scrollbar_width}px`;

        var artist_name = preview_info.artist_name;
        var biography = preview_info.biography;
        var modal_title = document.getElementById('bio-modal-title');
        var modal_body = document.getElementById('modal-body');
        modal_title.textContent = artist_name;
        modal_body.textContent = biography;

        var lastfm_modal = new bootstrap.Modal(document.getElementById('bio-modal-modal'));
        lastfm_modal.show();

        lastfm_modal._element.addEventListener('hidden.bs.modal', function () {
            document.body.style.overflow = 'auto';
            document.body.style.paddingRight = '0';
        });
    }
});

const theme_switch = document.getElementById('theme-switch');
const saved_theme = localStorage.getItem('theme');
const saved_switch_position = localStorage.getItem('switch-position');

if (saved_switch_position) {
    theme_switch.checked = saved_switch_position === 'true';
}

if (saved_theme) {
    document.documentElement.setAttribute('data-bs-theme', saved_theme);
}

theme_switch.addEventListener('click', () => {
    if (document.documentElement.getAttribute('data-bs-theme') === 'dark') {
        document.documentElement.setAttribute('data-bs-theme', 'light');
    } else {
        document.documentElement.setAttribute('data-bs-theme', 'dark');
    }
    localStorage.setItem('theme', document.documentElement.getAttribute('data-bs-theme'));
    localStorage.setItem('switch_position', theme_switch.checked);
});
