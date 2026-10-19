import sys
import argparse
import runpy
from pathlib import Path
from crashloom.storage import FlightStorage
from crashloom.synthesizer import ReproducerSynthesizer

def main(argv=None):
    parser = argparse.ArgumentParser(prog="crashloom")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    run_p = subparsers.add_parser("run", help="Run a Python script and record uncaught exceptions")
    run_p.add_argument("script", help="Python script to execute")
    run_p.add_argument("script_args", nargs=argparse.REMAINDER, help="Arguments passed to the script")

    list_p = subparsers.add_parser("list")
    list_p.add_argument("--limit", type=int, default=20)
    
    inspect_p = subparsers.add_parser("inspect")
    inspect_p.add_argument("identifier")
    
    synth_p = subparsers.add_parser("synthesize")
    synth_p.add_argument("identifier")
    synth_p.add_argument("-o", "--output", default=None)
    
    args = parser.parse_args(argv)
    if args.command == "run":
        script = Path(args.script).expanduser().resolve()
        if not script.is_file():
            parser.error(f"script not found: {script}")
        from crashloom import install

        install()
        sys.argv = [str(script), *args.script_args]
        runpy.run_path(str(script), run_name="__main__")
        return 0

    storage = FlightStorage()

    if args.command == "list":
        for r in storage.list_recent(args.limit):
            print(f"{r.flight_id} | {r.fingerprint} | {r.exception_type}")
    elif args.command == "inspect":
        rec = storage.get(args.identifier)
        if rec:
            print(rec.to_json())
    elif args.command == "synthesize":
        rec = storage.get(args.identifier)
        if rec:
            code = ReproducerSynthesizer().synthesize(rec)
            if args.output:
                open(args.output, "w").write(code)
            else:
                print(code)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
