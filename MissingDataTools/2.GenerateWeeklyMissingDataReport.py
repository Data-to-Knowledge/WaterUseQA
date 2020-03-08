"""
This program calculates the number of reports received for each WAP over a
specified week, and compares it to the expected number of reports.

Author: Alan Ambury
Last Edited: 16 December 2019
Contact the developer: alan@whiterockconsulting.co.nz

Inputs to the program:
1. WAPReportingMode.csv - contains the normal reporting frequency of each WAP.
This csv file is generated by a separate program. It needs to be refreshed every
two months.

In order to run the program the user needs to:
1. Have installed the hilltop-py package developed by Mike Exner-Kittridge
2. Have installed the pandas and datetime modules (NB: these come packaged with
the Anaconda distribution of Python)
3. Have the WAPReportingMode.csv saved in the same folder as this program.
"""


from hilltoppy import web_service as ws
import pandas as pd
import datetime as dt


def get_date():
    """Prompts the user to enter the end date for the weekly report"""
    user_date = None
    while user_date is None:
        date_entry = input("Enter the end date for the weekly report in YYYY-MM-DD format: ")
        try:
            year, month, day = map(int, date_entry.split('-'))
            user_date = dt.date(year, month, day)
            print("Data will be extracted for the 7 days ending on {}".format(user_date))
        except ValueError:
            print("Not a valid date. Please try again using YYYY-MM-DD format")        
    return user_date


def get_volume_data(base_url, hts, site, measurement, from_date, to_date):
    """Extracts compliance volume data from Hilltop for a given date range, and sums the reading counts for each day"""
    tsdata = ws.get_data(base_url, hts, site, measurement, from_date, to_date)
    dfdata = tsdata.reset_index().drop(columns='Site').drop(columns='Measurement')
    return dfdata


def transform_volume_data(dataframe, from_date, to_date):
    """This function transforms the volume data to obtain daily totals"""
    dataframe['Date'] = dataframe['DateTime'].dt.date
    daily_counts = dataframe.groupby(['Date'])['Value'].agg(['count']).rename(columns={'count':'Readings'})
    idx = pd.date_range(from_date, to_date)
    daily_counts2 = daily_counts.reindex(idx, fill_value=0)
    return daily_counts2


def main():
    """This function controls the execution of the main program"""
    # Get reporting modes
    wap_modes = pd.read_csv('WAPReportingMode.csv')
    
    ################################
    # Restrict to a subset of sites
    #df = wap_modes[0:1000]
    df = wap_modes
    #################################
    
    
    # Get end date for weekly report
    user_date = get_date()
    # Generate extraction dates
    end_date = user_date + dt.timedelta(days = 1)
    week_start = end_date - dt.timedelta(days = 7)
    year_start = end_date - dt.timedelta(days = 365)
    # Open output file
    outfile = open("Missing Data Report - Week ending {}.csv".format(str(user_date)), "w")
    outfile.write("Site,Mode,PercComplete,LastReport\n")
    # Iterate through site list
    i = 1
    for index, row in df.iterrows(): 
        site = row["Site"]
        mode = row["Mode"]
        base_url = 'http://wateruse.ecan.govt.nz'
        hts = 'WaterUse.hts'        
        measurement = 'Compliance Volume'
        print("Retrieving data for Site {0} - {1}".format(i,site))
        # Try extracting data for the last week
        try:
            week_data = get_volume_data(base_url, hts, site, measurement, str(week_start), str(end_date))
            daily_counts = transform_volume_data(week_data, str(week_start), str(end_date))
            if int(mode) > 0:
                weekly_total = daily_counts['Readings'].sum() - 1
                expected = int(mode) * 7
                perc_complete = round(weekly_total / expected * 100, 1)
                last_report = max(week_data['DateTime'])
                result = "{0},{1},{2},{3}\n".format(site, mode, perc_complete, last_report)
                outfile.write(result)
                i += 1
            elif int(mode) == 0:
                last_report = max(week_data['DateTime'])
                result = "{0},{1},Mode equals 0!,{2}\n".format(site, mode, last_report)
                outfile.write(result)
                i += 1
            elif mode == "No data":
                last_report = max(week_data['DateTime'])
                result = "{0},No mode data,Unknown,{1}\n".format(site, last_report)
                outfile.write(result)
                i += 1                  
        # If there is no data in the last week, extract data for the last year to ascertain when data was last received
        except ValueError:
            try:
                annual_data = get_volume_data(base_url, hts, site, measurement, str(year_start), str(end_date))
                last_report = max(annual_data['DateTime'])
                result = "{0},{1},No data in last week,{2}\n".format(site, mode,last_report)
                outfile.write(result)
                i += 1
            # This except clause deals with the situation where there is no data for the last year
            except ValueError:
                result = "{0},{1},Value error,Unknown\n".format(site, mode)
                outfile.write(result)
                i += 1                
            # Sometimes the web server throws a KeyError. Need to explore the cause of this.
            except KeyError:
                result = "{0},{1},Key error,Unknown\n".format(site, mode)
                outfile.write(result)
                i += 1             
        # Sometimes the web server throws a KeyError. Need to explore the cause of this.
        except KeyError:
            result = "{0},{1},Key error,Unknown\n".format(site, mode)
            outfile.write(result)
            i += 1
    # Close output file
    outfile.close()

main()   