from sys import executable

from asyncio import new_event_loop, run, sleep, run_coroutine_threadsafe
from datetime import datetime
from discord_webhook import DiscordWebhook, DiscordEmbed
from flask import Flask, request, send_file, render_template, session, redirect, url_for
from hashlib import sha256
from os import makedirs, rename, system, execl
from os.path import isfile, exists
from pytz import timezone
from shutil import move
from subprocess import run as srun
from threading import Thread, Timer
from traceback import format_exc
from waitress import serve

APP, TRIGGER = Flask(import_name=__name__), {"Сохранение": False, "Бэкап": False}
BAT = {"3467418": {"Триггер": False, "Очередь": 0}, "3468896": {"Триггер": False, "Очередь": 0}}
LEVELS = {1: {"Название": "DEBUG", "Цвет": 0x0000FF}, 2: {"Название": "INFO", "Цвет": 0x008000},
          3: {"Название": "WARNING", "Цвет": 0xFFFF00}, 4: {"Название": "ERROR", "Цвет": 0xFFA500},
          5: {"Название": "CRITICAL", "Цвет": 0xFF0000}}
TIME = str(datetime.now(tz=timezone(zone="Europe/Moscow")))[:-7].replace(" ", "_").replace("-", "_").replace(":", "_")
APP.secret_key = b""
LOGIN, PASSWORD = "JackieRyan", ""


async def logs(level, message, file=None):
    try:
        if level == LEVELS[1]:
            from db.settings import settings
            if not settings["Дебаг"]:
                return None
        print(f"{datetime.now(tz=timezone(zone='Europe/Moscow'))} {level['Название']}\n{message}")
        if not exists(path="logs"):
            makedirs(name="logs")
        with open(file=f"logs/{str(TIME)[:-6]}.log", mode="a", encoding="UTF-8") as log_file:
            log_file.write(f"{datetime.now(tz=timezone(zone='Europe/Moscow'))} {level['Название']} {message}\n")
        webhook = DiscordWebhook(username="JWR Mods",
                                 avatar_url="https://cdn.discordapp.com/attachments/1021085537802649661/"
                                            "1021392623044415597/JWR_Mods.png", url="")
        webhook.add_embed(embed=DiscordEmbed(title=level["Название"], description=str(message), color=level["Цвет"]))
        if file is not None:
            with open(file=f"backups/{file}", mode="rb") as backup_file:
                webhook.add_file(file=backup_file.read(), filename=file)
        webhook.execute()
    except Exception:
        await logs(level=LEVELS[4], message=format_exc())


async def save(file, content):
    try:
        while True:
            if not TRIGGER["Сохранение"]:
                TRIGGER["Сохранение"] = True
                if not exists(path="db"):
                    makedirs(name="db")
                if file in ["settings"]:
                    with open(file=f"db/{file}.py", mode="w", encoding="UTF-8") as open_file:
                        open_file.write(f"import datetime\n\n{file} = {content}\n")
                else:
                    with open(file=f"db/{file}.py", mode="w", encoding="UTF-8") as open_file:
                        open_file.write(f"{file} = {content}\n")
                TRIGGER["Сохранение"] = False
                break
            else:
                print("Идет сохранение...")
                await sleep(delay=1)
    except Exception:
        TRIGGER["Сохранение"] = False
        await logs(level=LEVELS[4], message=format_exc())


async def backup():
    try:
        time = int(datetime.now(tz=timezone(zone="Europe/Moscow")).strftime("%H%M%S"))
        print(f"jwrmods: {time}")
        from db.settings import settings
        if (datetime.utcnow() - settings["Дата обновления"]).days >= 1:
            if not TRIGGER["Бэкап"]:
                TRIGGER["Бэкап"] = True
                if not exists(path="backups"):
                    makedirs(name="backups")
                system(command=f"zip\\x64\\7za.exe a -mx9 backups\\jwrmods_{TIME[:-6]}.zip db")
                settings["Дата обновления"] = datetime.utcnow()
                await save(file="settings", content=settings)
                await logs(level=LEVELS[2], message=f"Бэкап БД создан успешно!", file=f"jwrmods_{TIME[:-6]}.zip")
                TRIGGER["Бэкап"] = False
        Timer(interval=1, function=lambda: run(main=backup())).start()
    except Exception:
        TRIGGER["Бэкап"] = False
        await logs(level=LEVELS[4], message=format_exc())


