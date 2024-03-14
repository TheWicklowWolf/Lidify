var lidarr_get_artists_button = document.getElementById('lidarr_get_artists_button');
var lidarr_spinner = document.getElementById('lidarr_spinner');
var lidarr_status = document.getElementById('lidarr_status');
var finder_spinner = document.getElementById('finder_spinner');
var finder_status = document.getElementById('finder_status');
var finder_button = document.getElementById('finder_button');
var add_button = document.getElementById('add_button');
var stop_button = document.getElementById('stop_button');
var reset_button = document.getElementById('reset_button');

var lidarr_item_list = document.getElementById("lidarr_item_list");
var lidarr_select_all_checkbox = document.getElementById("lidarr-select-all");
var lidarr_select_all_container = document.getElementById("lidarr-select-all-container");

var finder_table = document.getElementById('finder_table');
var finder_select_all_checkbox = document.getElementById("finder-select-all");
var finder_select_all_container = document.getElementById("finder-select-all-container");

var config_modal = document.getElementById('config_modal');
var save_message = document.getElementById("save_message");
var save_changes_button = document.getElementById("save_changes_button");
const lidarr_address = document.getElementById("lidarr_address");
const lidarr_api_key = document.getElementById("lidarr_api_key");
const root_folder_path = document.getElementById("root_folder_path");
const spotify_client_id = document.getElementById("spotify_client_id");
const spotify_client_secret = document.getElementById("spotify_client_secret");

var lidarr_items = [];
var finder_items = [];
var socket = io();

lidarr_select_all_checkbox.addEventListener("change", function () {
    var isChecked = this.checked;
    var checkboxes = document.querySelectorAll('input[name="lidarr_item"]');
    checkboxes.forEach(function (checkbox) {
        checkbox.checked = isChecked;
    });
});
finder_select_all_checkbox.addEventListener("change", function () {
    var isChecked = this.checked;
    var checkboxes = document.querySelectorAll('input[name="finder_item"]');
    checkboxes.forEach(function (checkbox) {
        checkbox.checked = isChecked;
    });
});

lidarr_get_artists_button.addEventListener('click', function () {
    lidarr_get_artists_button.disabled = true;
    lidarr_spinner.style.display = "inline-flex";
    lidarr_status.textContent = "Accessing Lidarr API";
    lidarr_item_list.innerHTML = '';
    socket.emit("getLidarrArtists");
});

socket.on("lidarr_status", (response) => {
    if (response.Status == "Success") {
        lidarr_get_artists_button.disabled = false;
        lidarr_status.textContent = "Lidarr List Retrieved";
        lidarr_spinner.style.display = "none";
        lidarr_items = response.Data;
        lidarr_item_list.innerHTML = '';
        lidarr_select_all_container.style.display = "block";
        lidarr_select_all_checkbox.checked = false;
        for (var i = 0; i < lidarr_items.length; i++) {
            var item = lidarr_items[i];

            var div = document.createElement("div");
            div.className = "form-check";

            var input = document.createElement("input");
            input.type = "checkbox";
            input.className = "form-check-input";
            input.id = "lidarr_" + i;
            input.name = "lidarr_item";
            input.value = item;

            var label = document.createElement("label");
            label.className = "form-check-label";
            label.htmlFor = "lidarr_" + i;
            label.textContent = item;

            input.addEventListener("change", function () {
                lidarr_select_all_checkbox.checked = false;
            });

            div.appendChild(input);
            div.appendChild(label);

            lidarr_item_list.appendChild(div);
        }
    }
    else if (response.Status == "Stopped") {
        lidarr_item_list.innerHTML = '';
        lidarr_status.textContent = "Stopped"
        lidarr_select_all_container.style.display = "none";
    }
    else {
        lidarr_item_list.innerHTML = '';
        var errorDiv = document.createElement("div");
        errorDiv.textContent = response.Code + " : " + response.Data;
        errorDiv.style.wordBreak = "break-all";
        lidarr_item_list.appendChild(errorDiv);
        lidarr_status.textContent = "Error Accessing Lidarr";
    }
    lidarr_spinner.style.display = "none";
    lidarr_get_artists_button.disabled = false;
});

finder_button.addEventListener('click', function () {
    finder_button.disabled = true;
    add_button.disabled = true;
    finder_status.textContent = "";
    finder_spinner.style.display = "inline-flex";
    var checkedItems = [];
    for (var i = 0; i < lidarr_items.length; i++) {
        var checkbox = document.getElementById("lidarr_" + i);
        if (checkbox.checked) {
            checkedItems.push(checkbox.value);
        }
    }
    socket.emit("finder", { "Data": checkedItems });
});

