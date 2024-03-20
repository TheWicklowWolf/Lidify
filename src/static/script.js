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
var finder_items = [];
var socket = io();

function load_lidarr_data(response) {
    var all_checked = true;
    var every_check_box = document.querySelectorAll('input[name="lidarr-item"]')
    if (response.Running) {
        start_stop_button.classList.remove('btn-success');
        start_stop_button.classList.add('btn-warning');
        start_stop_button.textContent = "Stop";
        every_check_box.forEach(item => {
            item.disabled = true;
            if (!item.checked) {
                all_checked = false;
            }
        });
        lidarr_select_all_checkbox.disabled = true;
        lidarr_get_artists_button.disabled = true;
    } else {
        start_stop_button.classList.add('btn-success');
        start_stop_button.classList.remove('btn-warning');
        start_stop_button.textContent = "Start";
        every_check_box.forEach(item => {
            item.disabled = false;
            if (!item.checked) {
                all_checked = false;
            }
        });
        lidarr_select_all_checkbox.disabled = false;
        lidarr_get_artists_button.disabled = false;
    }
    lidarr_select_all_checkbox.checked = all_checked;
}

function append_artists(artists) {
    var artist_row = document.getElementById('artist-row');
    var template = document.getElementById('artist-template');

    artists.forEach(function (artist) {
        var clone = document.importNode(template.content, true);
        var artist_col = clone.querySelector('.col-md-4');

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
        artist_col.querySelector('.followers').textContent = artist.Followers;
        artist_col.querySelector('.popularity').textContent = artist.Popularity;

        if (artist.Status === "Added" || artist.Status === "Already in Lidarr") {
            artist_col.querySelector('.card-body').classList.add('status-green');
            var add_button = artist_col.querySelector('.add-to-lidarr-btn');
            add_button.classList.remove('btn-primary');
            add_button.classList.add('btn-secondary');
            add_button.disabled = true;
            add_button.textContent = artist.Status;
        } else if (artist.Status === "Failed to Add" || artist.Status === "Invalid Path") {
            artist_col.querySelector('.card-body').classList.add('status-red');
            var add_button = artist_col.querySelector('.add-to-lidarr-btn');
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
    toast_template.querySelector('.text-muted').textContent = new Date().toLocaleString();;

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
    var isChecked = this.checked;
    var checkboxes = document.querySelectorAll('input[name="lidarr-item"]');
    checkboxes.forEach(function (checkbox) {
        checkbox.checked = isChecked;
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

socket.on("lidarr_sidebar_update", (response) => {
    if (response.Status == "Success") {
        lidarr_spinner.classList.add('d-none');
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
                lidarr_select_all_checkbox.checked = false;
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
    load_lidarr_data(response);
});

socket.on("refresh_artist", (artist) => {
    var artist_cards = document.querySelectorAll('.col-md-4.mb-3');
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
                add_button.disabled = false
            }
            return;
        }
    });
});

socket.on('more_artists_loaded', function (data) {
    append_artists(data);
});

socket.on('clear', function () {
    var artist_row = document.getElementById('artist-row');
    var artist_cards = artist_row.querySelectorAll('.col-md-4.mb-3');
    artist_cards.forEach(function (card) {
        card.remove();
    });
});

socket.on("new_toast_msg", function (data) {
    show_toast(data.title, data.message)
});

socket.on("disconnect", function () {
    show_toast("Connection Lost", "Please reconnect to continue.");
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
