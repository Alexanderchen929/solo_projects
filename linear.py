#!/usr/bin/python
import json
import sys
import math
import numpy as np
from datetime import datetime
import csv
import os.path

#USED FOR TESTING. Read data from file given as argument
input_file = sys.argv[1]
f = open(input_file, encoding="utf8")

#save_path = "C:/DFoundry/Df Laser/test_files/"
save_path = "C:/Users/achen/Documents/DiamondFoundry/tool-pathing/test_data/"

refraction = 1

def offset(x1,y1,x2,y2,magnitude):
	"""
	This function helps find coordinates of parallel lines. It uses an 
	orthogonal vector to work out offsets to calculate coordinates of
	lines parallel to (x1,y1) -> (x2,y2), with a given magnitude 
	"""
	norm = math.sqrt((y2-y1)**2 + (x1-x2)**2) / magnitude
	offset_x = (y2-y1)/norm
	offset_y = (x1-x2)/norm
	return offset_x, offset_y

# def line(x1,y1,x2,y2,z_thickness,laser):
# 	"""
# 	This algorithm creates a cut list for a cut of depth z_thickness
# 	between (x1,y1)->(x2,y2). 
# 	"""
# 	#Global variables that are used by all algorithms
# 	layers = int(z_thickness/laser["z_spacing"])

# 	#Works out offset when beginning on a new layer
# 	taper = math.tan(math.radians(laser["kerf_angle"]/2)) * laser["z_spacing"]
# 	taper_x,taper_y = offset(x1,y1,x2,y2,taper)

# 	#Works out offset between each parallel scan on the same layer
# 	delta_x,delta_y = offset(x1,y1,x2,y2,laser["xy_spacing"])

# 	#Works out maximum offset from starting line, we don't want to exceed this at any point.
# 	max_taper = math.tan(math.radians(laser["kerf_angle"]/2)) * (z_thickness) * 2
# 	max_delta_x, max_delta_y = offset(x1,y1,x2,y2,max_taper)
# 	#max_delta_x, max_delta_y = 2*max_delta_x, 2*max_delta_y

# 	#Loops through each layer, in which we fit as many parallel raster scans as the maximum offset allows
# 	cutlist = []
# 	for a in range(layers):
# 		new_x1,new_x2,new_y1,new_y2 = x1 + a*taper_x, x2 + a*taper_x, y1 + a*taper_y, y2 + a*taper_y
# 		i = 0
# 		while abs(new_x1-x1) < abs(max_delta_x) or abs(new_y1-y1) < abs(max_delta_y):
# 			#This use of i is to reduce the jump distance between individual scans
# 			if i % 2 == 0:
# 				cutlist.append(["jump", f"{new_x1:.6f}", f"{new_y1:.6f}"])
# 				cutlist.append(["mark", f"{new_x2:.6f}", f"{new_y2:.6f}"])
# 			else:
# 				cutlist.append(["jump", f"{new_x2:.6f}", f"{new_y2:.6f}"])
# 				cutlist.append(["mark", f"{new_x1:.6f}", f"{new_y1:.6f}"])
# 			new_x1,new_x2,new_y1,new_y2 = new_x1 + delta_x, new_x2 + delta_x, new_y1 + delta_y, new_y2 + delta_y
# 			i = i + 1
# 		#Having completed one layer, the laser moves down to begin the next layer
# 		cutlist.append(["z_rel", str(-laser["z_spacing"])])
# 		max_delta_x = max_delta_x - taper_x
# 	return json.dumps(cutlist)

