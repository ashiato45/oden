from flask import Flask, make_response, request, abort
import pickle
import threading
import requests
import datetime
import hashlib
import time
import sys
import logging


# ------ User write below ------
hosts = """
999.999.999.999
"""
name = "sample"


def calc(task):
    return "The result"


def make_tasks():
    tasks = []
    return tasks


def handle_finish_machine(num, uri):
    pass


def handle_finish_tasks():
    pass


def show_status():
    return "I'm working well!"


# ------ User write above ------

def get_time_hash():
    return datetime.datetime.now().strftime("%Y%m%d%H%M%S")

# Prepare Flask
app = Flask(__name__)

# State of worker.  It can be ("idle",), ("working", task), ("done", task, res) or
lock_state = threading.Lock()
state_worker = ("idle",)


# Prepare logger
logFormatter = logging.Formatter("%(asctime)s [%(who)s] [%(levelname)s]  %(message)s")
rootLogger = logging.getLogger()
rootLogger.setLevel(logging.INFO)

fileHandler = logging.FileHandler("{0}.log".format(get_time_hash()))
fileHandler.setFormatter(logFormatter)
rootLogger.addHandler(fileHandler)

consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
rootLogger.addHandler(consoleHandler)


# Make pages
@app.route("/", methods=["GET"])
def respond_home():
    return show_status()

def invoke_calc(task):
    global state_worker
    try:
        res = calc(task)
        lock_state.acquire()
        state_worker = ("done", task, res)
        lock_state.release()
    except Exception as e:
        import traceback, io
        with io.StringIO() as f:
            traceback.print_exc(file=f)
            rootLogger.error(f.getvalue(), {"who": "calc"})
            lock_state.acquire()
            state_worker = ("error", task, f.getvalue())
            lock_state.release()


@app.route("/calc", methods=["POST"])
def respond_calc():
    global state_worker
    rootLogger.info("Got calculation request {0}".format(request.data), {"who": "respond"})
    task = pickle.loads(request.data)
    try:
        lock_state.acquire()
        if state_worker[0] == "idle":
            state_worker = ("working", task)
            threading.Thread(target=invoke_calc, args=(task,)).start()
            rootLogger.info("Accepting task {0}".format(task), {"who": "respond"})
        else:
            lock_state.release()
            rootLogger.info("Rejecting the request because the state is {0}".format(state_worker[0]), {"who": "respond"})
            abort(503, {})
        lock_state.release()
    except Exception as e:
        import traceback, io
        with io.StringIO() as f:
            traceback.print_exc(file=f)
            rootLogger.error(f.getvalue(), {"who": "respond"})
            state_worker = ("error", task, f.getvalue())
    return "Accepted your task"


@app.route("/retrieve", methods=["POST"])
def respond_retrieve():
    global state_worker
    response = make_response()
    rootLogger.info("Got retrieval request {0}".format(request.data), {"who": "retrieve"})
    task_request = pickle.loads(request.data)
    task_request_hash = hashlib.md5(pickle.dumps(task_request)).hexdigest()
    lock_state.acquire()
    if state_worker[0] == "idle":
        rootLogger.error("The state was idle".format(), {"who": "retrieve"})
        abort(404, {})
    elif state_worker[0] == "working":
        rootLogger.info("The state was working".format(), {"who": "retrieve"})
        abort(503, {})  # Service Unavailable
    elif state_worker[0] == "done":
        rootLogger.info("The state was done".format(), {"who": "retrieve"})
        lock_state.acquire()
        _, task, res = state_worker
        task_hash = hashlib.md5(pickle.dumps(task)).hexdigest()
        if task_hash != task_request_hash:
            rootLogger.error("The task we have done and the task of the request are different".format(),
                             {"who": "retrieve"})
            abort(404, {})
        res = pickle.dumps({"task": task, "result": res})
        response.data = res
        response.mimetype = "application/octet-stream"
        state_worker = ("idle",)
        lock_state.release()
        return response
    elif state_worker[0] == "error":
        rootLogger.info("The state was error".format(), {"who": "retrieve"})
        lock_state.acquire()
        _, task, error = state_worker
        res = pickle.dumps({"task": task, "error": error})
        response.data = res
        response.mimetype = "application/octet-stream"
        state_worker = ("idle",)
        lock_state.release()
        return response
    rootLogger.info("Unexpected state {0}".format(state_worker), {"who": "retrieve"})
    abort(404, {}) # Not Found


