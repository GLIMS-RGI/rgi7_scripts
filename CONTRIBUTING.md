# Contribute to the Randolph Glacier Inventory version 7

Thank you for your help with the RGIv7! You can contribute in several ways.

## Review the RGI7 alpha region files

"RGI7 alpha" files contain the current "best choice" out of the GLIMS database for each RGI region. If reviewed positively, this files will enter the "beta" phase (attributes) and eventually become RGI version 7. You can download the current alpha files at: https://cluster.klima.uni-bremen.de/~fmaussion/misc/rgi7_data/l3_rgi7a_tar/

## Signalize a problem in the RGI7 alpha region files

If you found a problem in one of the alpha files or would like to make a suggestion of change, start a new discussion in: https://github.com/GLIMS-RGI/rgi7_scripts/issues. We will do our best to address it. If possible, please suggest a way to address the issue, for example by pointing to the GLIMS outlines we should use instead.

## Solve issues in the RGI7 alpha region files

The RGI7 alpha files are created via python scripts. You will find the scripts in the [workflow](workflow) folder. They are usually quite simple: they start from the GLIMS "level 2" files and select outlines based on one or more criteria, e.g. the analyst name or a combination of various analysts (one for each region). Solving an issue in the RGI7 alpha files might entail the following steps:
- if the outlines to change / add / delete are already in GLIMS, suggest a change in the region scripts
- if the outlines are in GLIMS but are wrong / strange, it might hint at a problem at the preprocessing scripts, or in GLIMS itself (for example, we are aware of [wrongly merged outlines in GLIMS](https://github.com/GLIMS-RGI/glims_issue_tracker/issues/5)). In the later case, the issue needs to be [reported to GLIMS](https://github.com/GLIMS-RGI/glims_issue_tracker/)
- if outlines need to be replaced or changed and are *not* in GLIMS, please discuss this with us first. Since all RGI outlines need to be fed to GLIMS before being available for the RGI, we have to consider time constraints as well

