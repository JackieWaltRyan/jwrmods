from asyncio import new_event_loop, run, run_coroutine_threadsafe
from datetime import datetime
from functools import partial
from hashlib import sha256
from os import makedirs, execl, listdir, remove
from os.path import exists
from shutil import move
from subprocess import run as s_run
from sys import executable
from threading import Thread, Timer
from traceback import format_exc

from discord_webhook import AsyncDiscordWebhook, DiscordEmbed
from flask import Flask, request, send_file, session, redirect, url_for, render_template_string
from psutil import cpu_percent, virtual_memory, disk_partitions, disk_usage
from pymongo import MongoClient
from pytz import timezone
from waitress import serve
from werkzeug.middleware.proxy_fix import ProxyFix

APP, DB, LEVELS = Flask(import_name=__name__), MongoClient()["jwrmods"], {"DEBUG": 0x0000FF,
                                                                          "INFO": 0x008000,
                                                                          "WARNING": 0xFFFF00,
                                                                          "ERROR": 0xFFA500,
                                                                          "CRITICAL": 0xFF0000}
APP.secret_key = DB["settings"].find_one(filter={"_id": "Настройки"})["Ключ"]
APP.wsgi_app = ProxyFix(app=APP.wsgi_app)  # type: ignore
TIME = str(datetime.now(tz=timezone(zone="Europe/Moscow")))[:-13].replace(" ", "_").replace("-", "_").replace(":", "_")


async def logs(level, message, file=None):
    try:
        db = DB["settings"].find_one(filter={"_id": "Логи"})
        if level == "DEBUG" and not db["Дебаг"]:
            return None
        print(f"{datetime.now(tz=timezone(zone='Europe/Moscow'))} {level}:\n{message}\n\n")
        if not exists(path="temp/logs"):
            makedirs(name="temp/logs")
        with open(file=f"temp/logs/{TIME}.log",
                  mode="a+",
                  encoding="UTF-8") as log_file:
            log_file.write(f"{datetime.now(tz=timezone(zone='Europe/Moscow'))} {level}:\n{message}\n\n")
        webhook = AsyncDiscordWebhook(username=db["Вебхук"]["Имя"],
                                      avatar_url=db["Вебхук"]["Аватар"],
                                      url=db["Вебхук"]["Ссылка"])
        if len(message) <= 4096:
            webhook.add_embed(embed=DiscordEmbed(title=level,
                                                 description=message,
                                                 color=LEVELS[level]))
        else:
            webhook.add_file(file=message.encode(encoding="UTF-8",
                                                 errors="ignore"),
                             filename=f"{level}.log")
        if file is not None:
            with open(file=f"temp/db/{file}",
                      mode="rb") as backup_file:
                webhook.add_file(file=backup_file.read(),
                                 filename=file)
        await webhook.execute()
    except Exception:
        await logs(level="CRITICAL",
                   message=format_exc())


async def backup():
    try:
        date = str(datetime.now(tz=timezone(zone="Europe/Moscow")))[:-13]
        time = date.replace(" ", "_").replace("-", "_").replace(":", "_")
        if not exists(path=f"temp/db/{time}"):
            makedirs(name=f"temp/db/{time}")
        for collection in DB.list_collections():
            file = []
            for item in DB[collection["name"]].find():
                file.append(item)
            with open(file=f"temp/db/{time}/{collection['name']}.py",
                      mode="w",
                      encoding="UTF-8") as db_file:
                db_file.write(f"{collection['name']} = {file}\n")
        result = s_run(args=f"bin\\zip\\x64\\7za.exe a -mx9 temp\\db\\jwrmods_{time}.zip temp\\db\\{time}",
                       shell=True,
                       capture_output=True,
                       text=True,
                       encoding="UTF-8",
                       errors="ignore")
        try:
            result.check_returncode()
        except Exception:
            raise Exception(result.stderr)
        await logs(level="INFO",
                   message="Бэкап БД создан успешно!",
                   file=f"jwrmods_{time}.zip")
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())


async def restart():
    try:
        try:
            execl(executable, executable, "jwrmods.py")
        except Exception:
            await logs(level="DEBUG",
                       message=format_exc())
            execl("python", "python", "jwrmods.py")
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())


