# oden
Easy distributed computation (with no communication) just by one Python file

## Abstract
![abstract](img/abst.gif)

## Features
- Easy to write tasks: All (picklable) Python objects can be used as tasks.  You don't have to learn new DSLs to write tasks.
- Easy to setup (?): Add oden.py in your project, fill in the placeholder in oden.py, copy the project in remote machines, and run oden.py in worker mode.
- Easy network setting: Opening 8080 of remote machines (only) to your PC is enough.  No need of tunneling or something.
- Easy to analyze the results: The results are saved in pickle files.  No need to write serializers nor parsers of the results.
- Easy to debug: The exceptions in the remote machines are sent to your PC and the task is skipped.
- Scheduling is supported: Even if the number of your tasks is larger than the number of remote machines, the tasks are automatically distributed.
- Resuming is supported: If some tasks failed because of exceptions or other errors, you can restart the failed tasks with skipping the succeeded tasks.

## Requirements
- Python3
- [flask](http://flask.pocoo.org/)
- [requests](http://docs.python-requests.org/en/master/)

## Usage
(An example comes later.  Reading it can be easier.)
1. Copy [oden.py](https://raw.githubusercontent.com/ashiato45/oden/master/oden.py) in your project.
2. Fill in the place holder between `------ User write below ------` and `------ User write above ------`.
    1. `hosts` is a string of the hostnames of remote machines separated by breaks.  In the default setting, it reads the hosts from `hosts.txt`.
    2. `name` is the name of your project of distributed computation.  The results are saved with the names of `(name)(number)_(date).pickle`.
    3. `interval_polling` is the interval of polling to retrive the results from the remote machines.  The unit is second.
    4. `timeout` is the timeout in the HTTP request to communicate remote machines.  The unit is second.
    5. `make_tasks()` has to return a list of tasks.  Any (picklable) Python objects can be used as tasks.
    6. `calc(task)` takes a task and returns the result.  It can return any (picklable) Python objects.  This function is called in the remote machines.
    7. (optional) `handle_finish_machine(uri, name)` is called when a remote machine has no remaining task because of running out of the tasks.
    8. (optional) `show_status()` returns a string.  The return value is shown when you access the remote machine by `http://(hostname):8080`.
3. Copy whole your project to remote machines.
4. Run `python oden.py worker` on the remote machines.  The web servers to run the computations start.  Here 8080 port of the remote machines has to be open to your PC.  ⚠️ Opening 8080 port to the world is insecure.  Oden is designed to communicate only with your PC, so it is not designed to be secure...
5. Run `python oden.py manager` on your PC.  The distribution of the tasks starts!  If all the tasks are consumed, it stops.
6. (optional) If there is something wrong in the computation and a task fails, the stacktrace is sent to your PC and it appears on the log.  If fixing your script to handle the error does not affect the succeeded result, you can restart the computation only for the failed tasks.
    1. Fix your script.
    2. Stop `oden.py` in the remote machines.  Running `killall python` is a good idea.
    3. Start `oden.py` by `python oden.py worker` in the remote machines.
    4. Run `python oden.py resume` on your PC.  It skips the succeeded tasks by checking the result files starts from the `name` and starts to distribute the failed tasks.
