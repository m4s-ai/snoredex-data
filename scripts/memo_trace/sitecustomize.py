"""Observed-input tracer for scripts/check_memo.py; inert unless SNOREDEX_MEMO_TRACE is set."""
import os
import sys


def _install(trace_dir: str) -> None:
    import atexit
    import json
    import uuid

    root = os.path.normcase(os.path.abspath(os.environ["SNOREDEX_MEMO_ROOT"]))
    record = {"reads": set(), "writes": set(), "lists": set(), "probes": set(), "procs": [], "events": set()}
    write_flags = os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC

    def rel(path):
        if path is None or isinstance(path, int):
            return None
        try:
            full = os.path.normcase(os.path.abspath(os.fsdecode(path)))
        except (TypeError, ValueError):
            return None
        return full[len(root) + 1:].replace(os.sep, "/") if full.startswith(root + os.sep) else None

    def add(kind, path):
        name = rel(path)
        if name is not None:
            record[kind].add(name)

    def on_open(args):
        path, mode, flags = args
        writing = any(c in mode for c in "wxa+") if mode else bool(flags & write_flags)
        add("writes" if writing else "reads", path)

    def on_popen(args):
        _executable, argv, cwd, env = args
        argv = [os.fsdecode(a) for a in (argv if isinstance(argv, (list, tuple)) else [argv])]
        record["procs"].append({"argv": argv, "cwd": os.fsdecode(cwd) if cwd else os.getcwd(),
                                "envTraced": env is None or "SNOREDEX_MEMO_TRACE" in env})

    first = lambda a: a[0] if a and a[0] is not None else "."
    handlers = {
        "open": on_open, "subprocess.Popen": on_popen,
        "os.listdir": lambda a: add("lists", first(a)), "os.scandir": lambda a: add("lists", first(a)),
        "os.rename": lambda a: (add("writes", a[0]), add("writes", a[1])),
        "os.remove": lambda a: add("writes", a[0]), "os.rmdir": lambda a: add("writes", a[0]),
        "os.mkdir": lambda a: add("writes", a[0]), "os.truncate": lambda a: add("writes", a[0]),
        "os.utime": lambda a: add("writes", a[0]), "shutil.rmtree": lambda a: add("writes", a[0]),
        "sqlite3.connect": lambda a: add("reads", a[0]),
    }
    flagged = {"os.system": "exec", "os.exec": "exec", "os.posix_spawn": "exec", "os.spawn": "exec",
               "os.startfile": "exec", "socket.connect": "network", "socket.getaddrinfo": "network",
               "urllib.Request": "network"}

    def hook(event, args):
        handler = handlers.get(event)
        try:
            if handler is not None:
                handler(args)
            elif event in flagged:
                record["events"].add(flagged[event])
        except Exception:  # noqa: BLE001 - a tracer error must make the step non-memoizable
            record["events"].add("tracer-error")

    def probing(function):
        def wrapper(path, *args, **kwargs):
            if not kwargs.get("dir_fd"):
                add("probes", path)
            return function(path, *args, **kwargs)
        return wrapper

    os.stat, os.lstat = probing(os.stat), probing(os.lstat)
    for name in ("exists", "lexists", "isfile", "isdir", "islink"):
        setattr(os.path, name, probing(getattr(os.path, name)))

    def dump():
        data = {k: sorted(v) if isinstance(v, set) else v for k, v in record.items()}
        target = os.path.join(trace_dir, f"{os.getpid()}-{uuid.uuid4().hex}.json")
        with open(target + ".tmp", "w", encoding="utf-8") as handle:
            json.dump(data, handle)
        os.replace(target + ".tmp", target)

    if hasattr(os, "register_at_fork"):
        os.register_at_fork(after_in_child=lambda: open(
            os.path.join(trace_dir, f"{os.getpid()}-{uuid.uuid4().hex}.forked"), "w").close())
    atexit.register(dump)
    sys.addaudithook(hook)


if os.environ.get("SNOREDEX_MEMO_TRACE"):
    _install(os.environ["SNOREDEX_MEMO_TRACE"])
