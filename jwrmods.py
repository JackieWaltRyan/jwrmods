from asyncio import new_event_loop, run, sleep, run_coroutine_threadsafe
from datetime import datetime
from discord_webhook import DiscordWebhook, DiscordEmbed
from flask import Flask, request, send_file, render_template
from hashlib import sha256
from os import makedirs, rename, system
from os.path import isfile, exists
from pytz import timezone
from shutil import move
from subprocess import run as srun
from threading import Thread, Timer
from traceback import format_exc
from waitress import serve

APP, BAT = Flask(import_name=__name__), {"3467418": {"key": False, "queue": 0}, "3468896": {"key": False, "queue": 0}}
LEVELS, TRIGGER = {1: {"name": "DEBUG", "color": 0x0000FF}, 2: {"name": "INFO", "color": 0x008000},
                   3: {"name": "WARNING", "color": 0xFFFF00}, 4: {"name": "ERROR", "color": 0xFFA500},
                   5: {"name": "CRITICAL", "color": 0xFF0000}}, {"Save": False, "Backup": False}
TIME = str(datetime.now(tz=timezone(zone="Europe/Moscow")))[:-7].replace(" ", "_").replace("-", "_").replace(":", "_")


async def logs(level, message, file=None):
    try:
        if level == LEVELS[1]:
            from db.settings import settings
            if not settings["Дебаг"]:
                return None
        print(f"{datetime.now(tz=timezone(zone='Europe/Moscow'))} {level['name']}\n{message}")
        if not exists(path="logs"):
            makedirs(name="logs")
        with open(file=f"logs/{str(TIME)[:-6]}.log", mode="a", encoding="UTF-8") as log_file:
            log_file.write(f"{datetime.now(tz=timezone(zone='Europe/Moscow'))} {level['name']} {message}\n")
        webhook = DiscordWebhook(username="JWR Mods",
                                 avatar_url="https://cdn.discordapp.com/attachments/1021085537802649661/"
                                            "1021392623044415597/JWR_Mods.png", url="")
        webhook.add_embed(embed=DiscordEmbed(title=level["name"], description=str(message), color=level["color"]))
        if file is not None:
            with open(file=f"backups/{file}", mode="rb") as backup_file:
                webhook.add_file(file=backup_file.read(), filename=file)
        webhook.execute()
    except Exception:
        print(format_exc())


async def save(file, content):
    try:
        while True:
            if not TRIGGER["Save"]:
                TRIGGER["Save"] = True
                if not exists(path="db"):
                    makedirs(name="db")
                if file in ["settings"]:
                    with open(file=f"db/{file}.py", mode="w", encoding="UTF-8") as open_file:
                        open_file.write(f"import datetime\n\n{file} = {content}\n")
                else:
                    with open(file=f"db/{file}.py", mode="w", encoding="UTF-8") as open_file:
                        open_file.write(f"{file} = {content}\n")
                TRIGGER["Save"] = False
                break
            else:
                print("Идет сохранение...")
                await sleep(delay=1)
    except Exception:
        TRIGGER["Save"] = False
        await logs(level=LEVELS[4], message=format_exc())


async def backup():
    try:
        time = int(datetime.now(tz=timezone(zone="Europe/Moscow")).strftime("%H%M%S"))
        print(f"jwrmods: {time}")
        from db.settings import settings
        if (datetime.utcnow() - settings["Дата обновления"]).days >= 1:
            if not TRIGGER["Backup"]:
                TRIGGER["Backup"] = True
                if not exists(path="backups"):
                    makedirs(name="backups")
                system(command=f"zip\\x64\\7za.exe a -mx9 backups\\jwrmods_{TIME[:-6]}.zip db")
                settings["Дата обновления"] = datetime.utcnow()
                await save(file="settings", content=settings)
                await logs(level=LEVELS[2], message=f"Бэкап БД создан успешно!", file=f"jwrmods_{TIME[:-6]}.zip")
                TRIGGER["Backup"] = False
        Timer(interval=1, function=lambda: run(main=backup())).start()
    except Exception:
        TRIGGER["Backup"] = False
        await logs(level=LEVELS[4], message=format_exc())


