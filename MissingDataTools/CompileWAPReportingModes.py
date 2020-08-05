
"""
This program calculates the normal reporting frequency of each WAP and compiles
this information into a csv file.

Author: Alan Ambury
Last Edited: 27 July 2020
Contact the developer: alan@whiterockconsulting.co.nz

Notes:
1. This program only needs to be run intermittently (perhaps every 2 months) as
the reporting mode of most WAPs will be fairly stable.
2. The program takes a considerable time to run. For this reason you may like to
restrict it to a subset of WAPs (perhaps 500 at a time). You can use lines 38-42
of the program to achieve this. If you adopt this approach, you will need to 
compile the results from each subset into a combined csv file.

Inputs to the program:

Outputs of the program:
1. WAPReportingMode.csv - contains the normal reporting frequency of each WAP.

In order to run the program the user needs to:
1. Have installed the hilltop-py package developed by Mike Exner-Kittridge
2. Have installed the pandas and datetime modules (NB: these come packaged with
the Anaconda distribution of Python)
"""


from hilltoppy import web_service as ws
import pandas as pd
import datetime as dt


def get_site_list(base_url, hts):
    """Creates a dataframe of sites from the WaterUse.hts file"""
    all_sites = ws.site_list(base_url, hts)
    ################################
    # Restrict to a subset of sites
    sites = all_sites[3400:4000] 
    #sites = all_sites
    #################################    
    return sites
    

def get_volume_data(base_url, hts, site, measurement, from_date, to_date):
    """Extracts compliance volume data from Hilltop for a given date range, and sums the reading counts for each day"""
    tsdata = ws.get_data(base_url, hts, site, measurement, from_date, to_date)
    dfdata = tsdata.reset_index().drop(columns='Site').drop(columns='Measurement')
    dfdata['Date'] = dfdata['DateTime'].dt.date
    daily_counts = dfdata.groupby(['Date'])['Value'].agg(['count']).rename(columns={'count':'Readings'})
    idx = pd.date_range(from_date, to_date)
    daily_counts2 = daily_counts.reindex(idx, fill_value=0)
    return daily_counts2
    
    
