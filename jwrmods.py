from sys import executable

from asyncio import new_event_loop, run, sleep, run_coroutine_threadsafe
from datetime import datetime
from discord_webhook import DiscordWebhook, DiscordEmbed
from flask import Flask, request, send_file, session, redirect, url_for, render_template_string
from hashlib import sha256
from os import makedirs, rename, system, execl
from os.path import isfile, exists
from psutil import cpu_percent, virtual_memory, disk_partitions, disk_usage
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
TIME = str(datetime.now(tz=timezone(zone="Europe/Moscow")))[:-13].replace(" ", "_").replace("-", "_").replace(":", "_")
APP.secret_key = b""
LOGIN, PASSWORD = "JackieRyan", ""


async def logs(level, message, file=None):
    try:
        if level == LEVELS[1]:
            from db.settings import settings
            if not settings["Дебаг"]:
                return None
        print(f"{datetime.now(tz=timezone(zone='Europe/Moscow'))} {level['Название']}\n{message}")
        if not exists(path="temp/logs"):
            makedirs(name="temp/logs")
        with open(file=f"temp/logs/{TIME}.log", mode="a+", encoding="UTF-8") as log_file:
            log_file.write(f"{datetime.now(tz=timezone(zone='Europe/Moscow'))} {level['Название']}:\n{message}\n\n")
        webhook = DiscordWebhook(username="JWR Mods",
                                 avatar_url="https://cdn.discordapp.com/attachments/1021085537802649661/"
                                            "1021392623044415597/JWR_Mods.png", url="")
        webhook.add_embed(embed=DiscordEmbed(title=level["Название"], description=str(message), color=level["Цвет"]))
        if file is not None:
            with open(file=f"temp/backups/{file}", mode="rb") as backup_file:
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
                    with open(file=f"db/{file}.py", mode="w", encoding="UTF-8") as db_file:
                        db_file.write(f"import datetime\n\n{file} = {content}\n")
                else:
                    with open(file=f"db/{file}.py", mode="w", encoding="UTF-8") as db_file:
                        db_file.write(f"{file} = {content}\n")
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
                if not exists(path="temp/backups"):
                    makedirs(name="temp/backups")
                date = str(datetime.now(tz=timezone(zone="Europe/Moscow")))[:-13]
                time = date.replace(" ", "_").replace("-", "_").replace(":", "_")
                system(command=f"bin\\zip\\x64\\7za.exe a -mx9 temp\\backups\\jwrmods_{time}.zip db")
                settings["Дата обновления"] = datetime.utcnow()
                await save(file="settings", content=settings)
                await logs(level=LEVELS[2], message=f"Бэкап БД создан успешно!", file=f"jwrmods_{time}.zip")
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
                with open(file=f"bin/bat/{module}/_INPUT_APK/com/assets/ccwc.txt", mode="w", encoding="UTF-8") as ccwc:
                    ccwc.write(user)
                srun(args=f"bin\\bat\\{module}\\bin\\BATCHAPKTOOL.bat launcher 11")
                with open(file=f"bin/bat/{module}/log_recompile.txt", mode="r", encoding="UTF-8") as log_recompile:
                    await logs(level=LEVELS[2], message=log_recompile.read())
                if isfile(path=f"bin/bat/{module}/_OUT_APK/com.apk"):
                    rename(f"bin/bat/{module}/_OUT_APK/com.apk",
                           f"bin/bat/{module}/_OUT_APK/com.gameloft.android.ANMP.GloftPOHM_{module}.apk")
                    move(f"bin/bat/{module}/_OUT_APK/com.gameloft.android.ANMP.GloftPOHM_{module}.apk",
                         f"temp/files/{user}/com.gameloft.android.ANMP.GloftPOHM_{module}.apk")
                else:
                    raise Exception(f"File \"bin/bat/{module}/_OUT_APK/com.apk\" not found.\n"
                                    f"User: {user}, Time: {datetime.now(tz=timezone(zone='Europe/Moscow'))}")
                BAT[mod]["Триггер"] = False
                BAT[mod]["Очередь"] -= 1
                with open(file=f"temp/files/{user}/index.html", mode="w", encoding="UTF-8") as index_html:
                    with open(file=f"www/html/files.html", mode="r", encoding="UTF-8") as files_html:
                        index_html.write(render_template_string(source=files_html.read(), user=user, module=module))
                break
            else:
                await sleep(delay=5)
    except Exception:
        BAT[mod]["Триггер"] = False
        BAT[mod]["Очередь"] -= 1
        with open(file=f"temp/files/{user}/index.html", mode="w", encoding="UTF-8") as index_html:
            with open(file=f"www/html/error.html", mode="r", encoding="UTF-8") as error_html:
                index_html.write(render_template_string(source=error_html.read(), user=user,
                                                        time=datetime.now(tz=timezone(zone="Europe/Moscow"))))
        await logs(level=LEVELS[4], message=format_exc())


