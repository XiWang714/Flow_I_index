import geopandas as gpd
import pandas as pd
from geographiclib.geodesic import Geodesic
from shapely.geometry import Point
import numpy as np
from shapely import wkt
import osmnx as ox

def calgeodis(r):
    geodis = Geodesic.WGS84.Inverse(r.olat, r.olon, r.dlat, r.dlon)['s12']
    return geodis

def calAlpha(grp):
    medlen = np.median(grp.geodis)
    flowcnt = len(grp)
    return pd.Series([medlen,flowcnt],index=["medlen","flowcnt"])

## core function to calculate I-index
def idxfunc(grp,alpha):
    flowlen_arr = list(grp.geodis)
    flowlen_sum = np.sum(flowlen_arr)/1000  #convert to km
    flowcnt = len(flowlen_arr)
    flowlen_arr.sort(reverse=True)
    flowlen_arr_index = [(k[0] + 1, k[1]) for k in list(enumerate(flowlen_arr))]
    if (len(list(filter(lambda x: x[0] <= x[1] / alpha, flowlen_arr_index))) > 0):
        iidx = list(filter(lambda x: x[0] <= x[1] / alpha, flowlen_arr_index))[-1][0]
        return pd.Series([iidx,flowcnt,flowlen_sum],index=["I_index","flowtotalcnt","flowtotallength"])
    else:
        iidx = 0
        return pd.Series([iidx,flowcnt,flowlen_sum],index=["I_index","flowtotalcnt","flowtotallength"])

if __name__ == "__main__":

    ## Step1 File path and params
    odfile = "./data/bj_od_sample.csv"       #OD flow file, header: odid, olon,olat, dlon,dlat
    polyfile = "./data/grid.csv"             #Polygon file, header: polyid, geometry
    odtype = "d"                             #Calculated based on O point or D point, default D
    alphastr = "auto"                        #decide alpha: choose auto or direct give a number
    iidxfile = "./data/grid_iidx.csv"        #result file, header: "polyid","alpha","I_index","flowtotalcnt","flowtotallength"
    prjrawcode = 'EPSG:4326'                 #information of gcs for later project


    ## Step2 read file to geodataframe and project
    poly_df = pd.read_csv(polyfile)
    poly_df['geometry'] = poly_df['geometry'].apply(wkt.loads)
    poly_gdf = gpd.GeoDataFrame(poly_df, geometry='geometry',crs=prjrawcode)
    poly_gdf = ox.projection.project_gdf(poly_gdf)

    od_df = pd.read_csv(odfile)
    od_df["geodis"] = od_df.apply(calgeodis, axis=1)
    if odtype.lower()=="d":
        odpt_gdf = gpd.GeoDataFrame(od_df, geometry=[Point(xy) for xy in zip(od_df.dlon, od_df.dlat)],crs=prjrawcode)
    else:
        odpt_gdf = gpd.GeoDataFrame(od_df, geometry=[Point(xy) for xy in zip(od_df.olon, od_df.olat)],crs=prjrawcode)
    odpt_gdf = odpt_gdf.to_crs(poly_gdf.crs)

    ##step3 calculate I-index
    ## 3.1 spatial join
    flows_with_poly = gpd.sjoin(odpt_gdf, poly_gdf, how="inner", predicate="within")

    ## 3.2 decide alpha
    if alphastr=="auto":
        alphadf = flows_with_poly.groupby('polyid').apply(calAlpha)
        alpha = np.median(alphadf["medlen"]) / np.median(alphadf["flowcnt"])
    else:
        alpha = float(alphastr)

    ## 3.3 calculate I-index for each poly and output
    idxdf = flows_with_poly.groupby('polyid',as_index=False).apply(idxfunc,alpha=alpha)
    idxdf['alpha'] = alpha
    idxdf[["polyid","alpha","I_index","flowtotalcnt","flowtotallength"]].to_csv(iidxfile,index=False,sep =',')




