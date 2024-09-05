import time as t

start_times = {}
times = {}

def start(name:str):
    start_times[name] = t.time()

def end(name:str,multiplier:int=1):
    if name not in times:
        times[name] = []
    times[name].append((t.time()-start_times[name])*multiplier)


def results():
    global times
    results = {}

    for name,time in times.items():
        results[name] = sum(time)/len(time)

    from operator import itemgetter
    r = sorted(results.items(), key=itemgetter(1))

    for name,time in r:
        print(f'{name} Took {time} Seconds on average')