@APP.route(rule="/", methods=["GET", "POST"])
async def home():
    try:
        with open(file=f"www/html/index.html", mode="r", encoding="UTF-8") as index_html:
            return render_template_string(source=index_html.read(),
                                          time=str(datetime.now(tz=timezone(zone="Europe/Moscow")))[:-13],
                                          queue=[BAT[x]["Очередь"] for x in BAT], trigger=TRIGGER)
    except Exception:
        await logs(level=LEVELS[4], message=format_exc())


@APP.route(rule="/css/<file>", methods=["GET", "POST"])
async def css(file):
    try:
        return send_file(path_or_file=f"www/css/{file}")
    except Exception:
        await logs(level=LEVELS[4], message=format_exc())


@APP.route(rule="/fonts/<file>", methods=["GET", "POST"])
async def fonts(file):
    try:
        return send_file(path_or_file=f"www/fonts/{file}")
    except Exception:
        await logs(level=LEVELS[4], message=format_exc())


@APP.route(rule="/images/<file>", methods=["GET", "POST"])
async def images(file):
    try:
        return send_file(path_or_file=f"www/images/{file}")
    except Exception:
        await logs(level=LEVELS[4], message=format_exc())


@APP.route(rule="/confirm", methods=["GET", "POST"])
async def confirm(user=None, mod=None):
    try:
        if user is None:
            user = request.get_json(force=True, silent=True)["inv"]
        if mod is None:
            mod = request.get_json(force=True, silent=True)["id"]
        makedirs(name=f"temp/files/{user}")
        from db.users import users
        users.update({user: {"Лимит": 5, "Установок": 0, "Попыток": 0}})
        await save(file="users", content=users)
        time = BAT[mod]["Очередь"] * 15
        if time == 0:
            time = 15
        with open(file=f"temp/files/{user}/index.html", mode="w", encoding="UTF-8") as index_html:
            with open(file=f"www/html/wait.html", mode="r", encoding="UTF-8") as wait_html:
                index_html.write(render_template_string(source=wait_html.read(), queue=BAT[mod]["Очередь"], time=time))
        new_loop = new_event_loop()
        Thread(target=new_loop.run_forever).start()
        run_coroutine_threadsafe(coro=bat(user=user, mod=mod), loop=new_loop)
        with open(file=f"www/html/response.html", mode="r", encoding="UTF-8") as response_html:
            return {"id": mod, "inv": user, "goods": render_template_string(source=response_html.read(), user=user)}
    except Exception:
        await logs(level=LEVELS[4], message=format_exc())
        with open(file=f"www/html/error.html", mode="r", encoding="UTF-8") as error_html:
            return {"id": mod, "inv": user, "error": render_template_string(
                source=error_html.read(), user=user, time=datetime.now(tz=timezone(zone="Europe/Moscow")))}


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


@APP.route(rule="/files/<user>/<file>", methods=["GET", "POST"])
async def files(user, file):
    try:
        if file == "index.html":
            with open(file=f"temp/files/{user}/index.html", mode="r", encoding="UTF-8") as index_html:
                return index_html.read()
        else:
            return send_file(path_or_file=f"temp/files/{user}/{file}", as_attachment=True)
    except Exception:
        await logs(level=LEVELS[4], message=format_exc())
        if exists(path=f"temp/files/{user}/index.html"):
            return files(user=user, file="index.html")
        else:
            with open(file=f"www/html/error.html", mode="r", encoding="UTF-8") as error_html:
                return render_template_string(source=error_html.read(), user=user,
                                              time=datetime.now(tz=timezone(zone="Europe/Moscow")))