def line(x1,y1,x2,y2,z_thickness,laser):
	"""
	This algorithm creates a cut list for a cut of depth z_thickness
	between (x1,y1)->(x2,y2). 
	"""
	#Global variables that are used by all algorithms
	layers = int(z_thickness/laser["z_spacing"])

	#Works out offset when beginning on a new layer
	taper = math.tan(math.radians(laser["kerf_angle"]/2)) * laser["z_spacing"]
	taper_x,taper_y = offset(x1,y1,x2,y2,taper)

	#Works out offset between each parallel scan on the same layer
	delta_x,delta_y = offset(x1,y1,x2,y2,laser["xy_spacing"])

	#Works out maximum offset from starting line, we don't want to exceed this at any point.
	max_taper = math.tan(math.radians(laser["kerf_angle"]/2)) * (z_thickness) * 2
	max_delta_x, max_delta_y = offset(x1,y1,x2,y2,max_taper)
	#max_delta_x, max_delta_y = 2*max_delta_x, 2*max_delta_y

	#Loops through each layer, in which we fit as many parallel raster scans as the maximum offset allows
	cutlist = []
	for a in range(layers):
		new_x1,new_x2,new_y1,new_y2 = x1 + a*taper_x, x2 + a*taper_x, y1 + a*taper_y, y2 + a*taper_y
		i = 0
		cutlist.append(["z_step", str(-laser["z_spacing"])])
		while abs(new_x1-x1) < abs(max_delta_x) or abs(new_y1-y1) < abs(max_delta_y):
			#This use of i is to reduce the jump distance between individual scans
			if i % 2 == 0:
				cutlist.append(["jump", f"{new_x1:.6f}", f"{new_y1:.6f}"])
				cutlist.append(["mark", f"{new_x2:.6f}", f"{new_y2:.6f}"])
			else:
				cutlist.append(["jump", f"{new_x2:.6f}", f"{new_y2:.6f}"])
				cutlist.append(["mark", f"{new_x1:.6f}", f"{new_y1:.6f}"])
			new_x1,new_x2,new_y1,new_y2 = new_x1 + delta_x, new_x2 + delta_x, new_y1 + delta_y, new_y2 + delta_y
			i = i + 1
		#Having completed one layer, the laser moves down to begin the next layer
		max_delta_x = max_delta_x - taper_x

	cutlist.insert(0, ["set_trigger4", "1", "0", "7", "8", "45"])
	cutlist.append(["stop_trigger"])
	return json.dumps(cutlist)

def z_focus(block,cut,laser):
	"""
	This algorithm returns a cutlist which describes a series of parallel lines,
	each with a different z value, to calibrate the z value for the laser.
	"""
	cutlist = []
	iterations = int(cut["final_dimension_z"]/laser["z_spacing"])
	#Currently x,y is decided to take up a good amount of the block, rather than having set distances and sizes
	y = cut["final_dimension_y"]/2
	offset = laser["xy_spacing"]
	x = 0

	cutlist.append(["z_abs","0"])
	for a in range(iterations):
		cutlist.append(["jump", f"{x:.6f}", f"{y:.6f}"])
		cutlist.append(["mark", f"{x:.6f}", f"{-y:.6f}"])
		cutlist.append(["z_rel", str(-laser["z_spacing"])])
		x = x + offset
	cutlist.insert(0, ["set_trigger4", "1", "0", "7", "8", "45"])
	cutlist.append(["stop_trigger"])
	return json.dumps(cutlist)


def simple_core(block,cut,laser):
	"""
	This algorithm returns a cutlist which performs a simple core operation.
	The laser runs race track style around the specified core, going around
	all 4 sides before the laser moves down to the next layer. The poly is
	expected to fall off the core at the end of the entire cutting operation.
	"""

	layers = int(block["thickness"]/laser["z_spacing"])

	#Since all cuts are square, the offsets are more obvious than in the general linear case.
	taper = math.tan(math.radians(laser["kerf_angle"]/2)) * laser["z_spacing"]
	max_delta = math.tan(math.radians(laser["kerf_angle"]/2)) * (block["thickness"] + laser["z_final_overshoot"]) * 2
	
	cutlist = []
	cutlist.append(["a_abs", "0"])
	cutlist.append(["c_abs", str(block["physical_rotation"])])
	cutlist.append(["z_abs", str(block["thickness"])])

	for a in range(layers):
		x1, y1 = cut["final_dimension_x"]/2 + a*taper, cut["final_dimension_y"]/2 + a*taper
		while abs(x1-cut["final_dimension_x"]/2)  < abs(max_delta):
			cutlist.append(["jump", str(x1 + block["origin_x"]), str(y1 + block["origin_y"])])
			cutlist.append(["mark", str(x1 + block["origin_x"]), str(-y1 + block["origin_y"])])
			cutlist.append(["mark", str(-x1 + block["origin_x"]), str(-y1 + block["origin_y"])])
			cutlist.append(["mark", str(-x1 + block["origin_x"]), str(y1 + block["origin_y"])])
			cutlist.append(["mark", str(x1 + block["origin_x"]), str(y1 + block["origin_y"])])
			x1, y1 = x1 + laser["xy_spacing"], y1 + laser["xy_spacing"]
		cutlist.append(["z_step", str(-laser["z_spacing"])])
		max_delta = max_delta - taper 
	return json.dumps(cutlist)

