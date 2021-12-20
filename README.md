# Scripts used to generate the Randolph Glacier Inventory version 7

RGI7 is the next version of the Randolph Glacier Inventory. RGI7 intends to be the reference inventory for all of the world's glaciers outside of the two ice sheets. All glacier outlines should be mapped as close as possible to the the year 2000. 

Unlike previous versions of the RGI, RGI7 will be a pure subset of the GLIMS database. This repository contains the scripts that generate RGI7 out of GLIMS. 

This is a work in progress! Contributions and feedback welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for tips and instructions about how to help in this process.

![RGI Workflow](img/workflow_rgi.png)

## 01. Pre-processing workflow

The preprocessing workflow downloads the GLIMS database into regional blocks, converts the GLIMS geometries to the RGI format, 
and prepares the outlines for the regional selection scripts.

Notebooks in the [workflow/preprocessing](workflow/preprocessing) folder:

- Step 1: [Modify the RGI6 regions files for RGI7](workflow/preprocessing/01_rgi7_reg_files.ipynb): small updates to the RGI6 region files
- Step 2: [GLIMS region files download: Level 0 files](workflow/preprocessing/02_l0_download_from_glims.ipynb): download ALL outlines from the GLIMS servers, per region
- Step 3: [Convert GLIMS polygons to RGI polygons: Level 1 files](workflow/preprocessing/03_l1_interiors.ipynb): convert the polygons from the GLIMS to the RGI format
- Step 4: [Select glaciers within region shapes and basic attributes: Level 2 files](workflow/preprocessing/04_l2_select_and_zip.ipynb): a simple overlay to select only the relevant outlines for each region.

## 02. Regional outline selection workflow

Regional notebooks scripts are in the [workflow](workflow) folder.

The work-in-progress RGI7 alpha files are available for review in https://cluster.klima.uni-bremen.de/~fmaussion/misc/rgi7_data/l3_rgi7a_tar. Regions are being added regularly!

## 03. Attribute generation workflow

TBA.

## How to contribute

See [CONTRIBUTING.md](CONTRIBUTING.md).


## Downloads

The files at each level (in tar or shapefile format) are downloadable here:

https://cluster.klima.uni-bremen.de/~fmaussion/misc/rgi7_data/

Careful! The files might (and will) change with time.

File name conventions:
- "level 2 files" (`l2_sel_reg_tars`): GLIMS data files after preprocessing. Ready for the outlines choice scripts.
- "RGI alpha" (`l3_rgi7a_tar`): selected outlines for RGI7, still with GLIMS attributes. Ready for review of the outlines choice.
- "RGI beta" (not there yet) : alpha files with RGI attributes. Ready for review before final publication.

Other folders contain files which are used for testing in production (`l0_support_data`) or which are used to report problems to GLIMS (`l3_problem_glaciers_tar`).


**Download all data at once (currently about 12G):**

```bash
$ mkdir rgi7_data
$ cd rgi7_data
$ wget --recursive --no-parent --cut-dirs=3 -nH -R "index.html*" https://cluster.klima.uni-bremen.de/~fmaussion/misc/rgi7_data/
```

This will recursively download all currently available files on the server, including pre-processing levels and some necessary duplicated files. 

**If you want to participate to the RGI review process**, you may download only the alpha version regional files:

```bash
$ mkdir rgi7a
$ cd rgi7a
$ wget --recursive --no-parent --cut-dirs=4 -nH -R "index.html*" https://cluster.klima.uni-bremen.de/~fmaussion/misc/rgi7_data/l3_rgi7a/
```

**If you want to participate to the RGI selection process**, you may download the level 2 files as well:

```bash
$ mkdir l2_sel_reg_tars
$ cd l2_sel_reg_tars
$ wget --recursive --no-parent --cut-dirs=4 -nH -R "index.html*" https://cluster.klima.uni-bremen.de/~fmaussion/misc/rgi7_data/l2_sel_reg_tars/
```

## RGI region summary and known issues

For accurate, up-to-date information, see the regional scripts (where the outline selection actually happens) and the [RGI7 wiki](https://github.com/GLIMS-RGI/rgi7_scripts/wiki/RGI-7-wiki) on github.

## License

Code: BSD3

Data (RGI): CC BY 4.0
