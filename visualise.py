#!/usr/bin/python
import json
import math
import sys
import numpy as np
import plotly.express as px
import plotly.graph_objs as go
import pandas as pd
from scipy.spatial.transform import Rotation as R

#USED FOR TESTING. Read data from file given as argument
input_file = sys.argv[1]
f = open(input_file, encoding="utf8")

def rotate_a(X,vector):
	"""
	This function rotates vectors X degrees around the x axis, 
	in the negative direction as defined by the Right Hand Rule.
	Used to visualise where a cut would be made on a block prior
	to being rotated.
	"""
	axis_vector = (math.radians(-X)) * np.array([1,0,0])
	r =  R.from_rotvec(axis_vector)
	return list(r.apply(vector))

def rotate_c(X,a_set,vector):
	"""
	This function rotates vectors X degrees around the z axis, 
	in the negative direction as defined by the Right Hand Rule.
	Used to visualise where a cut would be made on a block prior
	to being rotated.
	"""
	axis_vector = math.radians(-X) * np.array([0,0,1])
	r =  R.from_rotvec(axis_vector)
	return list(r.apply(vector))

def visualise(cut_list):
	"""
	This function takes a cutlist, and produces an interactive
	plotly figure which displays exactly where the cuts in the 
	cutlist would appear on the block. 
	""" 
	cutlist = json.load(cut_list)
	modified_list =[]
	z_set = 0
	c_set = 0
	a_set = 0
	cut_num = 0
	for a in cutlist:
		if a[0] == "jump" or a[0] == "mark":
			a.pop(0)
			a = list(map(float,a)) + [z_set]
			
			if a_set != 0 or c_set != 0:
				a = rotate_a(a_set,a)
				a = rotate_c(c_set,a_set,a)

			a = a +[f"a_set {a_set} c_set {c_set} z_set {z_set:.1f} cut_num {cut_num}"]
			modified_list.append(a)

		elif a[0] == "z_abs":
			z_set = float(a[1])
			cut_num += 1
		elif a[0] == "c_abs":
			c_set = float(a[1])
		elif a[0] == "a_abs":
			a_set = float(a[1])

		elif a[0] == "z_rel" or a[0] == "z_step":
			z_set = z_set + float(a[1])
		elif a[0] == "c_rel" or a[0] == "c_step":
			c_set = c_set + float(a[1])
		elif a[0] == "a_rel" or a[0] == "a_step":
			a_set = a_set + float(a[1])
		else:
			pass
	df = pd.DataFrame(modified_list, columns = ["x","y","z","layer"])
	fig = px.line_3d(df,"x","y","z",color="layer")
	#fig.update_layout(scene_aspectmode = "data")
	fig.show()

visualise(f)

