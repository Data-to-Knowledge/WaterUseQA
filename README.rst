Water use data QA tools
=======================
This git repository contains project code for various water use data QA tools. The repository has several modules for performing different data QA tasks.

Modules:
	-	Missing data tools: 4 tools used to identify missing water use data
		-	Compile WAP Reporting Modes
		-	Generate Weekly Missing Data Report
		-	Create Daily and Hourly Plots – Single WAP
		-	Create Daily and Hourly Plots – WAP List
	-	Time-series analysis and visualisation: 8 tools for analasis and visulaiton of water use data
		-	Generate water meter list
		-	Quality Assessment - WAP List - By Measurement Type
		-	Quality Assessment - WAP List - Combined Series
		-	Analyse Time Series - Without  Consent Conditions - Single WAP
		-	Analyse Time Series - Without  Consent Conditions - WAP List
		-	Analyse Time Series - With Consent Conditions - Single WAP
		-	Analyse Time Series - With Consent Conditions - WAP List
		-	Plot Water Use - Single WAP - Specified Month

Missing data tools
------------------
-	These programs enable you to explore and detect missing water take data, so that the compliance team can investigate and follow-up if necessary. This data assessment needs:
	-	to be applied to all active WAPs
	-	to be run frequently (eg, weekly)
	-	to focus on the latest data (eg, data for the last week).

1	Compile WAP Reporting Modes.py
	-	This program calculates the normal daily reporting frequency for each WAP and compiles the results into a csv file (‘WAPReportingMode.csv’). It calculates the normal reporting frequency by extracting water take data for the last year and calculating the daily reporting mode. In instances where the annual mode equals zero, the program iterates through four quarters of data trying to calculate a non-zero mode.

2	Generate Weekly Missing Data Report.py
	-	This program calculates the number of reports received for each WAP over a specified week and compares it to the expected number of reports. It compiles the results into a csv file (‘Missing Data Report - Week ending YYYY-MM-DD’). In instances where a WAP has no data for the specified week, the last year of data is extracted in order to find when data was last received.
	
3a	Create Daily and Hourly Plots – Single WAP.py
	-	This program calculates the number of reports received for each WAP over a specified week and compares it to the expected number of reports. It compiles the results into a csv file (‘Missing Data Report - Week ending YYYY-MM-DD’). In instances where a WAP has no data for the specified week, the last year of data is extracted in order to find when data was last received.
	
3b	Create Daily and Hourly Plots – WAP List.py
	-	This program can be used to investigate recent volume and meter reading data for a list of WAPs. The program iterates through the WAP list, generating the associated Daily Plot and Hourly Plot pdfs.