def vertical_core(block,cut,laser):
	"""
	This algorithm returns a cutlist which performs a vertical core operation.
	The laser cuts off one side of poly at a time, rotating the block such that
	the edge of the laser "cone" is parallel to the SCD core. After one side of
	the block has been removed, the block is rotated 90 degrees and the algorithm
	repeats until all 4 sides have been removed.
	"""

	layers = int(block["thickness"]/laser["z_spacing"])
	angle = math.radians(laser["kerf_angle"]/2)
	taper = math.tan(angle) * laser["z_spacing"]

	u = math.tan(2 * angle) * (block["thickness"] + laser["z_final_overshoot"])
	z_0 = block["thickness"]*math.cos(angle) + math.sin(angle)*((cut["final_dimension_y"])/2 - block["origin_y"] + u)
	z_1 = block["thickness"]*math.cos(angle) + math.sin(angle)*((cut["final_dimension_x"])/2 + block["origin_x"] + u)
	z_2 = block["thickness"]*math.cos(angle) + math.sin(angle)*((cut["final_dimension_y"])/2 + block["origin_y"] + u)
	z_3 = block["thickness"]*math.cos(angle) + math.sin(angle)*((cut["final_dimension_x"])/2 - block["origin_x"] + u)
	
	cutlist = []
	cutlist.append(["a_abs", f"{math.degrees(angle):.6f}"])
	cutlist.append(["c_abs", str(block["physical_rotation"])])
	cutlist.append(["z_abs", f"{z_0:.6f}"])

	y_start_wide = ((u + cut["final_dimension_x"]/2)* math.cos(angle) 
				 - block["thickness"]*math.sin(angle) 
				 - u/math.cos(angle))
	y_start_length = ((u + cut["final_dimension_y"]/2)* math.cos(angle) 
				   - block["thickness"]*math.sin(angle) 
				   - u/math.cos(angle))

	depth_cut = (block["thickness"] + laser["z_final_overshoot"]) * math.cos(angle)/math.cos(2*angle)

	cut1 = json.loads(line(block["width"]/2 - block["origin_x"],y_start_length - block["origin_y"],-block["width"]/2 - block["origin_x"],y_start_length - block["origin_y"],depth_cut,laser))

	cut2 = json.loads(line(block["length"]/2 + block["origin_y"],y_start_wide - block["origin_x"],-block["length"]/2 + block["origin_y"],y_start_wide - block["origin_x"],depth_cut,laser))

	cut3 = json.loads(line(block["width"]/2 + block["origin_x"],y_start_length + block["origin_y"],-block["width"]/2 + block["origin_x"],y_start_length + block["origin_y"],depth_cut,laser))

	cut4 = json.loads(line(block["length"]/2 - block["origin_y"],y_start_wide + block["origin_x"],-block["length"]/2 - block["origin_y"],y_start_wide + block["origin_x"],depth_cut,laser))

	#cut1 = json.loads(line(block["width"]/2,y_start_length,-block["width"]/2,y_start_length,depth_cut,laser))

	#cut2 = json.loads(line(block["length"]/2,y_start_wide,-cut["final_dimension_y"]/2,y_start_wide,depth_cut,laser))

	#cut3 = json.loads(line(block["width"]/2,y_start_length,-cut["final_dimension_x"]/2,y_start_length,depth_cut,laser))

	#cut4 = json.loads(line(cut["final_dimension_y"]/2,y_start_wide,-cut["final_dimension_y"]/2,y_start_wide,depth_cut,laser))

	cutlist = (cutlist + cut1
	                   + [["c_rel", "90"],["z_abs", f"{z_1:.6f}"],] 
	                   + cut2
	                   + [["c_rel", "90"],["z_abs", f"{z_2:.6f}"]] 
					   + cut3 
					   + [["z_abs", f"{z_3:.6f}"],["c_rel", "90"]] 
					   + cut4)

	cutlist.insert(0, ["set_trigger4", "1", "0", "7", "8", "45"])
	cutlist.append(["stop_trigger"])

	return json.dumps(cutlist)