async def bat(user, mod):
    try:
        module = None
        if mod == [x for x in BAT][0]:
            module = "money"
        if mod == [x for x in BAT][1]:
            module = "maximum"
        while True:
            if not BAT[mod]["Триггер"]:
                BAT[mod]["Триггер"] = True
                BAT[mod]["Очередь"] += 1
                with open(file=f"bat/{module}/_INPUT_APK/com/assets/ccwc.txt", mode="w", encoding="UTF-8") as f:
                    f.write(user)
                srun(args=f"bat\\{module}\\bin\\BATCHAPKTOOL.bat launcher 11")
                with open(file=f"bat/{module}/log_recompile.txt", mode="r", encoding="UTF-8") as log:
                    await logs(level=LEVELS[2], message=log.read())
                if isfile(path=f"bat/{module}/_OUT_APK/com.apk"):
                    rename(f"bat/{module}/_OUT_APK/com.apk",
                           f"bat/{module}/_OUT_APK/com.gameloft.android.ANMP.GloftPOHM_{module}.apk")
                    move(f"bat/{module}/_OUT_APK/com.gameloft.android.ANMP.GloftPOHM_{module}.apk",
                         f"files/{user}/com.gameloft.android.ANMP.GloftPOHM_{module}.apk")
                else:
                    raise Exception(f"File \"bat/{module}/_OUT_APK/com.apk\" not found.\n"
                                    f"User: {user}, Time: {datetime.now(tz=timezone(zone='Europe/Moscow'))}")
                BAT[mod]["Триггер"] = False
                BAT[mod]["Очередь"] -= 1
                with open(file=f"files/{user}/index.html", mode="w", encoding="UTF-8") as html:
                    html.write(render_template(template_name_or_list="files.html", user=user, module=module))
                break
            else:
                await sleep(delay=5)
    except Exception:
        BAT[mod]["Триггер"] = False
        BAT[mod]["Очередь"] -= 1
        with open(file=f"files/{user}/index.html", mode="w", encoding="UTF-8") as error:
            error.write(render_template(template_name_or_list="error.html", user=user,
                                        time=datetime.now(tz=timezone(zone="Europe/Moscow"))))
        await logs(level=LEVELS[4], message=format_exc())


@APP.route(rule="/", methods=["GET", "POST"])
async def home():
    try:
        return render_template(template_name_or_list="index.html",
                               time=str(datetime.now(tz=timezone(zone="Europe/Moscow")))[:-13],
                               queue=[BAT[x]["Очередь"] for x in BAT], trigger=TRIGGER)
    except Exception:
        await logs(level=LEVELS[4], message=format_exc())


@APP.route(rule="/templates/css/<file>", methods=["GET", "POST"])
@APP.route(rule="/templates/fonts/<file>", methods=["GET", "POST"])
async def templates(file):
    try:
        if "css" in file:
            return send_file(path_or_file=f"templates/css/{file}")
        if "celestia" in file:
            return send_file(path_or_file=f"templates/fonts/{file}")
    except Exception:
        await logs(level=LEVELS[4], message=format_exc())


@APP.route(rule="/files/<user>/<file>", methods=["GET", "POST"])
async def files(user, file):
    try:
        if file == "index.html":
            with open(file=f"files/{user}/index.html", mode="r", encoding="UTF-8") as file:
                return file.read()
        else:
            return send_file(path_or_file=f"files/{user}/{file}", as_attachment=True)
    except Exception:
        await logs(level=LEVELS[4], message=format_exc())
        if exists(path=f"files/{user}/index.html"):
            return files(user=user, file="index.html")
        else:
            return render_template(template_name_or_list="error.html", user=user,
                                   time=datetime.now(tz=timezone(zone="Europe/Moscow")))


@APP.route(rule="/confirm", methods=["GET", "POST"])
async def confirm(user=None, mod=None):
    try:
        if user is None:
            user = request.get_json(force=True, silent=True)["inv"]
        if mod is None:
            mod = request.get_json(force=True, silent=True)["id"]
        from db.users import users
        users.update({user: {"Лимит": 5, "Установок": 0, "Попыток": 0}})
        await save(file="users", content=users)
        makedirs(name=f"files/{user}")
        time = BAT[mod]["Очередь"] * 15
        if time == 0:
            time = 15
        with open(file=f"files/{user}/index.html", mode="w", encoding="UTF-8") as html:
            html.write(render_template(template_name_or_list="wait.html", queue=BAT[mod]["Очередь"], time=time))
        new_loop = new_event_loop()
        Thread(target=new_loop.run_forever).start()
        run_coroutine_threadsafe(coro=bat(user=user, mod=mod), loop=new_loop)
        return {"id": mod, "inv": user, "goods": render_template(template_name_or_list="response.html", user=user)}
    except Exception:
        await logs(level=LEVELS[4], message=format_exc())
        return {"id": mod, "inv": user, "error": render_template(template_name_or_list="error.html", user=user,
                                                                 time=datetime.now(tz=timezone(zone="Europe/Moscow")))}


