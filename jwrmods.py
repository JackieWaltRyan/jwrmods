from asyncio import new_event_loop, run, run_coroutine_threadsafe, sleep
from datetime import datetime
from functools import partial
from hashlib import sha256
from json import loads, dump
from os import makedirs, execl, listdir, remove, rmdir
from os.path import exists
from shutil import move
from sys import executable
from threading import Thread, Timer
from traceback import format_exc

from discord_webhook import AsyncDiscordWebhook, DiscordEmbed
from flask import Flask, request, send_file, render_template_string, abort, make_response
from pytz import timezone
from waitress import serve
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

APP, LEVELS = Flask(import_name=__name__), {"DEBUG": 0x0000FF,
                                            "INFO": 0x008000,
                                            "WARNING": 0xFFFF00,
                                            "ERROR": 0xFFA500,
                                            "CRITICAL": 0xFF0000}
APP.wsgi_app = ProxyFix(app=APP.wsgi_app)
TIME = str(datetime.now(tz=timezone(zone="Europe/Moscow")))[:-13].replace(" ", "_").replace("-", "_").replace(":", "_")
ADMINS = {}
TOKENS = [sha256((x + ADMINS[x]).encode(encoding="UTF-8",
                                        errors="ignore")).hexdigest() for x in ADMINS]


async def logs(level, message, file=None):
    try:
        print(f"{datetime.now(tz=timezone(zone='Europe/Moscow'))} {level}:\n{message}\n\n")

        if not exists(path="temp/logs"):
            makedirs(name="temp/logs")

        with open(file=f"temp/logs/{TIME}.log",
                  mode="a+",
                  encoding="UTF-8") as log_file:
            log_file.write(f"{datetime.now(tz=timezone(zone='Europe/Moscow'))} {level}:\n{message}\n\n")

        webhook = AsyncDiscordWebhook(username="JWR Mods",
                                      avatar_url="https://cdn.discordapp.com/attachments/1021085537802649661/"
                                                 "1021392623044415597/JWR_Mods.png",
                                      url="")

        if len(message) <= 4096:
            webhook.add_embed(embed=DiscordEmbed(title=level,
                                                 description=message,
                                                 color=LEVELS[level]))
        else:
            webhook.add_file(file=message.encode(encoding="UTF-8",
                                                 errors="ignore"),
                             filename=f"{level}.log")

        if file is not None:
            with open(file=file,
                      mode="rb") as backup_file:
                webhook.add_file(file=backup_file.read(),
                                 filename=file)

        await webhook.execute()
    except Exception:
        await logs(level="CRITICAL",
                   message=format_exc())


async def backup():
    try:
        await logs(level="INFO",
                   message="Бэкап БД создан успешно!",
                   file="db/users.json")
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())


async def restart():
    try:
        execl(executable, "python", "jwrmods.py")
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
        await sleep(delay=1)

        mods = {"3467418": "money",
                "3468896": "maximum"}

        file = [x for x in listdir(path=f"temp/files/{mods[mod]}")][0]

        move(src=f"temp/files/{mods[mod]}/{file}",
             dst=f"temp/users/{user}/com.gameloft.android.ANMP.GloftPOHM_{mods[mod]}.apk")

        with open(file="db/users.json",
                  mode="r",
                  encoding="UTF-8") as users_json:
            db = loads(s=users_json.read())

            db[user].update({"Файл": file[:-4]})

            with open(file="db/users.json",
                      mode="w",
                      encoding="UTF-8") as users_json_2:
                dump(obj=db,
                     fp=users_json_2,
                     indent=4,
                     ensure_ascii=False)
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())


@APP.route(rule="/")
async def url_home():
    try:
        if request.method == "GET":
            with open(file="www/html/services/index.html",
                      mode="r",
                      encoding="UTF-8") as index_html:
                return render_template_string(source=index_html.read())
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())
        return abort(code=404)


@APP.route(rule="/css/<path:file>")
async def url_css(file):
    try:
        if request.method == "GET":
            return send_file(path_or_file=f"www/css/{file}")
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())
        return abort(code=404)


@APP.route(rule="/fonts/<path:file>")
async def url_fonts(file):
    try:
        if request.method == "GET":
            return send_file(path_or_file=f"www/fonts/{file}")
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())
        return abort(code=404)


@APP.route(rule="/images/<path:file>")
async def url_images(file):
    try:
        if request.method == "GET":
            return send_file(path_or_file=f"www/images/{file}")
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())
        return abort(code=404)


@APP.route(rule="/js/<path:file>")
async def url_js(file):
    try:
        if request.method == "GET":
            return send_file(path_or_file=f"www/js/{file}")
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())
        return abort(code=404)


@APP.route(rule="/users/<user>")
async def url_users(user):
    try:
        if request.method == "GET":
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
        return abort(code=404)