def pyramid_slice(x1,y1,x2,y2,z,delta,deltaz,taper_x,taper_y,taper_straight,layers):
	"""
	This algorithm returns a cutlist which performs a cut which is a quarter
	of the total slicing required to create a pyramid top, while ensuring a flat
	bottom above it, both of which is required for an OG seed.
	"""
	cutlist = []
	y_max = abs(y1-y2)
	for a in range(layers):
		i = 0
		new_x1, new_y1, new_x2, new_y2 = x1 - a*taper_x, y1-a*taper_straight, x2+a*taper_x, y2+a*taper_y
		while abs(new_y1 - (y1 - a*taper_straight)) < y_max and x1 > 0:
			if i % 2 == 0:
				cutlist.append(["jump", f"{new_x1:.6f}", f"{new_y1:.6f}"])
				cutlist.append(["mark", f"{new_x2:.6f}", f"{new_y1:.6f}"])
			else:
				cutlist.append(["jump", f"{new_x2:.6f}", f"{new_y1:.6f}"])
				cutlist.append(["mark", f"{new_x1:.6f}", f"{new_y1:.6f}"])
			new_y1 = new_y1-delta
			i = i + 1
		if a < layers - 1:
			cutlist.append(["z_step", str(-deltaz)])
		y_max = y_max - taper_straight - taper_y

	return cutlist

# def oss_stacked(block, cut, laser):
# 	"""
# 	This algorithm returns a cutlist which performs OG slicing. It begins
# 	with an optional core, then cuts out slices until as many OG seeds as 
# 	specified are removed from the block.
# 	"""
# 	pyramid_angle_1 = math.atan(cut["pyramid_height"]/(cut["final_dimension_x"]/2))
# 	pyramid_angle_2 = math.atan(cut["pyramid_height"]/(cut["final_dimension_y"]/2))

# 	angle = math.radians(laser["kerf_angle"]/2)
# 	gap = math.tan(pyramid_angle_1) * (cut["final_dimension_x"]/2) + cut["gap_size"]
# 	unit_length = gap + cut["base_height"]
# 	max_slices = math.floor(block["thickness"]/unit_length)

# 	if cut["core"] == "yes":
# 		cutlist = json.loads(vertical_core(block,cut,laser))
# 		return json.dumps(cutlist)
# 	else:
# 		cutlist = []

# 	a0 = -(90 + math.degrees(angle))

# 	if cut["excess"] == "top":
# 		#Cut out of bottom_up
# 		side_x = unit_length * max_slices-cut["pyramid_height"]
# 	elif cut["excess"] == "bottom":
# 		#Cut out of top
# 		side_x = block["thickness"]-cut["pyramid_height"]

# 	diagonal_1 = math.sqrt(side_x**2 + (cut["final_dimension_x"]/2)**2)
# 	theta_1 = math.atan(side_x*2/cut["final_dimension_x"])
# 	z0_1 = math.cos(theta_1 + angle) * diagonal_1

# 	diagonal_2 = math.sqrt(side_x**2 + (cut["final_dimension_y"]/2)**2)
# 	theta_2 = math.atan(side_x*2/cut["final_dimension_y"])
# 	z0_2 = math.cos(theta_2 + angle) * diagonal_2


# 	x1_1 = math.sin(theta_1 + angle) * diagonal_1
# 	x1_2 = math.sin(theta_2 + angle) * diagonal_2
# 	x_offset = gap/math.cos(angle)
# 	x0_1 = x1_1 + x_offset
# 	x0_2 = x1_2 + x_offset

# 	z_shift = (cut["base_height"] + gap) * math.sin(angle)
# 	x_shift = (cut["base_height"] + gap) * math.cos(angle)

# 	cutlist.append(["a_abs",f"{a0:.6f}"])
# 	cutlist.append(["c_abs",str(block["physical_rotation"])])
# 	cutlist.append(["z_abs",f"{z0_1:.6f}"])

# 	if pyramid_angle_1 >= angle and pyramid_angle_2 >= angle:
# 		max_depth_1 = ((cut["pyramid_height"]/math.sin(pyramid_angle_1))*math.cos(angle))*refraction
# 		max_layers_1 = math.ceil(max_depth_1/laser["z_spacing"])
# 		max_depth_2 = ((cut["pyramid_height"]/math.sin(pyramid_angle_2))*math.cos(angle))*refraction
# 		max_layers_2 = math.ceil(max_depth_2/laser["z_spacing"])

