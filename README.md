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
