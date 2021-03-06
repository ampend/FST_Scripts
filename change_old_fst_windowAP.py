#!/usr/bin/env python
import fileinput
import math
import numpy as np
import sys
import re
from optparse import  OptionParser

###############################################################################
USAGE = """
python Fst_hudson_window_50kbSlide.py	--pop1 < Count file from population 1 needing to go into analysis > 
								--pop2 < Count file from population 2 needing to go into analysis >
								--out < Output file stem name >
								--dir < Root directory for output (before Sliding/NoSliding)>

pop1 == Count file from population 1 needing to go into analysis
pop2 == Count file from population 2 needing to go into analysis
out == Output file stem name
dir == root directory (results will pass to root + Sliding/ and root + NoSliding/)
"""

parser = OptionParser(USAGE)
parser.add_option('--pop1',dest='pop1', help = 'Count file from population 1 needing to go into analysis (generated from vcf tools)')
parser.add_option('--pop2',dest='pop2', help = 'Count file from population 2 needing to go into analysis (generated from vcf tools)')
parser.add_option('--out',dest='out', help = 'Output file stem name (e.g. dog_wolf_54callset_Xnonpar)')
parser.add_option('--dir',dest='dir', help = 'root directory (results will pass to root + Sliding/ and root + NoSliding/)')

(options, args) = parser.parse_args()

parser = OptionParser(USAGE)
if options.pop1 is None:
	parser.error('input file name not given')
if options.pop2 is None:
	parser.error('input file name not given')
if options.out is None:
	parser.error('Output file stem name not given')
if options.dir is None:
	parser.error('No output root directory given')
############################################################################

#####################################################################
# PER JEFF:
# Calculates estimate of 2 pop Fst using Hudson's estimator
# as described in Bhatia et al 2013
# input is [a1_count,a2_count][a1_counts,a2_count]
# returns (fst,numerator,denominator) for use in taking ratio of averages for multiple markers
def fst_hudson_twopop(pop1,pop2):
    n1 = pop1[0] + pop1[1]
    n2 = pop2[0] + pop2[1]
    p1 = float(pop1[0]) / float((pop1[0]+pop1[1]))  # allele freq in pop 1
    p2 = float(pop2[0]) / float((pop2[0]+pop2[1]))  # allele freq in pop 2

    num = (p1-p2)*(p1-p2) -  ((p1*(1.0-p1))/(n1-1)) -  ((p2*(1.0-p2))/(n2-1.0))
    denom = p1*(1.0-p2) + p2*(1.0-p1)
    #The below code was added to check why f=num/denom was failing,
    #found it was due to having pop1 or pop2 allele frequencies = 0
    #if num == 0:
    #    print "num = zero"
    """if denom == 0:
        f = 0
        print 'pop1 =', pop1
        print 'p1 = float(%i) / float((%i+%i))' % (pop1[0], pop1[0], pop1[1])
        print 'p2 = float(%i) / float(%i + %i))' % (pop2[0], pop2[0], pop2[1])
        print "denom = zero"
    else:
        f = 1
    """
    #if denom == 0:
     #   f=0
    #else:
     #   f = float(num)/float(denom)
    f = float(num)/float(denom)
    return (f,num,denom)
#####################################################################
def process_inputlines(line):
	line = line.rstrip() #removing extraneous whitespace characters
	line = line.split() #delimiting "columns" in the file based on tabs
	line[4] = float(line[4].split(':')[-1])
	line[5] = float(line[5].split(':')[-1])
	return line[4],line[5] 
#####################################################################
#####################################################################
###Setting up outfiles
#SLIDING (Overlapping every 50kb)
type = 'Sliding/'
#fstOutfile = 'FSTOutput_DogsVersusWolves_HudsonCalc_withFixed_AutoXpar.txt' #Write out the new FST data here
fstOutfile = options.dir + type + options.out + '_Hudson_Fst_200kbWindow_50kbSlide.txt' #Write out the new FST data here
fstOutFile = open(fstOutfile, 'w')
header = 'CHROM' + '\t' + 'START_POS' + '\t' + 'END_POS' + '\t' + 'WINDOW_ID' + '\t' +'N_varients_tot' + '\t' + 'N_varients_forFst' + '\t' + 'N_varients_fixed' + '\t' + 'RofA_Fst' + '\t' + 'AofR_Fst' + '\t'
fstOutFile.write('%s' % (header))
fstOutFile.write("\n")