# 		if cut["layers"] == "max":
# 			layers_1 = max_layers_1 + 1
# 			layers_2 = max_layers_2 + 1
# 		else:
# 			layers_1 = cut["layers"]
# 			layers_2 = cut["layers"]

# 		new_angle_1 = math.atan((math.tan(pyramid_angle_1))/refraction)
# 		taper_y_1 = math.tan(new_angle_1 - angle)*(laser["z_spacing"])
# 		taper_x_1 = cut["final_dimension_x"]/(2*max_layers_1)
# 		new_angle_2 = math.atan((math.tan(pyramid_angle_2))/refraction)
# 		taper_y_2 = math.tan(new_angle_2 - angle)*(laser["z_spacing"])
# 		taper_x_2 = cut["final_dimension_x"]/(2*max_layers_2)
# 		taper_straight = math.tan(angle)*(laser["z_spacing"])

# 		if cut["num_of_seeds"] == "max":
# 			num_slices = max_slices
# 		else:
# 			num_slices = cut["num_of_seeds"] + 1

# 		for i in range(num_slices):
# 			cutlist = (cutlist
# 						  + pyramid_slice(cut["final_dimension_y"]/2,x0_1,-cut["final_dimension_y"]/2,x1_1,z0_1,laser["xy_spacing"], laser["z_spacing"], taper_x_1,taper_y_1,taper_straight,layers_1)
# 						  + [["z_abs",f"{z0_2:.6f}"]] + [["c_abs","90"]]
# 						  + pyramid_slice(cut["final_dimension_x"]/2,x0_2,-cut["final_dimension_x"]/2,x1_2,z0_2,laser["xy_spacing"], laser["z_spacing"], taper_x_2,taper_y_2,taper_straight,layers_2)
# 						  + [["z_abs",f"{z0_1:.6f}"]] + [["c_abs","180"]]
# 						  + pyramid_slice(cut["final_dimension_y"]/2,x0_1,-cut["final_dimension_y"]/2,x1_1,z0_1,laser["xy_spacing"], laser["z_spacing"], taper_x_1,taper_y_1,taper_straight,layers_1)
# 						  + [["z_abs",f"{z0_2:.6f}"]] + [["c_abs","270"]]
# 						  + pyramid_slice(cut["final_dimension_x"]/2,x0_2,-cut["final_dimension_x"]/2,x1_2,z0_2,laser["xy_spacing"], laser["z_spacing"], taper_x_2,taper_y_2,taper_straight,layers_2)
# 						  )
# 			z0_1 = z0_1 + z_shift
# 			z0_2 = z0_2 + z_shift
# 			x0_1, x1_1, x0_2, x1_2 = x0_1 - x_shift, x1_1 - x_shift, x0_2 - x_shift, x1_2 - x_shift
# 			cutlist.append(["c_abs",str(block["physical_rotation"])])
# 			cutlist.append(["z_abs",f"{z0_1:.6f}"])	
# 	else:
# 		raise Exception("Pyramid angle too small")

# 	return json.dumps(cutlist)

def oss_helper(block, cut, laser, x):
	pyramid_angle_1 = math.atan(cut["pyramid_height"]/x)
	angle = math.radians(laser["kerf_angle"]/2)

	gap = math.tan(pyramid_angle_1) * (x) + cut["gap_size"]
	unit_length = gap + cut["base_height"]
	max_slices = math.floor(block["thickness"]/unit_length)

	if cut["excess"] == "top":
		#Cut out of bottom_up
		side_x = unit_length * max_slices-cut["pyramid_height"]
	elif cut["excess"] == "bottom":
		#Cut out of top
		side_x = block["thickness"]-cut["pyramid_height"]

	diagonal_1 = math.sqrt(side_x**2 + x**2)
	theta_1 = math.atan(side_x/x)
	z0_1 = math.cos(theta_1 + angle) * diagonal_1

	x1_1 = math.sin(theta_1 + angle) * diagonal_1
	x_offset = gap/math.cos(angle)
	x0_1 = x1_1 + x_offset

	max_depth_1 = ((cut["pyramid_height"]/math.sin(pyramid_angle_1))*math.cos(angle))*refraction
	max_layers_1 = math.ceil(max_depth_1/laser["z_spacing"])

	if cut["layers"] == "max":
		layers_1 = max_layers_1 + 1
	else:
		layers_1 = cut["layers"]

	new_angle_1 = math.atan((math.tan(pyramid_angle_1))/refraction)
	taper_y_1 = math.tan(new_angle_1 - angle)*(laser["z_spacing"])
	taper_x_1 = cut["final_dimension_x"]/(2*max_layers_1)

	return x0_1, x1_1, z0_1, taper_x_1, taper_y_1, layers_1, pyramid_angle_1