async def autores():
    try:
        time = int(datetime.now(tz=timezone(zone="Europe/Moscow")).strftime("%H%M%S"))
        print(f"jwrmods: {time}")
        if time == 0 or time == 120000:
            await backup()
        Timer(interval=1,
              function=partial(run, main=autores())).start()
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())


async def copy(user, mod):
    try:
        mods = {"3467418": "money",
                "3468896": "maximum"}
        file = [x for x in listdir(path=f"temp/files/{mods[mod]}")][0]
        move(src=f"temp/files/{mods[mod]}/{file}",
             dst=f"temp/users/{user}/com.gameloft.android.ANMP.GloftPOHM_{mods[mod]}.apk")
        DB["users"].update_one(filter={"_id": int(user)},
                               update={"$set": {"Файл": int(file[:-4])}})
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())


async def data_admin(error=None):
    try:
        if "user" in session and "token" in session:
            db = DB["settings"].find_one(filter={"_id": "Администраторы"})
            if session["user"] in db and session["token"] == db[session["user"]]:
                mods_str = str(f"Денежный: {len(listdir(path='temp/files/money'))}\n"
                               f"Максимальный: {len(listdir(path='temp/files/maximum'))}\n")
                settings_str = f"Дебаг: {DB['settings'].find_one(filter={'_id': 'Логи'})['Дебаг']}\n"
                users_str, users_rows, users_cols = "", 1, 55
                for user in DB["users"].find(filter={}):
                    users_str += f"{user['_id']}:\n"
                    for item in user:
                        if item == "_id":
                            continue
                        users_str += f"    {item}: {user[item]}\n"
                        if len(f"    {item}: {user[item]}\n") > users_cols:
                            users_cols = len(f"    {item}: {user[item]}\n") + 5
                        users_rows += 1
                    users_rows += 1
                with open(file=f"www/html/admins/admin.html",
                          mode="r",
                          encoding="UTF-8") as admin_html:
                    return render_template_string(source=admin_html.read(),
                                                  mods_str=mods_str,
                                                  mods_cols=55,
                                                  mods_rows=3,
                                                  settings_str=settings_str,
                                                  settings_cols=55,
                                                  settings_rows=2,
                                                  users_str=users_str,
                                                  users_cols=users_cols,
                                                  users_rows=users_rows,
                                                  error=error)
        with open(file=f"www/html/admins/login.html",
                  mode="r",
                  encoding="UTF-8") as login_html:
            return render_template_string(source=login_html.read(),
                                          error=error)
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())
        return redirect(location=url_for(endpoint="url_admin"))


@APP.route(rule="/",
           methods=["GET", "POST"])
async def url_home():
    try:
        with open(file=f"www/html/services/index.html",
                  mode="r",
                  encoding="UTF-8") as index_html:
            return render_template_string(source=index_html.read(),
                                          time=str(datetime.now(tz=timezone(zone="Europe/Moscow")))[:-13])
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())


@APP.route(rule="/mods",
           methods=["GET", "POST"])
async def url_mods():
    try:
        if "friend" in request.args:
            session["friend"] = request.args["friend"]
            session.permanent = True
        if "friend" in request.args:
            session["friend"] = request.args["friend"]
            session.permanent = True
        if "friend" in request.args:
            session["friend"] = request.args["friend"]
            session.permanent = True
        with open(file=f"www/html/services/mods.html",
                  mode="r",
                  encoding="UTF-8") as mods_html:
            return render_template_string(source=mods_html.read())
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())


@APP.route(rule="/css/<file>",
           methods=["GET", "POST"])
async def url_css(file):
    try:
        return send_file(path_or_file=f"www/css/{file}")
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())


@APP.route(rule="/fonts/<file>",
           methods=["GET", "POST"])
async def url_fonts(file):
    try:
        return send_file(path_or_file=f"www/fonts/{file}")
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())


@APP.route(rule="/images/<path:file>",
           methods=["GET", "POST"])
async def url_images(file):
    try:
        return send_file(path_or_file=f"www/images/{file}")
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())