@APP.route(rule="/files/<user>/<file>")
async def url_files(user, file):
    try:
        if request.method == "GET":
            return send_file(path_or_file=f"temp/users/{user}/{file}",
                             as_attachment=True)
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())
        return abort(code=404)


@APP.route(rule="/admin")
async def url_admin():
    try:
        if request.method == "GET":
            if "token" in request.args:
                token = request.args["token"]
            else:
                token = request.cookies.get("mods_token")

            if token in TOKENS:
                with open(file=f"www/html/admins/admin.html",
                          mode="r",
                          encoding="UTF-8") as admin_html:
                    return render_template_string(source=admin_html.read())
            else:
                with open(file=f"www/html/admins/login.html",
                          mode="r",
                          encoding="UTF-8") as login_html:
                    return render_template_string(source=login_html.read())
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())
        return abort(code=500)


@APP.route(rule="/api/time")
async def url_api_time():
    try:
        if request.method == "GET":
            return str(datetime.now(tz=timezone(zone="Europe/Moscow")))[:-13]
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())
        return abort(code=500)


@APP.route(rule="/api/pay",
           methods=["POST"])
async def url_api_pay(user=None, mod=None):
    try:
        if request.method == "POST":
            if user is None:
                user = request.get_json(force=True,
                                        silent=True)["inv"]
            if mod is None:
                mod = request.get_json(force=True,
                                       silent=True)["id"]

            mods = {"3467418": "Денежный (3467418)",
                    "3468896": "Максимальный (3468896)"}

            makedirs(name=f"temp/users/{user}")

            with open(file="db/users.json",
                      mode="r",
                      encoding="UTF-8") as users_json:
                db = loads(s=users_json.read())

                db.update({user: {"Мод": mods[mod],
                                  "Лимит": "5",
                                  "Установок": "0",
                                  "Попыток": "0"}})

                with open(file="db/users.json",
                          mode="w",
                          encoding="UTF-8") as users_json_2:
                    dump(obj=db,
                         fp=users_json_2,
                         indent=4,
                         ensure_ascii=False)

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


@APP.route(rule="/api/start")
async def url_api_start():
    try:
        if request.method == "GET":
            file = request.args["file"]

            with open(file="db/users.json",
                      mode="r",
                      encoding="UTF-8") as users_json:
                db = loads(s=users_json.read())

                for user in db:
                    if db[user]["Файл"] == file:
                        if int(db[user]["Установок"]) < int(db[user]["Лимит"]):
                            db[user]["Установок"] = str(int(db[user]["Установок"]) + 1)

                            with open(file="db/users.json",
                                      mode="w",
                                      encoding="UTF-8") as users_json_2:
                                dump(obj=db,
                                     fp=users_json_2,
                                     indent=4,
                                     ensure_ascii=False)
                            return "1125"
                        else:
                            db[user]["Попыток"] = str(int(db[user]["Попыток"]) + 1)

                            with open(file="db/users.json",
                                      mode="w",
                                      encoding="UTF-8") as users_json_2:
                                dump(obj=db,
                                     fp=users_json_2,
                                     indent=4,
                                     ensure_ascii=False)

                            if int(db[user]["Попыток"]) == 20:
                                await logs(level="CRITICAL",
                                           message=f"Пользователь {user} превысил лимит 20 попыток!")

                            if int(db[user]["Попыток"]) == 100:
                                await logs(level="CRITICAL",
                                           message=f"Пользователь {user} превысил лимит 100 попыток!")

                            return "1126"
                return "1127"
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())
        return "1127"


@APP.route(rule="/api/admin/auth")
async def url_api_admin_auth():
    try:
        if request.method == "GET":
            try:
                password = sha256(request.args["password"].encode(encoding="UTF-8",
                                                                  errors="ignore")).hexdigest()
                token = sha256((request.args["login"] + password).encode(encoding="UTF-8",
                                                                         errors="ignore")).hexdigest()
            except Exception:
                raise Exception

            if token in TOKENS:
                response = make_response({"user": request.args["login"],
                                          "token": token})
                response.set_cookie("mods_token", token)

                return response
            else:
                raise HTTPException
    except HTTPException:
        return abort(code=401)
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())
        return abort(code=400)


@APP.route(rule="/api/admin/user")
async def url_api_admin_user():
    try:
        if request.method == "GET":
            if "token" in request.args:
                token = request.args["token"]
            else:
                token = request.cookies.get("mods_token")

            if token is None:
                raise HTTPException

            try:
                for admin in ADMINS:
                    if token == sha256((admin + ADMINS[admin]).encode(encoding="UTF-8",
                                                                      errors="ignore")).hexdigest():
                        return {"user": admin,
                                "token": token}
                raise Exception
            except Exception:
                raise Exception
    except HTTPException:
        return abort(code=401)
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())
        return abort(code=404)