def oss_stacked(block, cut, laser):
	"""
	This algorithm returns a cutlist which performs OG slicing. It begins
	with an optional core, then cuts out slices until as many OG seeds as 
	specified are removed from the block.
	"""
	x0_1, x1_1, z0_1, taper_x_1, taper_y_1, layers_1, pyramid_angle_1 = oss_helper(block, cut, laser, cut["final_dimension_x"]/2)
	x0_2, x1_2, z0_2, taper_x_2, taper_y_2, layers_2, pyramid_angle_2 = oss_helper(block, cut, laser, cut["final_dimension_y"]/2)
	angle = math.radians(laser["kerf_angle"]/2)
	gap = math.tan(pyramid_angle_1) * (cut["final_dimension_x"]/2) + cut["gap_size"]
	unit_length = gap + cut["base_height"]
	max_slices = math.floor(block["thickness"]/unit_length)
	taper_straight = math.tan(angle)*(laser["z_spacing"])

	if cut["core"] == "yes":
		cutlist = json.loads(vertical_core(block,cut,laser))
		cutlist.pop()
		cutlist.pop(0)
	else:
		cutlist = []

	a0 = -(90 + math.degrees(angle))

	z_shift = (cut["base_height"] + gap) * math.sin(angle)
	x_shift = (cut["base_height"] + gap) * math.cos(angle)

	x_delta = math.sin(angle) * block["origin_x"]
	y_delta = math.sin(angle) * block["origin_y"]
	z1_delta = math.cos(angle) * block["origin_x"]
	z2_delta = math.cos(angle) * block["origin_y"]

	cutlist.append(["a_abs",f"{a0:.6f}"])
	cutlist.append(["c_abs",str(block["physical_rotation"])])
	cutlist.append(["z_abs",str(z0_1 + z2_delta)])

	if pyramid_angle_1 >= angle and pyramid_angle_2 >= angle:

		if cut["num_of_seeds"] == "max":
			num_slices = max_slices
		else:
			num_slices = cut["num_of_seeds"] + 1
		
		for i in range(num_slices):
			cutlist = (cutlist
						  + pyramid_slice(cut["final_dimension_y"]/2 - block["origin_x"],x0_1 + y_delta,-cut["final_dimension_y"]/2 - block["origin_x"],x1_1 + y_delta,z0_1 + block["origin_y"],laser["xy_spacing"], laser["z_spacing"], taper_x_1,taper_y_1,taper_straight,layers_1)
						  + [["z_abs",str(z0_2 + z1_delta)]] + [["c_abs","90"]]
						  + pyramid_slice(cut["final_dimension_x"]/2 + block["origin_y"],x0_2 + x_delta,-cut["final_dimension_x"]/2 + block["origin_y"],x1_2 + x_delta,z0_2 + block["origin_x"],laser["xy_spacing"], laser["z_spacing"], taper_x_2,taper_y_2,taper_straight,layers_2)
						  + [["z_abs",str(z0_1 - z2_delta)]] + [["c_abs","180"]]
						  + pyramid_slice(cut["final_dimension_y"]/2 + block["origin_x"],x0_1 - y_delta,-cut["final_dimension_y"]/2 + block["origin_x"],x1_1 - y_delta,z0_1 - block["origin_y"],laser["xy_spacing"], laser["z_spacing"], taper_x_1,taper_y_1,taper_straight,layers_1)
						  + [["z_abs",str(z0_2 - z1_delta)]] + [["c_abs","270"]]
						  + pyramid_slice(cut["final_dimension_x"]/2 - block["origin_y"],x0_2 - x_delta,-cut["final_dimension_x"]/2 - block["origin_y"],x1_2 - x_delta,z0_2 - block["origin_x"],laser["xy_spacing"], laser["z_spacing"], taper_x_2,taper_y_2,taper_straight,layers_2)
						  )
			z0_1 = z0_1 + z_shift
			z0_2 = z0_2 + z_shift
			x0_1, x1_1, x0_2, x1_2 = x0_1 - x_shift, x1_1 - x_shift, x0_2 - x_shift, x1_2 - x_shift
			cutlist.append(["c_abs",str(block["physical_rotation"])])
			cutlist.append(["z_abs",str(z0_1 + z2_delta)])	
	else:
		raise Exception("Pyramid angle too small")

	cutlist.insert(0, ["set_trigger4", "1", "0", "7", "8", "45"])
	cutlist.append(["stop_trigger"])
	return json.dumps(cutlist)

