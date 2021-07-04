# Contribute to the Randolph Glacier Inventory version 7


Thank you for your help with the RGIv7! You can contribute in several ways.

## Review the RGI7 alpha region files

"RGI7 alpha" files contain the current "best choice" out of the GLIMS database for each RGI region. If reviewed positively, this files will enter the "beta" phase (attributes) and eventually become RGI version 7. You can download the current alpha files at: https://cluster.klima.uni-bremen.de/~fmaussion/misc/rgi7_data/l3_rgi7a_tar/

At this stage, reviewers should focus on the following points:
- are all glaciated areas properly inventorized? (remember: the target inventory date of RGI7 is the year 2000)
- are there missing glaciers?
- are there inventories of better quality (in GLIMS or ready to be submitted to GLIMS) that we should use instead?
- etc.

## Signalize a problem in the RGI7 alpha region files

If you found a problem in one of the alpha files or would like to make a suggestion of change, start a new discussion in: https://github.com/GLIMS-RGI/rgi7_scripts/issues. We will do our best to address it. If possible, please suggest a way to address the issue, for example by pointing to the GLIMS outlines we should use instead.

## Solve issues in the RGI7 alpha region files

The RGI7 alpha files are created via python scripts. You will find the scripts in the [workflow](workflow) folder. They are usually quite simple: they start from the GLIMS "level 2" files and select outlines based on one or more criteria, e.g. the analyst name or a combination of various analysts (one for each region). Solving an issue in the RGI7 alpha files might entail the following steps:
- if the outlines to change / add / delete are already in GLIMS, suggest a change in the region scripts
- if the outlines are in GLIMS but are wrong / strange, it might hint at a problem at the preprocessing scripts, or in GLIMS itself (for example, we are aware of [wrongly merged outlines in GLIMS](https://github.com/GLIMS-RGI/glims_issue_tracker/issues/5)). In the later case, the issue needs to be [reported to GLIMS](https://github.com/GLIMS-RGI/glims_issue_tracker/)
- if outlines need to be replaced or changed and are *not* in GLIMS, please discuss this with us first. Since all RGI outlines need to be fed to GLIMS before being available for the RGI, we have to consider time constraints as well

## Help us with the existing RGI alpha regional scripts

You will find the scripts in the [workflow](workflow) folder. We run these exact scripts on our cluster in Bremen. If you have some python experience, you should be able to run these scripts as well relatively easily. Here are the steps needed to run the scripts locally:
- make sure to have a recent scientific python environment on your computer, including jupyter (notebook or lab) and the following scientific python packages: numpy, geopandas, matplotlib.
- download the necessary input files from our severs (https://cluster.klima.uni-bremen.de/~fmaussion/misc/rgi7_data). At the very least, you will need the "level 2 files" (to start from) and possibly some others as well (depending on the region). Follow the instructions in [README.md](README.md) to batch download all necessary files (in case of doubt, run the regional script you want to modify and check which files are needed).
- download and run the regional script. The first code block contains the paths to the necessary input files. Adapt to your setup if necessary.

## Help us with new regional scrips

There are 19 regions in the RGI. If your region of choice is not yet listed in the scripts, we may not have had the time to work on it. If you want to help us, please get in touch first! It might be that we are already working on it, or that we are waiting for outlines to be ingested in GLIMS before going on.
