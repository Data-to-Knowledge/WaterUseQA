"""
This program generates plots of a) volume extracted and b) number of meter
readings for a WAP of interest. The daily plots show daily totals over the 
course of the last year. The hourly plots show hourly totals over the course
of the last month.

Author: Alan Ambury
Last Edited: 6 January 2020
Contact the developer: alan@whiterockconsulting.co.nz

Inputs to the program:
1. The user needs to specify the WAP of interest

In order to run the program the user needs to:
1. Have installed the hilltop-py package developed by Mike Exner-Kittridge
2. Have installed the pandas, numpy, seaborn, matplotlib and datetime modules
(NB: these come packaged with the Anaconda distribution of Python).
"""

import numpy as np
import pandas as pd
import seaborn as sns
import datetime as dt
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from hilltoppy import web_service as ws


def get_site():
    """This function prompts the user to enter the WAP that they wish to generate plots for"""
    site = None
    while site is None:
        site_entry = input("Enter the WAP of interest: ")
        site_list = ws.site_list('http://wateruse.ecan.govt.nz', 'WaterUse.hts')
        if site_entry in site_list.values:
            site = site_entry
        else:
            print("Not a valid WAP. Please try again.")
    return site
    

def get_volume_data(site, from_date, to_date):
    """Extracts compliance volume data from Hilltop for a given date range, and sums the reading counts for each day"""
    base_url = 'http://wateruse.ecan.govt.nz'
    hts = 'WaterUse.hts'
    measurement = 'Compliance Volume'    
    tsdata = ws.get_data(base_url, hts, site, measurement, from_date, to_date)
    vol_data = tsdata.reset_index().drop(columns='Site').drop(columns='Measurement')
    return vol_data


def process_daily_data(dataframe, from_date, to_date):
    """This function calculates daily totals, adds in any days that are missing data and gets the
    dataframe ready for plotting"""
    dataframe['Date'] = dataframe['DateTime'].dt.date
    daily_counts = dataframe.groupby(['Date'])['Value'].agg(['count', 'sum']).rename(columns={'count':'Readings', 'sum':'Volume'})
    idx = pd.date_range(from_date, to_date)
    daily_counts2 = daily_counts.reindex(idx)
    daily_counts2 = daily_counts2.reset_index().rename(columns={'index':'Date'})
    daily_counts2['Year'] = daily_counts2['Date'].dt.year
    daily_counts2['MonthVal'] = daily_counts2['Date'].dt.month 
    daily_counts2['MonthVal2'] = daily_counts2['MonthVal'].apply(lambda x: '{0:0>2}'.format(x))
    daily_counts2['Month'] = daily_counts2['Year'].astype(str) + "-" + daily_counts2['MonthVal2'].astype(str)
    daily_counts2['Day'] = daily_counts2['Date'].dt.day    
    return daily_counts2


def generate_daily_plots(site, dataframe):
    """This function generates the daily plots and outputs them to a pdf file"""
    # Open pdf
    filename = site.replace('/','-') + ' - Daily Plots'
    pp = PdfPages(filename + '.pdf')
    # Create line plot of daily volumes
    daily_vol_grid = sns.FacetGrid(dataframe, col="Month", hue="Month",
                     col_wrap=4, height=1.5, dropna=False)
    daily_vol_grid.map(plt.plot, "Day", "Volume")
    daily_vol_grid.fig.tight_layout(w_pad=1)
    plt.subplots_adjust(top=0.9)
    daily_vol_grid.fig.suptitle('Volume extracted in m3 (daily)')
    daily_vol_grid.savefig(pp, format='pdf')
    plt.close()
    # Create bar plot of daily readings
    daily_report_grid = sns.FacetGrid(dataframe, col="Month", hue="Month",
                     col_wrap=4, height=1.5)
    daily_report_grid.map(plt.bar, "Day", "Readings")
    daily_report_grid.fig.tight_layout(w_pad=1)
    plt.subplots_adjust(top=0.9)
    daily_report_grid.fig.suptitle('Meter readings received (daily)')
    daily_report_grid.savefig(pp, format='pdf')
    plt.close()
    # Close pdf
    pp.close()


def process_hourly_data(vol_data2, from_date, to_date):
    """This function calculates hourly totals, adds in any days that are missing data and gets the
    dataframe ready for plotting"""
    # Add time variables
    vol_data2['Date'] = vol_data2['DateTime'].dt.date
    vol_data2['Year'] = vol_data2['DateTime'].dt.year
    vol_data2['Month'] = vol_data2['DateTime'].dt.month 
    vol_data2['DayVal'] = vol_data2['DateTime'].dt.day
    vol_data2['Hour'] = vol_data2['DateTime'].dt.hour
    # Group by hour
    hourly_vol = vol_data2.groupby(['Date','Month','DayVal','Hour'])['Value'].agg(['count', 'sum']).rename(columns={'count':'Readings', 'sum':'Volume'}).reset_index()
    return hourly_vol