def cross(block, cut, laser):
	cutlist = []
	for i in range(1,5):
		cutlist.append(["jump", "0", str(i/4)])
		cutlist.append(["mark", "0", str(-i/4)])
		cutlist.append(["jump", str(i/4), "0"])
		cutlist.append(["mark", str(-i/4), "0"])
		if i < 4:
			cutlist.append(["c_rel", "90"])
	return json.dumps(cutlist)

def time_taken(json_cutlist, laser):
	"""
	This algorithm takes a cutlist and returns an estimate for the time
	taken to execute this algorithm in hours:minutes:seconds, based on	jump and mark speeds as well as experimental data on how long a,c,z 
	transformations take.
	"""
	cutlist = json.loads(json_cutlist)
	time = 0
	coordinate_array = [0, 0]
	for a in cutlist:
		if a[0] == "jump" or a[0] == "mark":
			coordinate_array = [float(a[1]) - coordinate_array[0], float(a[2]) - coordinate_array[1]]
			mag = math.sqrt(coordinate_array[0]**2 + coordinate_array[1]**2)
			if a[0] == "jump":
				time += mag/laser["jump_speed"]
			else:
				time += mag/laser["mark_speed"]
			coordinate_array = [float(a[1]), float(a[2])]
		elif a[0] == "z_abs" or a[0] == "z_rel":
			zSet = float(a[1])
		elif a[0] == "c_abs" or a[0] == "c_rel":
			cSet = float(a[1])
		elif a[0] == "a_abs" or a[0] == "a_rel":
			aSet = float(a[1])
		else:
			pass
	return str(datetime.timedelta(seconds=int(time)))

def generateCutList(cut_configuration):
	"""
	This function takes a cut_configuration json object and calls the function
	corresponding to the desired cut, thereby returning the cutlist.
	"""
	#Check that this line reads json.loads(cut_configuration)
	input_json = json.load(cut_configuration)

	#Currently only desired_cut and laser_cut_config are required
	try:
		block = input_json["block"]
	except:
		pass
	try:
		cut = input_json["desired_cut"]
		laser = input_json["laser_cut_config"]
	except:
		raise Exception("Either desired_cut or laser_cut_config not provided")

	if cut["cut_process"] == "line":
		final_list = line(cut["x1"],cut["y1"],cut["x2"],cut["y2"],cut["final_dimension_z"]+laser["z_final_overshoot"],laser)
	elif cut["cut_process"] == "simple_core":
		final_list = simple_core(block,cut,laser)
	elif cut["cut_process"] == "vertical_core":
		final_list = vertical_core(block,cut,laser)
	elif cut["cut_process"] == "oss_stacked":
		final_list = oss_stacked(block,cut,laser)
	elif cut["cut_process"] == "z_focus":
		final_list = z_focus(block,cut,laser)
	elif cut["cut_process"] == "cross":
		final_list = cross(block,cut,laser)
	else:
		raise Exception("No such cut exists: Check cut_process")
	#print(time_taken(final_list, laser))
	now = datetime.now()
	timestamp = str(now.strftime("%m-%d_%H_%M"))
	complete_name = os.path.join(save_path, timestamp+".csv")
	with open(complete_name, mode='w',newline ='') as test_data:
	    data_writer = csv.writer(test_data, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
	    list_data = json.loads(final_list)
	    for line1 in list_data:
	    	data_writer.writerow(line1)
	return final_list

#Also used for testing
data = generateCutList(f)
test = open ("test.txt","w")
test.write(data)


	