def caller(server, tasks, saved, failed, lock):
    uri_server = server[0]
    name_server = server[1]
    rootLogger.info("Starting {0}@{1}".format(name_server, uri_server), {"who": name_server})
    while True:
        lock.acquire()
        if tasks == []:
            break
        task = tasks.pop()
        rootLogger.info("Popped {0}".format(task), {"who": name_server})
        lock.release()
        try:
            filename = "{0}_{1}.pickle".format(name_server, get_time_hash())
            data = pickle.dumps(task)
            res = requests.post(uri_server + "calc", data=data, timeout=None)
            if res.status_code == 200:
                rootLogger.info("Request {0} is accepted".format(task), {"who": name_server})
                while True:
                    time.sleep(60)
                    res2 = requests.post(uri_server + "retrieve", data=data, timeout=None)
                    if res2.status_code == 200:
                        res2.raw.decode_content = True
                        res = pickle.loads(res2.content)
                        if "result" in res:
                            with open(filename, "wb") as f:
                                rootLogger.info("Saving the result for {0} as {1}".format(task, filename),
                                                {"who": name_server})
                                f.write(res2.content)
                        elif "error" in res:
                            rootLogger.info("Error occurred in the remote machine: {0}".format(res["error"]),
                                            {"who": name_server})
                            raise Exception("Error occurred in the remote machine")
                        else:
                            raise Exception("Invalid result is given")

                    elif res2.status_code == 503:
                        pass  # the remote is working
                    else:
                        raise Exception("The remote machine is in idle.  The task was gone away...")
                lock.acquire()
                saved.append(filename)
                lock.release()
            else:
                lock.acquire()
                failed.append(task)
                rootLogger.info("Retrieving {0} failed with {1}".format(task, res.status_code), {"who": name_server})
                lock.release()
        except Exception as e:
            import traceback, io
            with io.StringIO() as f:
                traceback.print_exc(file=f)
                rootLogger.error("Request {0} failed with the following error: {1}".format(task, f.getvalue()))

    lock.release()
    rootLogger.info("Closing".format(), {"who": name_server})


if __name__ == "__main__":
    print(sys.argv[1])
    if len(sys.argv) < 2:
        rootLogger.fatal("No modes specified", {"who": "error"})
    else:
        if sys.argv[1] in ["manager", "test", "resume"]:
            if sys.argv[1] == "resume":
                rootLogger.info("Starting resume mode".format(), {"who": "resume"})
                with open("failed.pickle", "rb") as f:
                    tasks = pickle.load(f)
                rootLogger.info("Loaded {0} tasks".format(len(tasks)), {"who": "resume"})
                sys.argv[1] = "manager"
            else:
                tasks = make_tasks()
            if sys.argv[1] == "manager":
                rootLogger.info("Starting manager mode", {"who": "manager"})
                servers = [x.strip() for x in hosts.split("\n") if x.strip() != ""]
                servers = ["http://{0}:8080/".format(x) for x in servers]
                servers = [(server, name + str(i)) for i, server in enumerate(servers)]
                rootLogger.info("Servers: " + str(servers), {"who": "manager"})

                lock = threading.Lock()
                num_tasks = len(tasks)
                saved = []
                failed = []
                rootLogger.info("We have {0} tasks.".format(num_tasks), {"who": "manager"})
                for server in servers:
                    threading.Thread(target=caller, args=(server, tasks, saved, failed, lock)).start()
                while True:
                    if len(saved) + len(failed) == num_tasks:
                        rootLogger.info("Succeeded {0} tasks.".format(len(saved)), {"who": "manager"})
                        rootLogger.info("Failed {0} tasks.".format(len(failed)), {"who": "manager"})
                        with open("failed.pickle", "wb") as f:
                            pickle.dump(failed, f)
                        break
            elif sys.argv[1] == "test":
                rootLogger.info("Starting test mode", {"who": "test"})
                for i in tasks:
                    rootLogger.info("Starting task {0}".format(i), {"who": "manager"})
                    calc(i, "test")
        elif sys.argv[1] == "worker":
            app.run(host='0.0.0.0', port=8080)
        else:
            rootLogger.fatal("Invalid argument {0}".format(sys.argv[1]), {"who": "error"})
