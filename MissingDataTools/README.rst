=========================================
Water Use Data Assessment: Missing Data
=========================================

Aims
=======

To detect missing water take data over the last week, so that the compliance team can investigate and follow-up if necessary. This data assessment needs:

-	to be applied to all active WAPs
-	to be run frequently (eg, weekly)
-	to focus on the latest data (eg, data for the last week).

Requirements
----------------
An initial method of detecting missing water take data has been developed in Python, utilising the Hilltop web server. In order to run the associated Python programs the user will need to have installed:

-	Python Anaconda
-	The hilltop-py package developed by Mike Exner-Kitteridge.

Summary of method and instructions for running Python programs
=================================================================

The method involves three main steps.

1.	Compile WAP Reporting Modes.py
-------------------------------------
This program calculates the normal daily reporting frequency for each WAP and compiles the results into a csv file (‘WAPReportingMode.csv’). It calculates the normal reporting frequency by extracting water take data for the last year and calculating the daily reporting mode. In instances where the annual mode equals zero, the program iterates through four quarters of data trying to calculate a non-zero mode.
Instructions for running: 

-	This programme only needs to be run intermittently (perhaps every two months) for two main reasons. Firstly, the reporting mode of most WAPs will be fairly stable. Secondly, this programme takes a considerable time to run (due to the extraction of annual data). 
-	For the purposes of this initial trial, this programme does not need to be run. All that is needed is the ‘WAPReportingMode.csv’ file that has already been generated.

2.	Generate Weekly Missing Data Report.py
--------------------------------------------
This program calculates the number of reports received for each WAP over a specified week and compares it to the expected number of reports. It compiles the results into a csv file (‘Missing Data Report - Week ending YYYY-MM-DD’). In instances where a WAP has no data for the specified week, the last year of data is extracted in order to find when data was last received.
Instructions for running:

-	Make sure ‘WAPReportingMode.csv’ is saved in the same folder as this program.
-	On running the program you will be prompted to enter the end date for the weekly report in YYYY-MM-DD format (NB: this gives you some control over the time period that the assessment will focus on).
-	Depending on the time it takes for the program to run, you may wish to restrict it to a subset of WAPs. You can use lines 63-65 of the program to achieve this.

3. Create Daily and Hourly Plots – Single WAP.py
---------------------------------------------------
This program can be used to investigate recent volume and meter reading data for a single WAP of interest. If the data exists, it generates two pdf files: a) a Daily Plot file that displays daily totals over the course of the last year, and b) a Hourly Plot file that displays hourly totals over the course of the last month. All the pdf files that are generated will be stored in the folder that the program is saved in.
Instructions for running:

-	On running the program you will be prompted to enter the WAP that you are interested in. Once entered the program will execute.

4. Create Daily and Hourly Plots – WAP List.py
--------------------------------------------------
This program can be used to investigate recent volume and meter reading data for a list of WAPs. The program iterates through the WAP list, generating the associated Daily Plot and Hourly Plot pdfs.
Instructions for running:

-	You will need to create a csv file containing the WAPs you wish to investigate and save it in the same folder that the program is saved in.
-	On running the program you will be prompted to enter the name of your csv file. Once entered the program will execute.

Troubleshooting
=====================

1.	ElementTree.ParseError:

	Occasionally, on running a program, you may get the error message below. This seems to be a temporary issue with the Hilltop web server and is normally resolved when you re-run the program. 
	xml.etree.ElementTree.ParseError: not well-formed (invalid token)

2.	Key and Value errors in Weekly Missing Data report:

	Occasionally (approximately 0.2 percent of the time), the Hilltop web server throws a KeyError or ValueError when retrieving data. At this stage I’m not sure of the exact cause of this. I have set up my program so that it records these errors without crashing. However, I would like to investigate and understand the root cause of this problem.

Contact details
=================
Alan Ambury
Email: alan@whiterockconsulting.co.nz
Cell: 0274 942 263