async def bat(user, mod):
    try:
        module, apks = None, {"v7a": "armeabi-v7a", "v8a": "arm64-v8a", "x86": "x86", "64": "x86_64"}
        if mod == [x for x in BAT][0]:
            module = "money"
        if mod == [x for x in BAT][1]:
            module = "maximum"
        while True:
            if not BAT[mod]["key"]:
                BAT[mod]["key"] = True
                BAT[mod]["queue"] += 1
                for apk in apks:
                    with open(file=f"bat/{module}/_INPUT_APK/{apk}/assets/ccwc.txt", mode="w", encoding="UTF-8") as f:
                        f.write(user)
                srun(args=f"bat\\{module}\\bin\\BATCHAPKTOOL.bat launcher 11")
                with open(file=f"bat/{module}/log_recompile.txt", mode="r", encoding="UTF-8") as log:
                    await logs(level=LEVELS[2], message=log.read())
                for apk in apks:
                    if isfile(path=f"bat/{module}/_OUT_APK/{apk}.apk"):
                        rename(f"bat/{module}/_OUT_APK/{apk}.apk",
                               f"bat/{module}/_OUT_APK/com.gameloft.android.ANMP.GloftPOHM_{apks[apk]}_{module}.apk")
                        move(f"bat/{module}/_OUT_APK/com.gameloft.android.ANMP.GloftPOHM_{apks[apk]}_{module}.apk",
                             f"files/{user}/com.gameloft.android.ANMP.GloftPOHM_{apks[apk]}_{module}.apk")
                    else:
                        raise Exception(f"File \"bat/{module}/_OUT_APK/{apk}.apk\" not found.\n"
                                        f"User: {user}, Time: {datetime.now(tz=timezone(zone='Europe/Moscow'))}")
                BAT[mod]["key"] = False
                BAT[mod]["queue"] -= 1
                with open(file=f"files/{user}/index.html", mode="w", encoding="UTF-8") as html:
                    html.write(render_template(template_name_or_list="files.html", user=user, module=module))
                break
            else:
                await sleep(delay=5)
    except Exception:
        BAT[mod]["key"] = False
        BAT[mod]["queue"] -= 1
        with open(file=f"files/{user}/index.html", mode="w", encoding="UTF-8") as error:
            error.write(render_template(template_name_or_list="error.html", user=user,
                                        time=datetime.now(tz=timezone(zone="Europe/Moscow"))))
        await logs(level=LEVELS[4], message=format_exc())


@APP.route(rule="/", methods=["GET", "POST"])
async def home():
    try:
        return render_template(template_name_or_list="index.html",
                               time=str(datetime.now(tz=timezone(zone="Europe/Moscow")))[:-13])
    except Exception:
        await logs(level=LEVELS[4], message=format_exc())


@APP.route(rule="/templates/<file>", methods=["GET", "POST"])
@APP.route(rule="/templates/fonts/<file>", methods=["GET", "POST"])
async def templates(file):
    try:
        if file == "style.css":
            return send_file(path_or_file="templates/style.css")
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
async def confirm():
    try:
        from db.users import users
        users.update({request.get_json(force=True, silent=True)["id"]: {"Все": 20, "v7a": 0, "v8a": 0, "x86": 0,
                                                                        "x64": 0}})
        await save(file="users", content=users)
        makedirs(name=f"files/{request.get_json(force=True, silent=True)['id']}")
        time = BAT[request.get_json(force=True, silent=True)["inv"]]["queue"] * 5
        if time == 0:
            time = 5
        with open(file=f"files/{request.get_json(force=True, silent=True)['id']}/index.html", mode="w",
                  encoding="UTF-8") as html:
            html.write(render_template(template_name_or_list="wait.html",
                                       queue=BAT[request.get_json(force=True, silent=True)["inv"]]["queue"], time=time))
        new_loop = new_event_loop()
        Thread(target=new_loop.run_forever).start()
        run_coroutine_threadsafe(coro=bat(user=request.get_json(force=True, silent=True)["id"],
                                          mod=request.get_json(force=True, silent=True)["inv"]), loop=new_loop)
        return {"id": request.get_json(force=True, silent=True)["id"],
                "inv": request.get_json(force=True, silent=True)["inv"],
                "goods": render_template(template_name_or_list="response.html",
                                         user=request.get_json(force=True, silent=True)["id"])}
    except Exception:
        await logs(level=LEVELS[4], message=format_exc())
        return {"id": request.get_json(force=True, silent=True)["id"],
                "inv": request.get_json(force=True, silent=True)["inv"],
                "error": render_template(template_name_or_list="error.html",
                                         user=request.get_json(force=True, silent=True)["id"],
                                         time=datetime.now(tz=timezone(zone="Europe/Moscow")))}


@APP.route(rule="/start/<user>/<architecture>/<time>", methods=["GET", "POST"])
async def start(user, architecture, time):
    try:
        from db.users import users
        if users[user][architecture] < int(users[user]["Все"] / 4):
            users[user][architecture] += 1
            await save(file="users", content=users)
            return "1125"
        else:
            return "1126"
    except Exception:
        await logs(level=LEVELS[4], message=format_exc())
        return "1127"


@APP.route(rule="/admin/<password>/<trigger>/<user>/<value>", methods=["GET", "POST"])
async def admin(password, trigger, user, value):
    try:
        password_hash = "36aff10f2915d0d5e95b1c63bb9be2892e9ea3fa8685472a1c7f4bd895e4a06e"
        if sha256(password.encode(encoding="UTF-8")).hexdigest() == password_hash:
            if trigger == "add":
                await confirm(user=user, mod=value)
            if trigger == "change":
                from db.users import users
                old = users[user]["Все"]
                users[user]["Все"] = int(value)
                await save(file="users", content=users)
                return f"Status: OK<br><br>User: {user}<br>Old value: {old}<br>New value: {value}"
            if trigger == "debug":
                from db.settings import settings
                if value == "on":
                    settings["Дебаг"] = True
                    await save(file="settings", content=settings)
                if value == "off":
                    settings["Дебаг"] = False
                    await save(file="settings", content=settings)
                return f"Status: OK<br><br>Debug: {value}"
        else:
            return f"Status: Error<br><br>Неверный пароль!"
    except Exception:
        await logs(level=LEVELS[4], message=format_exc())
        return format_exc()


if __name__ == "__main__":
    try:
        run(main=backup())
        serve(app=APP, port=80)
    except Exception:
        run(main=logs(level=LEVELS[4], message=format_exc()))