socket.on("new_artists_refresh", (response) => {
    if (response.Status != "Error") {
        finder_status.textContent = response.Text;
        finder_items = response.Data;
        finder_table.innerHTML = '';
        finder_select_all_container.style.display = "block";
        finder_select_all_checkbox.checked = false;

        finder_items.forEach((item, i) => {
            var row = finder_table.insertRow();

            var checkboxCell = row.insertCell();
            checkboxCell.className = "form-check";
            var tdGenre = row.insertCell();
            var tdStatus = row.insertCell();

            var input = document.createElement("input");
            input.type = "checkbox";
            input.className = "form-check-input";
            input.id = "finder_" + i;
            input.name = "finder_item";
            input.value = item.Name;

            var label = document.createElement("label");
            label.className = "form-check-label";
            label.htmlFor = "finder_" + i;
            label.textContent = item.Name;

            input.addEventListener("change", () => {
                finder_select_all_checkbox.checked = false;
            });

            checkboxCell.appendChild(input);
            checkboxCell.appendChild(label);

            tdGenre.textContent = item.Genre;
            tdStatus.textContent = item.Status;
        });
        finder_table.style.display = 'table';
    } else {
        finder_table.innerHTML = '';
        var errorDiv = document.createElement("div");
        errorDiv.textContent = response.Code + " : " + response.Data;
        errorDiv.style.wordBreak = "break-all";
        finder_table.appendChild(errorDiv);
        finder_status.textContent = "Error Accessing Spotify";
    }
    finder_spinner.style.display = "none";
    finder_button.disabled = false;
    add_button.disabled = false;
});

socket.on("finder_status", (response) => {
    if (response.Status == "Success") {
        finder_spinner.style.display = "none";
        finder_status.textContent = "";
    } else {
        finder_status.textContent = response.Data;
    }
});

add_button.addEventListener('click', function () {
    finder_button.disabled = true;
    add_button.disabled = true;
    finder_spinner.style.display = "inline-flex";
    finder_status.textContent = "Adding Artists...";
    var checkedItems = [];
    for (var i = 0; i < finder_items.length; i++) {
        var checkbox = document.getElementById("finder_" + i);
        if (checkbox) {
            if (checkbox.checked) {
                checkedItems.push(checkbox.value);
            }
        }
    }
    socket.emit("adder", { "Data": checkedItems });
});

stop_button.addEventListener('click', function () {
    socket.emit("stopper");
});

config_modal.addEventListener('show.bs.modal', function (event) {
    socket.emit("loadSettings");

    function handleSettingsLoaded(settings) {
        lidarr_address.value = settings.lidarr_address;
        lidarr_api_key.value = settings.lidarr_api_key;
        root_folder_path.value = settings.root_folder_path;
        spotify_client_id.value = settings.spotify_client_id;
        spotify_client_secret.value = settings.spotify_client_secret;
        socket.off("settingsLoaded", handleSettingsLoaded);
    }
    socket.on("settingsLoaded", handleSettingsLoaded);
});

save_changes_button.addEventListener("click", () => {
    socket.emit("updateSettings", {
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

reset_button.addEventListener('click', function () {
    socket.emit("reset");
    finder_table.innerHTML = '';
    finder_spinner.style.display = "none";
    finder_status.textContent = "";
    finder_select_all_container.style.display = "none";
    finder_button.disabled = false;
    add_button.disabled = false;
});

const theme_switch = document.getElementById('theme_switch');
const savedTheme = localStorage.getItem('theme');
const savedSwitchPosition = localStorage.getItem('switchPosition');

if (savedSwitchPosition) {
    theme_switch.checked = savedSwitchPosition === 'true';
}

if (savedTheme) {
    document.documentElement.setAttribute('data-bs-theme', savedTheme);
}

theme_switch.addEventListener('click', () => {
    if (document.documentElement.getAttribute('data-bs-theme') === 'dark') {
        document.documentElement.setAttribute('data-bs-theme', 'light');
    } else {
        document.documentElement.setAttribute('data-bs-theme', 'dark');
    }
    localStorage.setItem('theme', document.documentElement.getAttribute('data-bs-theme'));
    localStorage.setItem('switchPosition', theme_switch.checked);
});