@APP.route(rule="/js/<file>",
           methods=["GET", "POST"])
async def url_js(file):
    try:
        return send_file(path_or_file=f"www/js/{file}")
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())


@APP.route(rule="/confirm",
           methods=["GET", "POST"])
async def url_confirm(user=None, mod=None, friend=None):
    try:
        if user is None:
            user = request.get_json(force=True,
                                    silent=True)["inv"]
        if mod is None:
            mod = request.get_json(force=True,
                                   silent=True)["id"]
        if friend is None:
            friend = request.get_json(force=True,
                                      silent=True)["friend"] if "friend" in request.get_json(force=True,
                                                                                             silent=True) else None
        makedirs(name=f"temp/users/{user}")
        document = {"_id": int(user),
                    "Лимит": 5,
                    "Установок": 0,
                    "Попыток": 0}
        document.update({"Друг": friend} if friend is not None else {})
        DB["users"].insert_one(document=document)
        loop = new_event_loop()
        Thread(target=loop.run_forever).start()
        run_coroutine_threadsafe(coro=copy(user=user,
                                           mod=mod),
                                 loop=loop)
        with open(file=f"www/html/responses/goods.html",
                  mode="r",
                  encoding="UTF-8") as goods_html:
            return {"id": mod,
                    "inv": user,
                    "goods": render_template_string(source=goods_html.read(),
                                                    user=user)}
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())
        with open(file=f"www/html/responses/error.html",
                  mode="r",
                  encoding="UTF-8") as error_html:
            return {"id": mod,
                    "inv": user,
                    "error": render_template_string(source=error_html.read(),
                                                    user=user,
                                                    time=datetime.now(tz=timezone(zone="Europe/Moscow")))}


@APP.route(rule="/start/<file>",
           methods=["GET", "POST"])
async def url_start(file):
    try:
        db = DB["users"].find_one(filter={"Файл": int(file)})
        if db["Установок"] < db["Лимит"]:
            DB["users"].update_one(filter={"_id": db["_id"]},
                                   update={"$inc": {"Установок": 1,
                                                    "Попыток": 1}})
            return "1125"
        else:
            DB["users"].update_one(filter={"_id": db["_id"]},
                                   update={"$inc": {"Попыток": 1}})
            if db["Попыток"] == 20:
                await logs(level="CRITICAL",
                           message=f"Пользователь {db['_id']} превысил лимит 20 попыток!")
            if db["Попыток"] == 100:
                await logs(level="CRITICAL",
                           message=f"Пользователь {db['_id']} превысил лимит 100 попыток!")
            return "1126"
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())
        return "1127"


@APP.route(rule="/users/<user>",
           methods=["GET", "POST"])
async def url_users(user):
    try:
        if "friend" in session:
            DB["users"].update_one(filter={"_id": int(user)},
                                   update={"$set": {"Друг": session["friend"]}})
        files = [x for x in listdir(path=f"temp/users/{user}") if x.endswith(".apk")]
        if len(files) > 0:
            with open(file=f"www/html/users/files.html",
                      mode="r",
                      encoding="UTF-8") as files_html:
                return render_template_string(source=files_html.read(),
                                              user=user,
                                              file=files[0])
        else:
            with open(file=f"www/html/users/wait.html",
                      mode="r",
                      encoding="UTF-8") as wait_html:
                return wait_html.read()
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())


@APP.route(rule="/files/<user>/<file>",
           methods=["GET", "POST"])
async def url_files(user, file):
    try:
        if file.startswith("com.gameloft.android.ANMP.GloftPOHM.apk"):
            return send_file(path_or_file="temp/files/com.gameloft.android.ANMP.GloftPOHM.apk",
                             as_attachment=True)
        if file.startswith("com.gameloft.android.ANMP.GloftPOHM_gapps.apk"):
            return send_file(path_or_file="temp/files/com.gameloft.android.ANMP.GloftPOHM_gapps.apk",
                             as_attachment=True)
        if file.startswith("com.gameloft.android.ANMP.GloftPOHM_farm.apk"):
            return send_file(path_or_file="temp/files/com.gameloft.android.ANMP.GloftPOHM_farm.apk",
                             as_attachment=True)
        return send_file(path_or_file=f"temp/users/{user}/{file}",
                         as_attachment=True)
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())


