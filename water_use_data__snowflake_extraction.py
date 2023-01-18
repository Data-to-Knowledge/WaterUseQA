# -*- coding: utf-8 -*-
"""
Created on Thu Feb 17 11:19:01 2022

@author: BenHiggs
"""

#import packages
import snowflake.connector
import matplotlib.pyplot as plt
import pandas as pd
import os
import csv

#change these inputs

#your Snowflake login username
user1 = 'hamish.graham@ecan.govt.nz'

#output path for the data csv
data_Output_path = r'C:\Users\hamishg.CH\OneDrive - Environment Canterbury\Documents\_Projects\Data extraction\Water Use\Rangitata\rangitata_data.csv'
meter_name = r'C:\Users\hamishg.CH\OneDrive - Environment Canterbury\Documents\_Projects\Data extraction\Water Use\Rangitata\waps.csv'

#import meter list from csv and convert to string
site_list = []
with open(meter_name, newline='') as f:
    for row in csv.reader(f):
        site_list.append(row[0])

   

site_list_str = ','.join(map("'{0}'".format, site_list))
site_list_str = '('+site_list_str+')'
#Snowflake connection
ctx = snowflake.connector.connect(
user = user1,
account='ru48422',
authenticator='externalbrowser' ,
region = 'australia-east.azure',
role ='GLOBALREADERS_PROD',
warehouse='USERS_PROD_WH'
)

#create a cursor object
cs = ctx.cursor()

#send a SQL query to Snowflake that sums 15 min data into daily data. Also group by Attribute Name, DataSource etc so data from different sources isnt summed together.
cs.execute('''
    WITH TYPE_CORRECTED_COMBINED_METERS AS (
        SELECT "SiteId", "AttributeName", "UnitName", "HydroYear", "DataSource", "ObservationValue", "ObservationDateTime",
        //create a new column called "PrevObservationValue" for the abstraction recorded in the previous timestep
        LAG("ObservationValue") OVER (PARTITION BY "SiteId", "AttributeName", "DataSource" ORDER BY "ObservationDateTime") AS "PrevObservationValue",
        //create a new column called "PrevObservationDateTime" for the DateTime recorded in the previous time step
        LAG("ObservationDateTime") OVER (PARTITION BY "SiteId", "AttributeName", "DataSource" ORDER BY "ObservationDateTime") AS "PrevObservationDateTime",

        CASE 
            //Water Meter is measured in cumulative m3 and is converted to volume (m3) using: 
            WHEN "AttributeName" = 'Water Meter' THEN
                ("ObservationValue" - "PrevObservationValue")
            //Flow is measured in L/s and is converted to Volume (m3) using: 1000*Flow/(time difference to the previous reading in seconds)
            WHEN "AttributeName" = 'Flow' THEN			
                ("ObservationValue"*1000)/TIMEDIFF(seconds,"PrevObservationDateTime","ObservationDateTime")
            //Average Flow is measured in m3/hr and is converted to Volume (m3) using :Average Flow/(time difference to the previous reading in hours)
            WHEN "AttributeName" = 'Average Flow' THEN
                ("ObservationValue")/TIMEDIFF(hours,"PrevObservationDateTime","ObservationDateTime")  
        ELSE "ObservationValue" 
            END 
        AS MeasuredValue
        
        FROM "WATERDATAREPO_PROD"."hill"."WaterAbstractionObservations"

        WHERE "SiteId" IN ''' + site_list_str + '''
    ),

        //Sum the abstraction volume for each site, date, and data source
        DAILY_DATASOURCE_SUM AS (
            SELECT SUM(MeasuredValue) AS DailyMeasuredValue, DATE, "SiteId", "DataSource"
            FROM (
                SELECT MeasuredValue, "DataSource", "SiteId", TO_DATE("ObservationDateTime") AS DATE
                FROM TYPE_CORRECTED_COMBINED_METERS
                WHERE MeasuredValue >= 0
                )
            GROUP BY "SiteId", DATE, "DataSource"
    ), 

        //Multiple datasource check
        NUMBER_OF_DATASOURCES AS (
        SELECT "SiteId", DATE, COUNT (*) AS "DuplicateDays", MAX(DAILYMEASUREDVALUE) AS "Max", MIN(DAILYMEASUREDVALUE) AS "Min"
        FROM DAILY_DATASOURCE_SUM
        
        GROUP BY "SiteId", DATE
    )

SELECT DDS."SiteId", DDS.DATE, "DataSource", DAILYMEASUREDVALUE, "DuplicateDays", "Max", "Min", "Max"-"Min" AS "Difference"
FROM DAILY_DATASOURCE_SUM DDS
INNER JOIN NUMBER_OF_DATASOURCES NOD
    ON NOD."SiteId" = DDS."SiteId" AND NOD.DATE = DDS.DATE
ORDER BY "SiteId", DATE

    ''')           
        
#convert the returned query result into a dataframe
abstraction_dataM = cs.fetch_pandas_all()

abstraction_dataM.to_csv(data_Output_path)