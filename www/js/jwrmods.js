let temp = null;

function update_time() {
    let time = document.getElementById("time");
    let xhr = new XMLHttpRequest();

    xhr.open("GET", "/api/time", true);

    xhr.addEventListener("load", () => {
        if (xhr.status === 200) {
            time.innerText = xhr.responseText;
        } else {
            time.innerText = "Во время обработки запроса возникла ошибка!";
        }
    });

    xhr.addEventListener("error", () => {
        time.innerText = "Во время обработки запроса возникла ошибка!";
    });

    xhr.send();

    setTimeout(() => {
        update_time();
    }, 1000);
}

function admin_login() {
    let alert = document.getElementById("alert");
    let xhr = new XMLHttpRequest();

    xhr.open("GET", ("/api/admin/auth?login=" + encodeURIComponent(document.getElementById("login").value) + "&password=" + encodeURIComponent(document.getElementById("password").value)), true);

    xhr.addEventListener("load", () => {
        if (xhr.status === 200) {
            location.href = "/admin";
        } else if (xhr.status === 401) {
            alert.innerText = "Значение \"Логин\" или \"Пароль\" неверные!";
        } else {
            alert.innerText = "Во время обработки запроса возникла ошибка!";
        }
    });

    xhr.addEventListener("error", () => {
        alert.innerText = "Во время обработки запроса возникла ошибка!";
    });

    xhr.send();
}

function admin_load() {
    let xhr = new XMLHttpRequest();

    xhr.open("GET", ("/api/admin/user"), true);

    xhr.addEventListener("load", () => {
        if (xhr.status === 200) {
            let data = JSON.parse(xhr.responseText);

            document.getElementById("user").innerText += (" " + data["user"]);

            document.getElementById("token").addEventListener("click", () => {
                if (isSecureContext && navigator.clipboard) {
                    navigator.clipboard.writeText(data["token"]).then(r => r);
                } else {
                    let input = document.createElement("input");
                    document.getElementById("token").appendChild(input);
                    input.value = data["token"];
                    input.select();
                    document.execCommand("copy");
                    input.remove();
                }
            });

            document.getElementById("restart").addEventListener("click", () => {
                if (confirm("Вы действительно хотите перезагрузить сервер?\n\nСервер перезагрузится без какого либо ответа.\n\nПосле подтверждения вам нужно будет вручную перезагрузить страницу через несколько секунд.\n\nВнимание: Если в коде сервера имеются ошибки, сервер может не запустится после перезагрузки!")) {
                    let xhr = new XMLHttpRequest();

                    xhr.open("GET", ("/api/admin/restart"), true);
                    xhr.send();

                    location.reload();
                }
            });
        }
    });

    xhr.addEventListener("error", () => {
        alert("Во время обработки запроса возникла ошибка!");
    });

    xhr.send();

    document.getElementById("logout").addEventListener("click", () => {
        document.cookie = "mods_token=null; max-age=0";
        location.reload();
    });

    admin_generate("users");
    admin_count();

    document.getElementById("select").addEventListener("change", (event) => {
        if (temp !== null) {
            document.getElementById("form").innerHTML = temp;
        }

        document.getElementById("form_value_1").style.display = "block";
        document.getElementById("form_value_1_name").innerText = "Пользователь:";

        document.getElementById("form_submit_input").style.display = "block";

        document.getElementById("form_value_1_input").value = "";
        document.getElementById("form_value_2_input").value = "";

        if (event.target.value === "add") {
            document.getElementById("form_value_2").style.display = "block";
            document.getElementById("form_value_2_name").innerText = "Мод:";
        }

        if (event.target.value === "change") {
            document.getElementById("form_value_2").style.display = "block";
            document.getElementById("form_value_2_name").innerText = "Лимит:";
        }

        if (event.target.value === "del") {
            temp = document.getElementById("form").innerHTML;

            document.getElementById("form_value_2").remove();
        }
    });
}

function admin_manage() {
    let value = document.getElementById("form_value_2_input") ? document.getElementById("form_value_2_input").value : "";
    let xhr = new XMLHttpRequest();

    xhr.open("GET", ("/api/admin/" + document.getElementById("select").value + "?user=" + encodeURIComponent(document.getElementById("form_value_1_input").value) + "&mod=" + encodeURIComponent(value) + "&value=" + encodeURIComponent(value)), true);

    xhr.addEventListener("load", () => {
        if (xhr.status === 200) {
            admin_generate("users");
            admin_count();

            document.getElementById("form_value_1").style.display = "none";
            document.getElementById("form_value_2").style.display = "none";
            document.getElementById("form_submit_input").style.display = "none";

            document.getElementById("select_none").selected = true;

            if (document.getElementById("select").value === "add") {
                window.open("/users/" + document.getElementById("form_value_1_input").value, "_blank");
            }
        } else {
            alert("Во время обработки запроса возникла ошибка!");
        }
    });

    xhr.addEventListener("error", () => {
        alert("Во время обработки запроса возникла ошибка!");
    });

    xhr.send();
}

function admin_count() {
    let xhr = new XMLHttpRequest();

    xhr.open("GET", ("/api/admin/count"), true);

    xhr.addEventListener("load", () => {
        if (xhr.status === 200) {
            let data = JSON.parse(xhr.responseText);

            document.getElementById("count").innerText = "Денежный: " + data["money"] + "\nМаксимальный: " + data["maximum"];
        }
    });

    xhr.send();
}

function admin_generate(value, trigger = true) {
    let title = {
        "users": "Пользователи"
    }

    let block = document.getElementById(value);
    block.innerHTML = "";

    let h3 = document.createElement("h3");
    h3.innerText = title[value] + ":";
    h3.addEventListener("click", () => {
        admin_generate(value, !trigger);
    });
    block.appendChild(h3);

    if (trigger) {
        let xhr = new XMLHttpRequest();

        xhr.open("GET", ("/api/admin/" + value), true);

        xhr.addEventListener("load", () => {
            if (xhr.status === 200) {
                let data = JSON.parse(xhr.responseText);

                for (let user in data) {
                    block.appendChild(document.createElement("hr"));

                    let p = document.createElement("p");
                    p.classList.add("users_names");
                    p.innerText = user;
                    block.appendChild(p);

                    let root = document.createElement("div");
                    root.classList.add("users_data");
                    block.appendChild(root);

                    for (let time in data[user]) {
                        let div = document.createElement("div");
                        div.classList.add("users_data_item");
                        root.appendChild(div);

                        let start = document.createElement("div");
                        start.innerText = time + ": " + data[user][time];
                        div.appendChild(start);
                    }
                }
            } else {
                block.innerText = "Во время обработки запроса возникла ошибка!";
            }
        });

        xhr.addEventListener("error", () => {
            block.innerText = "Во время обработки запроса возникла ошибка!";
        });

        xhr.send();
    }
}
