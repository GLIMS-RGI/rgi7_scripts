import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cf


# set the directory where the RGI folders are kept
rgi_dir = '/media/bob/seabox/RGI/'

# TODO:  replace with the final RGI attribute table
global_data = pd.read_csv('/media/bob/bigbox/projects/rgi/rgi07-surges/data/final_surgetable.csv')
global_data = gpd.GeoDataFrame(global_data, geometry=gpd.points_from_xy(global_data['cenlon'], global_data['cenlat']), crs='epsg:4326')

# rename the values according to their labels
reclass = {1.0: 'possible', 2.0: 'probable', 3.0: 'observed'}
global_data.replace({'surge_type': reclass}, inplace=True)


fig = plt.figure(figsize=(9, 5))
ax = plt.axes(projection=ccrs.PlateCarree())

# add cartopy land, lakes, country borders, and coastlines @ 50m resolution
ax.add_feature(cf.LAND, facecolor='whitesmoke')
ax.add_feature(cf.LAKES, facecolor='white', edgecolor='k', linewidth=0.2)
ax.add_feature(cf.BORDERS, linewidth=0.2)
ax.coastlines(resolution='50m', linewidth=0.2)

# TODO: replace with final RGI outlines
gl_outlines = gpd.read_file('/media/bob/bigbox/projects/rgi/rgi07-surges/data/buffered_glacier_outlines/rgi60_buff_diss.shp')
gl_outlines.plot(color='skyblue', ax=ax, zorder=2)

# plot points based on surge_type, using the tab10_r colormap
global_data.plot(column='surge_type', cmap='tab10_r', ax=ax, legend=True, markersize=2, 
                 legend_kwds={'fontsize': 8, 'loc': 'lower left'}, zorder=5)

# add the legend, finalize the plot
# ax.legend(fontsize=14, loc='lower left', markerscale=4)
ax.set_ylim(-85, 85)
ax.set_xlim(-180, 180)

fig.savefig('surgetype_distribution.png', dpi=300, bbox_inches='tight')