@APP.route(rule="/admin",
           methods=["GET", "POST"])
async def url_admin():
    try:
        if len(request.form) == 0:
            return await data_admin()
        else:
            db = DB["settings"].find_one(filter={"_id": "Администраторы"})
            if "login" in request.form and "password" in request.form:
                pass_hash = sha256(request.form["password"].encode(encoding="UTF-8",
                                                                   errors="ignore")).hexdigest()
                if request.form["login"] in db and pass_hash == db[request.form["login"]]:
                    session["user"] = request.form["login"]
                    session["token"] = db[request.form["login"]]
                    session.permanent = True
                else:
                    return await data_admin(error=True)
            if "debug" in request.form and "token" in session:
                if session["token"] == db[session["user"]]:
                    debug = DB["settings"].find_one(filter={"_id": "Логи"})["Дебаг"]
                    DB["settings"].update_one(filter={"_id": "Логи"},
                                              update={"$set": {"Дебаг": not debug}})
            if "exit" in request.form and "token" in session:
                if session["token"] == db[session["user"]]:
                    session.clear()
            if "res" in request.form and "token" in session:
                if session["token"] == db[session["user"]]:
                    await restart()
            if "select" in request.form and "token" in session:
                if request.form["select"] == "add" and session["token"] == db[session["user"]]:
                    if request.form["id"] != "" and request.form["value"] != "":
                        res = await url_confirm(user=request.form["id"],
                                                mod=request.form["value"],
                                                friend="jwr")
                        return res["goods"] if "goods" in res else res["error"]
                    else:
                        return await data_admin(error=1)
                if request.form["select"] == "change" and session["token"] == db[session["user"]]:
                    if request.form["id"] != "" and request.form["value"] != "":
                        DB["users"].update_one(filter={"_id": int(request.form["id"])},
                                               update={"$set": {"Лимит": int(request.form["value"])}})
                    else:
                        return await data_admin(error=2)
                if request.form["select"] == "del" and session["token"] == db[session["user"]]:
                    if request.form["id"] != "":
                        if request.form["id"].lower() == "all":
                            for user in DB["users"].find(filter={}):
                                for file in listdir(path=f"temp/users/{user['_id']}"):
                                    remove(path=f"temp/users/{user['_id']}/{file}")
                                DB["users"].delete_one(filter={"_id": user["_id"]})
                        else:
                            for file in listdir(path=f"temp/users/{request.form['id']}"):
                                remove(path=f"temp/users/{request.form['id']}/{file}")
                            DB["users"].delete_one(filter={"_id": int(request.form["id"])})
                    else:
                        return await data_admin(error=3)
        return redirect(location=url_for(endpoint="url_admin"))
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())
        return redirect(location=url_for(endpoint="url_admin"))


@APP.route(rule="/admin/monitor",
           methods=["GET", "POST"])
async def url_monitor():
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
        with open(file=f"www/html/admins/monitor.html",
                  mode="r",
                  encoding="UTF-8") as monitor_html:
            return render_template_string(source=monitor_html.read(),
                                          monitor_str=monitor_str,
                                          monitor_rows=monitor_rows,
                                          clear=True if "clear" in request.args else False)
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())
        return redirect(location=url_for(endpoint="url_monitor"))


@APP.errorhandler(code_or_exception=404)
async def error_404(error):
    try:
        print(error)
        with open(file=f"www/html/services/error.html",
                  mode="r",
                  encoding="UTF-8") as error_html:
            return error_html.read()
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())


@APP.errorhandler(code_or_exception=500)
async def error_500(error):
    try:
        print(error)
        with open(file=f"www/html/services/error.html",
                  mode="r",
                  encoding="UTF-8") as error_html:
            return error_html.read()
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())


if __name__ == "__main__":
    try:
        run(main=autores())
        serve(app=APP,
              port=80,
              threads=16)
    except Exception:
        run(main=logs(level="ERROR",
                      message=format_exc()))
