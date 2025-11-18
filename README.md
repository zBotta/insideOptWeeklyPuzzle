# insideOptWeeklyPuzzle
Operation Research problems proposed by  [Meinolf Sellmann](https://www.linkedin.com/in/meinolf-sellmann-a349636/)

## Environment set up
To be able to run the examples the following solvers must be installed in your computer:
- SCIP [downloadhere](https://portal.ampl.com/user/ampl/download/scip)
- CBC [download here](https://portal.ampl.com/user/ampl/download/cbc)

**NB**: Remember to add `cbc` and `scip` executables to the PATH (Windows) or to link it into bin folder (Linux).

## How to run

UV is installed in all subfolders. When downlaoded, verify that you have installed UV in your system `pip install uv`.

Then run the python files with the uv environment, e.g.:

```
cd ambiguity-crops
uv sync
uv run python ambiguity-crops.py --scenario both
```