@APP.route(rule="/api/admin/restart")
async def url_api_admin_restart():
    try:
        if request.method == "GET":
            if "token" in request.args:
                token = request.args["token"]
            else:
                token = request.cookies.get("mods_token")

            if token is None or token not in TOKENS:
                raise HTTPException

            try:
                await restart()

                return "1125"
            except Exception:
                raise Exception
    except HTTPException:
        return abort(code=401)
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())
        return abort(code=500)


@APP.route(rule="/api/admin/users")
async def url_api_admin_users():
    try:
        if request.method == "GET":
            if "token" in request.args:
                token = request.args["token"]
            else:
                token = request.cookies.get("mods_token")

            if token is None or token not in TOKENS:
                raise HTTPException

            try:
                with open(file="db/users.json",
                          mode="r",
                          encoding="UTF-8") as users_json:
                    db = loads(s=users_json.read())

                    return db
            except Exception:
                raise Exception
    except HTTPException:
        return abort(code=401)
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())
        return abort(code=500)


@APP.route(rule="/api/admin/count")
async def url_api_admin_count():
    try:
        if request.method == "GET":
            if "token" in request.args:
                token = request.args["token"]
            else:
                token = request.cookies.get("mods_token")

            if token is None or token not in TOKENS:
                raise HTTPException

            try:
                return {"money": len(listdir(path="temp/files/money")),
                        "maximum": len(listdir(path="temp/files/maximum"))}
            except Exception:
                raise Exception
    except HTTPException:
        return abort(code=401)
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())
        return abort(code=500)


@APP.route(rule="/api/admin/add")
async def url_api_admin_add():
    try:
        if request.method == "GET":
            if "token" in request.args:
                token = request.args["token"]
            else:
                token = request.cookies.get("mods_token")

            if token is None or token not in TOKENS:
                raise HTTPException

            try:
                responce = await url_api_pay(user=request.args["user"],
                                             mod=request.args["mod"])

                if "goods" in responce:
                    return responce["goods"]
                else:
                    raise Exception
            except Exception:
                raise Exception
    except HTTPException:
        return abort(code=401)
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())
        return abort(code=400)


@APP.route(rule="/api/admin/change")
async def url_api_admin_change():
    try:
        if request.method == "GET":
            if "token" in request.args:
                token = request.args["token"]
            else:
                token = request.cookies.get("mods_token")

            if token is None or token not in TOKENS:
                raise HTTPException

            try:
                with open(file="db/users.json",
                          mode="r",
                          encoding="UTF-8") as users_json:
                    db = loads(s=users_json.read())

                    db[request.args["user"]]["Лимит"] = request.args["value"]

                    with open(file="db/users.json",
                              mode="w",
                              encoding="UTF-8") as users_json_2:
                        dump(obj=db,
                             fp=users_json_2,
                             indent=4,
                             ensure_ascii=False)
                return "1125"
            except Exception:
                raise Exception
    except HTTPException:
        return abort(code=401)
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())
        return abort(code=400)


@APP.route(rule="/api/admin/del")
async def url_api_admin_del():
    try:
        if request.method == "GET":
            if "token" in request.args:
                token = request.args["token"]
            else:
                token = request.cookies.get("mods_token")

            if token is None or token not in TOKENS:
                raise HTTPException

            try:
                for file in listdir(path=f"temp/users/{request.args['user']}"):
                    remove(path=f"temp/users/{request.args['user']}/{file}")

                rmdir(path=f"temp/users/{request.args['user']}")

                with open(file="db/users.json",
                          mode="r",
                          encoding="UTF-8") as users_json:
                    db = loads(s=users_json.read())

                    db.pop(request.args["user"])

                    with open(file="db/users.json",
                              mode="w",
                              encoding="UTF-8") as users_json_2:
                        dump(obj=db,
                             fp=users_json_2,
                             indent=4,
                             ensure_ascii=False)
                return "1125"
            except Exception:
                raise Exception
    except HTTPException:
        return abort(code=401)
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())
        return abort(code=400)


@APP.errorhandler(code_or_exception=HTTPException)
async def error_handler(error):
    try:
        print(error)

        with open(file=f"www/html/services/error.html",
                  mode="r",
                  encoding="UTF-8") as error_html:
            return render_template_string(source=error_html.read(),
                                          name=error.name,
                                          code=error.code), error.code
    except Exception:
        await logs(level="ERROR",
                   message=format_exc())


if __name__ == "__main__":
    try:
        run(main=autores())

        serve(app=APP,
              port=1125,
              threads=16)
    except Exception:
        run(main=logs(level="ERROR",
                      message=format_exc()))
