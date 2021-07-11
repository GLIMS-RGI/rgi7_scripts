# Scripts used to generate the Randolph Glacier Inventory version 7

RGI7 is the next version of the Randolph Glacier Inventory. RGI7 intends to be the reference inventory for all of the world's glaciers outside of the two ice sheets. All glacier outlines should be mapped as close as possible to the the year 2000. 

Unlike previous versions of the RGI, RGI7 will be a full subset of the GLIMS database. This repository contains the scripts that generate RGI7 out of GLIMS. 

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

File name conventions:
- "l2 files": GLIMS data files after preprocessing. Ready for the outlines choice scripts.
- "RGI alpha": selected outlines for RGI7, still with GLIMS attributes. Ready for review of the outlines choice.
- "RGI beta": alpha files with RGI attributes. Ready for review before final publication.

The files at each level (in tar or shapefile format) are downloadable here:

https://cluster.klima.uni-bremen.de/~fmaussion/misc/rgi7_data/

Careful! The files might (and will) change with time.

**Download all data at once (currently about 10G):**

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

Thes list below is intentionally short. For accurate, up-to-date information, see the regional scripts (where the outline selection actually happens) and the [regional discussions](https://github.com/GLIMS-RGI/rgi7_scripts/issues) on github.

### RGI01 (Alaska)

Same as RGI6.

Known issues in 7a:
- two outlines (multipolygon) are [wrongly merged](https://github.com/GLIMS-RGI/glims_issue_tracker/issues/5) in GLIMS (i.e. this needs a fix in GLIMS itself).


### RGI09 (Russian Arctic)

Same as RGI6.

Known issues in 7a:
- NA

### RGI10 (Asia North)

RGI7a for region 10 was produced by:
- extracting RGI6 data from GLIMS data base
- dropping all nominal glaciers (116, located on Wrangel Island and islands in the Sibirian Sea) 
- replacing glaciers in Kamtchatka with data by Barr

Known issues in 7a:
- omitted nominal glaciers which account for about 84 km² and could not be replaced by other data as no outlines for these areas are available in GLIMS.
- the subset of Kamchatka glaciers which shall be replaced based on data by Barr. In a first version we replaced all...
- the glacier divides presented by Barr which should be checked and eventually be revised. 


### RGI12 (Caucasus and Middle East)

Most outlines replaced with the 2013 inventory by Levan Tielidze in Caucasus and the 2011 inventory by Neamat Karimi and others in Middle East. Remaining outlines in smaller mountain chains are from RGI6.

Known issues in 7a:
- Remaining outlines from RGI6 of variable quality
- The two new inventories are of good quality but quite far from the year 2000

### RGI13, 14, 15 (High Mountain Asia)

All outlines replaced with GAMDAMv2 (Akiko Sakai). 

Known issues in 7a:
- about 400 outlines that are not properly separated (probably same as region 01: data ingestion issues in GLIMS).

## License

Code: BSD3

Data (RGI): CC BY 4.0