@APP.route(rule="/start/<user>", methods=["GET", "POST"])
async def start(user):
    try:
        print(user)
        from db.users import users
        if users[user]["Установок"] < users[user]["Лимит"]:
            users[user]["Установок"] += 1
            users[user]["Попыток"] += 1
            await save(file="users", content=users)
            return "1125"
        else:
            users[user]["Попыток"] += 1
            await save(file="users", content=users)
            if users[user]["Попыток"] == 20:
                await logs(level=LEVELS[3], message=f"Пользователь {user} превысил лимит 20 попыток!")
            if users[user]["Попыток"] == 100:
                await logs(level=LEVELS[5], message=f"Пользователь {user} превысил лимит 100 попыток!")
            return "1126"
    except Exception:
        await logs(level=LEVELS[4], message=format_exc())
        return "1127"


@APP.route(rule="/admin", methods=["GET", "POST"])
async def admin():
    try:
        def data():
            variables_str, triggers_str, settings_str, users_str = "", "", "", ""
            for item in BAT:
                variables_str += f"{item}: {BAT[item]}\n"
            for item in TRIGGER:
                triggers_str += f"{item}: {TRIGGER[item]}\n"
            from db.settings import settings
            for item in settings:
                settings_str += f"{item}: {settings[item]}\n"
            from db.users import users
            for item in users:
                users_str += f"{item}: {users[item]}\n"
            return render_template(template_name_or_list="admin.html", variables=variables_str, triggers=triggers_str,
                                   settings=settings_str, users=users_str)

        if len(request.form) == 0:
            if "user" in session and "token" in session:
                if session["user"] == LOGIN and session["token"] == PASSWORD:
                    return data()
                else:
                    return render_template(template_name_or_list="login.html")
            else:
                return render_template(template_name_or_list="login.html")
        else:
            if "login" in request.form and "password" in request.form:
                pass_hash = sha256(request.form["password"].encode(encoding="UTF-8")).hexdigest()
                if request.form["login"] == LOGIN and pass_hash == PASSWORD:
                    session["user"] = LOGIN
                    session["token"] = PASSWORD
                    session.permanent = True
                    return redirect(location=url_for(endpoint="admin"))
                else:
                    return render_template(template_name_or_list="login.html")
            elif "debug" in request.form and "token" in session:
                if session["token"] == PASSWORD:
                    from db.settings import settings
                    if settings["Дебаг"]:
                        settings["Дебаг"] = False
                    else:
                        settings["Дебаг"] = True
                    await save(file="settings", content=settings)
                    return redirect(location=url_for(endpoint="admin"))
            elif "res" in request.form and "token" in session:
                if session["token"] == PASSWORD:
                    try:
                        execl(executable, executable, "jwrmods.py")
                    except Exception:
                        await logs(level=LEVELS[1], message=format_exc())
                        execl("python/python.exe", "python/python.exe", "jwrmods.py")
                    return redirect(location=url_for(endpoint="admin"))
            elif "select" in request.form and "token" in session:
                if request.form["select"] == "add" and session["token"] == PASSWORD:
                    res = await confirm(user=request.form["id"], mod=request.form["value"])
                    return res["goods"] if "goods" in res else res["error"]
                elif request.form["select"] == "change" and session["token"] == PASSWORD:
                    from db.users import users
                    users[request.form["id"]]["Лимит"] = int(request.form["value"])
                    await save(file="users", content=users)
                    return redirect(location=url_for(endpoint="admin"))
                elif request.form["select"] == "del" and session["token"] == PASSWORD:
                    from db.users import users
                    if request.form["value"] == "All":
                        users = {}
                    else:
                        users.pop(request.form["id"])
                    await save(file="users", content=users)
                    return redirect(location=url_for(endpoint="admin"))
                else:
                    return redirect(location=url_for(endpoint="admin"))
            else:
                return render_template(template_name_or_list="login.html")
    except Exception:
        await logs(level=LEVELS[4], message=format_exc())
        return redirect(location=url_for(endpoint="admin"))


if __name__ == "__main__":
    try:
        run(main=backup())
        serve(app=APP, port=80)
    except Exception:
        run(main=logs(level=LEVELS[4], message=format_exc()))