def main():
    """This function controls the execution of the main program"""
    base_url = 'http://wateruse.ecan.govt.nz'
    hts = 'WaterUse.hts'
    measurement = 'Compliance Volume'
    # Generate site list
    site_list = get_site_list(base_url, hts)
    # Get today's date
    today = dt.date.today()
    
    ## Annual calculations
    # Create first output file
    outfile = open("WAPMode_Round1.csv", "w")
    outfile.write("Site,Mode,ModeFreq,Method\n")
    # Generate dates
    year1 = today - dt.timedelta(days = 365)    
    # Iterate through site list
    i = 1
    for index, row in site_list.iterrows():
        site = row["SiteName"]
        if ',' not in site:
            print("Retrieving annual data for Site {0} - {1}".format(i, site))
            try:
                annual_data = get_volume_data(base_url, hts, site, measurement, str(year1), str(today))
                mode = annual_data['Readings'].mode()[0]
                mode_freq = round(annual_data[annual_data.Readings == mode].shape[0] / len(annual_data),2)
                print("Annual calculation successful - Mode equals {}".format(mode))
                result = "{0},{1},{2},Annual\n".format(site,mode,mode_freq)
                outfile.write(result)
                i += 1
            except ValueError:
                print("No data in the last year")
                i += 1
            except KeyError:
                print("Key error for annual calculation")
                i += 1           
        elif ',' in site:
            print("Skipping process for Site {0} - {1}".format(i, site))
            i += 1
    # Close output file
    outfile.close()    
    
    ## First quarter calculations
    # Read output file from first round
    wap_modes = pd.read_csv('WAPMode_Round1.csv')
    # Create second output file
    outfile = open("WAPMode_Round2.csv", "w")
    outfile.write("Site,Mode,ModeFreq,Method\n")
    # Generate dates
    qtr1_start = today - dt.timedelta(days = 91) 
    # Iterate through file, recalculating if mode = 0
    for index, row in wap_modes.iterrows(): 
        site = row["Site"]
        mode = row["Mode"]
        mode_freq = row['ModeFreq']
        method = row['Method']
        if mode != 0:
            result = "{0},{1},{2},{3}\n".format(site,mode,mode_freq,method)
            outfile.write(result)
        elif mode == 0:
            try:
                print("Retrieving 1st quarter data for {0}".format(site))
                qtr1_data = get_volume_data(base_url, hts, site, measurement, str(qtr1_start), str(today))
                qtr1_mode = qtr1_data['Readings'].mode()[0]
                # Output calculations if mode > 0
                if qtr1_mode > 0:
                    print("First quarter calculation successful - Mode equals {}".format(qtr1_mode))
                    result = "{0},{1},,Qtr1\n".format(site,qtr1_mode)
                    outfile.write(result)
                elif qtr1_mode == 0:
                    print("Mode still equals {}".format(mode))
                    result = "{0},{1},{2},{3}\n".format(site,mode,mode_freq,method)
                    outfile.write(result)
            except ValueError:
                print("No data for Quarter 1")
                result = "{0},{1},{2},{3}\n".format(site,mode,mode_freq,method)
                outfile.write(result)                
            except KeyError:
                print("Key error for Quarter 1")
                result = "{0},{1},{2},{3}\n".format(site,mode,mode_freq,method)
                outfile.write(result)                           
    # Close output file
    outfile.close()

    ## Second quarter calculations
    # Read output file from first round
    wap_modes = pd.read_csv('WAPMode_Round2.csv')
    # Create second output file
    outfile = open("WAPMode_Round3.csv", "w")
    outfile.write("Site,Mode,ModeFreq,Method\n")
    # Generate dates
    qtr2_start = qtr1_start - dt.timedelta(days = 91) 
    # Iterate through file, recalculating if mode = 0
    for index, row in wap_modes.iterrows(): 
        site = row["Site"]
        mode = row["Mode"]
        mode_freq = row['ModeFreq']
        method = row['Method']
        if mode != 0:
            result = "{0},{1},{2},{3}\n".format(site,mode,mode_freq,method)
            outfile.write(result)
        elif mode == 0:
            try:
                print("Retrieving 2nd quarter data for {0}".format(site))
                qtr2_data = get_volume_data(base_url, hts, site, measurement, str(qtr2_start), str(qtr1_start))
                qtr2_mode = qtr2_data['Readings'].mode()[0]
                # Output calculations if mode > 0
                if qtr2_mode > 0:
                    print("Second quarter calculation successful - Mode equals {}".format(qtr2_mode))
                    result = "{0},{1},,Qtr2\n".format(site,qtr2_mode)
                    outfile.write(result)
                elif qtr2_mode == 0:
                    print("Mode still equals {}".format(mode))
                    result = "{0},{1},{2},{3}\n".format(site,mode,mode_freq,method)
                    outfile.write(result)
            except ValueError:
                print("No data for Quarter 2")
                result = "{0},{1},{2},{3}\n".format(site,mode,mode_freq,method)
                outfile.write(result)                
            except KeyError:
                print("Key error for Quarter 2")
                result = "{0},{1},{2},{3}\n".format(site,mode,mode_freq,method)
                outfile.write(result)                           
    # Close output file
    outfile.close()    

    ## Third quarter calculations
    # Read output file from first round
    wap_modes = pd.read_csv('WAPMode_Round3.csv')
    # Create second output file
    outfile = open("WAPMode_Round4.csv", "w")
    outfile.write("Site,Mode,ModeFreq,Method\n")
    # Generate dates
    qtr3_start = qtr2_start - dt.timedelta(days = 91) 
    # Iterate through file, recalculating if mode = 0
    for index, row in wap_modes.iterrows(): 
        site = row["Site"]
        mode = row["Mode"]
        mode_freq = row['ModeFreq']
        method = row['Method']
        if mode != 0:
            result = "{0},{1},{2},{3}\n".format(site,mode,mode_freq,method)
            outfile.write(result)
        elif mode == 0:
            try:
                print("Retrieving 3rd quarter data for {0}".format(site))
                qtr3_data = get_volume_data(base_url, hts, site, measurement, str(qtr3_start), str(qtr2_start))
                qtr3_mode = qtr3_data['Readings'].mode()[0]
                # Output calculations if mode > 0
                if qtr3_mode > 0:
                    print("Third quarter calculation successful - Mode equals {}".format(qtr3_mode))
                    result = "{0},{1},,Qtr3\n".format(site,qtr3_mode)
                    outfile.write(result)
                elif qtr3_mode == 0:
                    print("Mode still equals {}".format(mode))
                    result = "{0},{1},{2},{3}\n".format(site,mode,mode_freq,method)
                    outfile.write(result)
            except ValueError:
                print("No data for Quarter 3")
                result = "{0},{1},{2},{3}\n".format(site,mode,mode_freq,method)
                outfile.write(result)                
            except KeyError:
                print("Key error for Quarter 3")
                result = "{0},{1},{2},{3}\n".format(site,mode,mode_freq,method)
                outfile.write(result)                           
    # Close output file
    outfile.close()
    
    ## Fourth quarter calculations
    # Read output file from first round
    wap_modes = pd.read_csv('WAPMode_Round4.csv')
    # Create second output file
    outfile = open("WAPReportingMode.csv", "w")
    outfile.write("Site,Mode,ModeFreq,Method\n")
    # Generate dates
    qtr4_start = qtr3_start - dt.timedelta(days = 91) 
    # Iterate through file, recalculating if mode = 0
    for index, row in wap_modes.iterrows(): 
        site = row["Site"]
        mode = row["Mode"]
        mode_freq = row['ModeFreq']
        method = row['Method']
        if mode != 0:
            result = "{0},{1},{2},{3}\n".format(site,mode,mode_freq,method)
            outfile.write(result)
        elif mode == 0:
            try:
                print("Retrieving 4th quarter data for {0}".format(site))
                qtr4_data = get_volume_data(base_url, hts, site, measurement, str(qtr4_start), str(qtr3_start))
                qtr4_mode = qtr4_data['Readings'].mode()[0]
                # Output calculations if mode > 0
                if qtr4_mode > 0:
                    print("Fourth quarter calculation successful - Mode equals {}".format(qtr4_mode))
                    result = "{0},{1},,Qtr4\n".format(site,qtr4_mode)
                    outfile.write(result)
                elif qtr4_mode == 0:
                    print("Mode still equals {}".format(mode))
                    result = "{0},{1},{2},{3}\n".format(site,mode,mode_freq,method)
                    outfile.write(result)
            except ValueError:
                print("No data for Quarter 4")
                result = "{0},{1},{2},{3}\n".format(site,mode,mode_freq,method)
                outfile.write(result)                
            except KeyError:
                print("Key error for Quarter 4")
                result = "{0},{1},{2},{3}\n".format(site,mode,mode_freq,method)
                outfile.write(result)                           
    # Close output file
    outfile.close()     

main()