@APP.route(rule="/admin", methods=["GET", "POST"])
async def admin():
    try:
        if len(request.form) == 0:
            if "user" in session and "token" in session:
                if session["user"] == LOGIN and session["token"] == PASSWORD:
                    variables_str, triggers_str, settings_str, users_str = "", "", "", ""
                    variables_rows, triggers_rows, settings_rows, users_rows = 1, 1, 1, 1
                    variables_cols, triggers_cols, settings_cols, users_cols = 55, 55, 55, 55
                    for item in BAT:
                        variables_str += f"{item}: {BAT[item]}\n"
                        if len(f"{item}: {BAT[item]}\n") > variables_cols:
                            variables_cols = len(f"{item}: {BAT[item]}\n") + 5
                        variables_rows += 1
                    for item in TRIGGER:
                        triggers_str += f"{item}: {TRIGGER[item]}\n"
                        if len(f"{item}: {TRIGGER[item]}\n") > triggers_cols:
                            triggers_cols = len(f"{item}: {TRIGGER[item]}\n") + 5
                        triggers_rows += 1
                    from db.settings import settings
                    for item in settings:
                        settings_str += f"{item}: {settings[item]}\n"
                        if len(f"{item}: {settings[item]}\n") > settings_cols:
                            settings_cols = len(f"{item}: {settings[item]}\n") + 5
                        settings_rows += 1
                    from db.users import users
                    for item in users:
                        users_str += f"{item}: {users[item]}\n"
                        if len(f"{item}: {users[item]}\n") > users_cols:
                            users_cols = len(f"{item}: {users[item]}\n") + 5
                        users_rows += 1
                    with open(file=f"www/html/admin.html", mode="r", encoding="UTF-8") as admin_html:
                        return render_template_string(
                            source=admin_html.read(), variables_str=variables_str, variables_cols=variables_cols,
                            variables_rows=variables_rows, triggers_str=triggers_str, triggers_cols=triggers_cols,
                            triggers_rows=triggers_rows, settings_str=settings_str, settings_cols=settings_cols,
                            settings_rows=settings_rows, users_str=users_str, users_cols=users_cols,
                            users_rows=users_rows)
            with open(file=f"www/html/login.html", mode="r", encoding="UTF-8") as login_html:
                return render_template_string(source=login_html.read())
        else:
            if "login" in request.form and "password" in request.form:
                pass_hash = sha256(request.form["password"].encode(encoding="UTF-8")).hexdigest()
                if request.form["login"] == LOGIN and pass_hash == PASSWORD:
                    session["user"] = LOGIN
                    session["token"] = PASSWORD
                    session.permanent = True
            if "debug" in request.form and "token" in session:
                if session["token"] == PASSWORD:
                    from db.settings import settings
                    if settings["Дебаг"]:
                        settings["Дебаг"] = False
                    else:
                        settings["Дебаг"] = True
                    await save(file="settings", content=settings)
            if "res" in request.form and "token" in session:
                if session["token"] == PASSWORD:
                    try:
                        execl(executable, executable, "jwrmods.py")
                    except Exception:
                        await logs(level=LEVELS[1], message=format_exc())
                        execl("bin/python/python.exe", "bin/python/python.exe", "jwrmods.py")
            if "select" in request.form and "value" in request.form and "token" in session:
                if request.form["select"] == "add" and request.form["value"] != "" and session["token"] == PASSWORD:
                    res = await confirm(user=request.form["id"], mod=request.form["value"])
                    return res["goods"] if "goods" in res else res["error"]
                if request.form["select"] == "change" and request.form["value"] != "" and session["token"] == PASSWORD:
                    from db.users import users
                    users[request.form["id"]]["Лимит"] = int(request.form["value"])
                    await save(file="users", content=users)
                if request.form["select"] == "del" and request.form["value"] != "" and session["token"] == PASSWORD:
                    from db.users import users
                    if request.form["value"] == "All":
                        users = {}
                    else:
                        users.pop(request.form["id"])
                    await save(file="users", content=users)
        return redirect(location=url_for(endpoint="admin"))
    except Exception:
        await logs(level=LEVELS[4], message=format_exc())
        return redirect(location=url_for(endpoint="admin"))


@APP.route(rule="/monitor", methods=["GET", "POST"])
async def monitor():
    try:
        monitor_str, monitor_rows = f"Процессор: {cpu_percent()} %\n\n", 8
        total = str(virtual_memory().total / 1024 / 1024 / 1024).split(".")
        available = str(virtual_memory().available / 1024 / 1024 / 1024).split(".")
        monitor_str += str(f"ОЗУ:\n"
                           f"    Всего: {total[0]}.{total[1][:2]} ГБ\n"
                           f"    Свободно: {available[0]}.{available[1][:2]} ГБ\n"
                           f"    Процент: {virtual_memory().percent} %\n\n")
        for disk in disk_partitions():
            monitor_str += str(f"Диск {disk.device}:\n"
                               f"    Всего: "
                               f"{int(disk_usage(disk.mountpoint).total / 1024 / 1024 / 1024)} ГБ\n"
                               f"    Использовано: "
                               f"{int(disk_usage(disk.mountpoint).used / 1024 / 1024 / 1024)} ГБ\n"
                               f"    Свободно: "
                               f"{int(disk_usage(disk.mountpoint).free / 1024 / 1024 / 1024)} ГБ\n"
                               f"    Процент: {disk_usage(disk.mountpoint).percent} %\n\n")
            monitor_rows += 6
        with open(file=f"www/html/monitor.html", mode="r", encoding="UTF-8") as monitor_html:
            return render_template_string(source=monitor_html.read(), monitor_str=monitor_str,
                                          monitor_rows=monitor_rows)
    except Exception:
        await logs(level=LEVELS[4], message=format_exc())
        return redirect(location=url_for(endpoint="monitor"))


if __name__ == "__main__":
    try:
        run(main=backup())
        serve(app=APP, port=80)
    except Exception:
        run(main=logs(level=LEVELS[4], message=format_exc()))