#NOSLIDING (Non-overlapping windows)
type = 'NoSliding/'
#fstOutfile = 'FSTOutput_DogsVersusWolves_HudsonCalc_withFixed_AutoXpar.txt' #Write out the new FST data here
fstNoOutfile = options.dir + type + options.out + '_Hudson_Fst_200kbWindow.txt' #Write out the new FST data here
fstNoOutFile = open(fstNoOutfile, 'w')
header = 'CHROM' + '\t' + 'START_POS' + '\t' + 'END_POS' + '\t' + 'WINDOW_ID' + '\t' +'N_varients_tot' + '\t' + 'N_varients_forFst' + '\t' + 'N_varients_fixed' + '\t' + 'RofA_Fst' + '\t' + 'AofR_Fst' + '\t'
fstNoOutFile.write('%s' % (header))
fstNoOutFile.write("\n")

#####################################################################
###Input files
dogCountFile = options.pop1
wolfCountFile = options.pop2

#dogCountFile = "TEST_village_biallelic_chr38_counts.frq.count" #Counts generated by VCF tools for dogs only
#wolfCountFile = "TEST_wolves_biallelic_chr38_counts.frq.count" #Counts generated by VCF tools for wolves only
#####################################################################
#### EXAMPLE OF COUNT FILE:
"""
chr1    32998   2       164     C:164   T:0 # You'll need a pop1 list to have 164, 0
chr1    33084   2       164     C:164   T:0 # Pop1 : 164, 0
chr1    33288   2       164     C:141   T:23 #Pop1: 141,23
chr1    33327   2       164     C:140   T:24
chr1    33353   2       164     G:163   T:1"""
chromlist = []

chromSizefile = '/home/ampend/kidd-lab-scratch/www/track-hub/canFam3/canFam3.1-browser-chrom-sizes.fai'
print 'Reading in chromosome lengths from: ', chromSizefile
chromSizeFile = open(chromSizefile, 'r')

chromSizeList = {}
#I also need a list of chr and position for finding the index for windows 
for line in chromSizeFile:
	if "chrUn" in line: #ignore chromsome unknowns 
		continue
	if "chrM" in line: #ignore mito
		continue
	line = line.rstrip()
	line = line.split()
	
	chromID = line[0] #chromosome ID
	chromlist.append(chromID)
	chromLength = int(line[1]) #length of chromosome
	chromSizeList[chromID] = chromLength

print chromSizeList

#####################################################################
#Change the below to generate pop1 and pop2 lists for the wolves and dogs separately
#that can be read into the function later. 
#I also need a list of chr and position for each SNP
chr_pos = []
for line in fileinput.input([dogCountFile]):
	if line[0] == 'C':
		continue 
	line = line.rstrip() #removing extraneous whitespace characters
	line = line.split() #delimiting "columns" in the file based on tabs		
	if len(chromlist) == 0 or line[0] != chromlist[-1]:
		chromlist.append(line[0])
	chr_pos.append(line) #I dont want to append the whole line I just need chr and pos...
	#print chr_pos
#####################################################################
pop1 = [] #dog allele counts
for line in fileinput.input([dogCountFile]):  #change count file for dog and count file for wolf here
	if line[0] == 'C':
		continue 
	temp = process_inputlines(line) #temp's structure is allele1, allele2
	pop1.append(temp) #this is adding the two alleles to pop1
#####################################################################
pop2 = [] #wolf allele counts
for line in fileinput.input([wolfCountFile]):	
	if line[0] == 'C':
		continue 
	temp = process_inputlines(line)
	pop2.append(temp)
#####################################################################

head_idx = 0
tail_idx = 0
last_line = 0