def add_missing_dates(hourly_vol1, from_date, to_date):
    """This function identifies days that are missing data and adds them to the main dataframe"""
    # Generate a full list of dates
    alldates_timestamp = pd.date_range(from_date, to_date)
    alldates_datetime = alldates_timestamp.to_pydatetime()
    alldates = []
    for item in alldates_datetime:
        date = item.date()
        alldates.append(date)
    # Generate a list of dates that have data
    dates_with_data = hourly_vol1['Date'].unique().tolist()
    # Generate a list of dates that are missing data
    missing_dates = list(set(alldates) - set(dates_with_data))
    # Convert to dataframe
    missing_df = pd.DataFrame(missing_dates, columns = ['Date'])
    # Merge into dataset
    hourly_vol2 = pd.merge(hourly_vol1, missing_df, on='Date', how='outer')
    # Tidy up dataframe
    hourly_vol2['Readings'].fillna(0, inplace=True)
    hourly_vol2['Volume'].fillna(0, inplace=True)
    hourly_vol2['Hour'].fillna(0, inplace=True)
    hourly_vol2['Date'] = pd.to_datetime(hourly_vol2['Date'])
    hourly_vol2['DayVal'] = hourly_vol2['Date'].dt.day
    hourly_vol2['Month'] = hourly_vol2['Date'].dt.month
    hourly_vol2['Hour'] = hourly_vol2['Hour'].astype(int)
    hourly_vol2['Readings'] = hourly_vol2['Readings'].astype(int)
    hourly_vol2['Volume'] = hourly_vol2['Volume'].astype(int)
    # Add in extra date labels needed for plotting
    hourly_vol2['DayVal2'] = hourly_vol2['DayVal'].apply(lambda x: '{0:0>2}'.format(x))
    hourly_vol2['Day'] = hourly_vol2['Month'].astype(str) + "/" + hourly_vol2['DayVal'].astype(str)    
    # Sort by date and hour
    hourly_vol2.sort_values(by=['Date','Hour'], inplace=True)
    return hourly_vol2

    
def generate_hourly_plots(site, dataframe):
    """This function generates the hourly plots and outputs them to a pdf file"""
    # Open pdf
    filename = site.replace('/','-') + ' - Hourly Plots'
    pp = PdfPages(filename + '.pdf')
    # Create line plot of hourly volumes
    hourly_vol_grid = sns.FacetGrid(dataframe, col="Day", hue="Day",
                         col_wrap=7, height=1.5, dropna=False)
    hourly_vol_grid.map(plt.plot, "Hour", "Volume")
    hourly_vol_grid.fig.tight_layout(w_pad=1)
    plt.subplots_adjust(top=0.9)
    hourly_vol_grid.fig.suptitle('Volume extracted in m3 (hourly)')
    hourly_vol_grid.savefig(pp, format='pdf')
    plt.close()
    # Create bar plot ofhourly readings
    hourly_report_grid = sns.FacetGrid(dataframe, col="Day", hue="Day",
                         col_wrap=7, height=1.5)
    # Draw a bar plot
    hourly_report_grid.map(plt.bar, "Hour", "Readings")
    # Adjust the arrangement of the plots
    hourly_report_grid.fig.tight_layout(w_pad=1)
    # Add title
    plt.subplots_adjust(top=0.9)
    hourly_report_grid.fig.suptitle('Meter readings received (hourly)')
    # Export to pdf
    hourly_report_grid.savefig(pp, format='pdf')
    plt.close()
    #Close pdf file
    pp.close()      


def main():
    """This function controls the execution of the main program"""
    # Edit these values
    site = get_site()
    # Generate dates to use for data extraction
    end_date = dt.date.today()
    start_date_year = end_date - dt.timedelta(days = 365)
    start_date_month = end_date - dt.timedelta(days = 31)
    # Generate daily plots for the last year
    try:
        vol_data = get_volume_data(site, str(start_date_year), str(end_date))
        daily_data = process_daily_data(vol_data, start_date_year, end_date)
        # Generate plots and output to pdf
        generate_daily_plots(site, daily_data)
        print("Daily plots have been generated for the year ended {}".format(str(end_date)))
    except ValueError:
        print("{0} has no data for the year ended {1}".format(site, end_date))
    # Generate hourly plots for the last month
    try:
        vol_data2 = get_volume_data(site, str(start_date_month), str(end_date))
        hourly_data1 = process_hourly_data(vol_data2, start_date_month, end_date)
        hourly_data2 = add_missing_dates(hourly_data1, start_date_month, end_date)
        # Generate plots and output to pdf
        generate_hourly_plots(site, hourly_data2)
        print("Hourly plots have been generated for the month ended {0}".format(str(end_date)))
    except ValueError:
        print("{0} has no data for the month ended {1}".format(site, end_date))    


main()