for chrom in chromlist:
	window_start = 0
	window_end = 0
	windowCount = 0
	lastWindow = False
	loopnum = 0
	#Keeping track of start positions. This will determine if the window
	#	is printed to the non-overlapping sliding window outfile or just the
	#	overlapping sliding window file
	newStart = 0
	nextStart = 1
	for i in range(1,130000000,50000):  #figure out the head/tail index
		loopnum +=1
		window_start = i
		window_end = i + 200000 - 1
		##KEEPING TRACK OF PREVIOUS WINDOW
		thisStart = i
	
		if window_start > chromSizeList[chrom]:
			break
		if int(window_end) > int(chromSizeList[chrom]): #if the end of the window extends further than the length of the chromsome, then the window end is the length of the chromosome
			window_end = int(chromSizeList[chrom])
		while int(chr_pos[head_idx][1]) < i and chr_pos[head_idx][0] == chrom:
			head_idx += 1
		if head_idx >= len(chr_pos):
			break
		if tail_idx >= len(chr_pos):
			break
		while (int(chr_pos[tail_idx][1]) <= (i+200000) and chr_pos[tail_idx][0] == chrom):
			tail_idx += 1
			if tail_idx == len(chr_pos): 
				last_line = 1
				break
		tail_ind_new = tail_idx - 1
		# Columns for output
		window_chr = chr_pos[head_idx][0]
		N_varients = tail_ind_new - head_idx
		windowCount += 1 
		N_varients_fixed = 0 
		N_varients_tot = 0
		N_varients_forFst = 0 
		
		if N_varients < 1: #This excludes windows with no variants in them. These will not go to calculating Fst
			continue
		fList = []
		numList = []
		denomList = []
		
		#Here is where you'll read in the new subroutine from Jeff (at the top)
		for k in range(head_idx, tail_ind_new+1): #This is going to calculate the F,num,denom at each site in the window
			N_varients_tot += 1
			if pop1[k][0] == 0 and pop2[k][0] == 0 or pop1[k][1] == 0 and pop2[k][1] == 0:
				#print 'pop1[k][0] and pop2[k][0]', pop1[k][0], pop2[k][0]
				#print 'pop1[k][1] and pop2[k][1]', pop1[k][1], pop2[k][1]
				N_varients_fixed+=1
				continue
			temp = fst_hudson_twopop(pop1[k],pop2[k]) #This function writes out three values: 1) f, 2) numerator, and 3) denominator
			f = temp[0] #defining variables for comprehension, not utility, here that were output from the fst_hudson_twopop function
			num = temp[1]
			denom = temp[2]
			N_varients_forFst += 1 
			fList.append(f) #now we are saving those to a list here that can be used to calculate the average later
			numList.append(num)
			denomList.append(denom)
		
		########################
		#Only until all the values for f,num,and denom are calculated can you find the average of ratios, etc.
		#Here is where you would calculate the AofR and RofA from the lists we generated above (f,num,denom)
		#AofR = averaging all of the Fst ratios 
		if len(fList) == 0:
			continue
		AofR = float(sum(fList))/len(fList)
		
		#RofA = averaging all the numerators and dividing it by the average of denominators:
		meanNum = float(sum(numList))/len(numList) #check where to put the float
		meanDenom = float(sum(denomList))/len(denomList)
		RofA = float(meanNum)/meanDenom
		########################
		#Printing out for sliding (overlapping)
		#Every window will be printed out to this file
		fstOutFile.write('%s\t%s\t%s\t%s_%s\t' % (window_chr, window_start, window_end, window_chr, window_start)) #change this to the new outfile for FST data
		#here is where you want to write out the windowID, RofA, AofR
		fstOutFile.write('%i\t%i\t%i\t%f\t%f\n' % (N_varients_tot, N_varients_forFst, N_varients_fixed, RofA, AofR)) #(remember that you can use %.3f (example) to limit the decimal places for these if you want)
		########################
		#Printing out for nosliding (no overlapping)
		#Only every 200kb will be printed out to this file
		"""if loopnum > 4:
			print loopnum, window_chr, window_start, window_end
		if loopnum == 1:
			fstNoOutFile.write('%s\t%s\t%s\t%s_%s\t' % (window_chr, window_start, window_end, window_chr, window_start)) #change this to the new outfile for FST data
			#here is where you want to write out the windowID, RofA, AofR
			fstNoOutFile.write('%i\t%i\t%i\t%f\t%f\n' % (N_varients_tot, N_varients_forFst, N_varients_fixed, RofA, AofR)) #(remember that you can use %.3f (example) to limit the decimal places for these if you want)
		if loopnum == 4:
			loopnum = 0"""
		"""if loopnum == 1: #always prints the first loop
			fstNoOutFile.write('%s\t%s\t%s\t%s_%s\t' % (window_chr, window_start, window_end, window_chr, window_start)) #change this to the new outfile for FST data
			#here is where you want to write out the windowID, RofA, AofR
			fstNoOutFile.write('%i\t%i\t%i\t%f\t%f\n' % (N_varients_tot, N_varients_forFst, N_varients_fixed, RofA, AofR)) #(remember that you can use %.3f (example) to limit the decimal places for these if you want)
			last = 1
		if loopnum - last == 4:
			#print loopnum, window_chr, window_start, window_end
			fstNoOutFile.write('%s\t%s\t%s\t%s_%s\t' % (window_chr, window_start, window_end, window_chr, window_start)) #change this to the new outfile for FST data
			#here is where you want to write out the windowID, RofA, AofR
			fstNoOutFile.write('%i\t%i\t%i\t%f\t%f\n' % (N_varients_tot, N_varients_forFst, N_varients_fixed, RofA, AofR)) #(remember that you can use %.3f (example) to limit the decimal places for these if you want)
			last = loopnum"""
		"""if thisStart == 1: #for first line
			fstNoOutFile.write('%s\t%s\t%s\t%s_%s\t' % (window_chr, window_start, window_end, window_chr, window_start)) #change this to the new outfile for FST data
			#here is where you want to write out the windowID, RofA, AofR
			fstNoOutFile.write('%i\t%i\t%i\t%f\t%f\n' % (N_varients_tot, N_varients_forFst, N_varients_fixed, RofA, AofR)) #(remember that you can use %.3f (example) to limit the decimal places for these if you want)
			nextStart = thisStart + 200000"""
		#This is for the first line because we set thisStart and nextStart = 1
		if thisStart == nextStart:
			fstNoOutFile.write('%s\t%s\t%s\t%s_%s\t' % (window_chr, window_start, window_end, window_chr, window_start)) #change this to the new outfile for FST data
			#here is where you want to write out the windowID, RofA, AofR
			fstNoOutFile.write('%i\t%i\t%i\t%f\t%f\n' % (N_varients_tot, N_varients_forFst, N_varients_fixed, RofA, AofR)) #(remember that you can use %.3f (example) to limit the decimal places for these if you want)
			nextStart = thisStart + 200000
		#This had to be written in this way because if a window didn't pass the above filtration
		#	requirements, then it would never get to this step, and the window start (or thisStart)
		#	would continually getting bigger, but the nextStart never had a chance to increase.
		#Here, if the window Start is longer than the next 200kb nonoverlapping window coordinate,
		#	then it checks to see if the difference between them is divisible by 200k, if so, 
		#	then it would work as the next possible window. 
		if thisStart > nextStart:
			diff = thisStart - nextStart
			if diff % 200000 == 0:
				fstNoOutFile.write('%s\t%s\t%s\t%s_%s\t' % (window_chr, window_start, window_end, window_chr, window_start)) #change this to the new outfile for FST data
				#here is where you want to write out the windowID, RofA, AofR
				fstNoOutFile.write('%i\t%i\t%i\t%f\t%f\n' % (N_varients_tot, N_varients_forFst, N_varients_fixed, RofA, AofR)) #(remember that you can use %.3f (example) to limit the decimal places for these if you want)
				nextStart = thisStart + 200000					
			else:
				continue
		#print thisStart, nextStart, int(thisStart - nextStart)

		if last_line == 1:
			break
		if chr_pos[tail_idx][0] != chrom:
			head_idx = tail_idx
			break
	#break
	#This prints out the chromosome stats when everything is done running and this corresponds to stats for the last chromosome only
	print 'Chrom: ', chrom
	print 'Window count', windowCount
	print 'fixed sites', N_varients_fixed

