import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.widgets import Button, TextBox
import matplotlib.patches as patches
import matplotlib as mpl
import json
import imageio

#These constants need to be established by hand with some engineers who can measure these values by hand
mm_per_pixel = 100
x_zero = 650
y_zero = 560
center = 0
side_length = 7.5 * mm_per_pixel
location_x = x_zero - side_length/2
location_y = y_zero + side_length/2

rotations = 0

#This generates a simple Matplotlib GUI for an operator to adjust their ideal coring boundary.
#It's pretty slow, might want to consider other options.

fig = plt.figure()
fig.suptitle('Use buttons to move boundary of core', fontsize=16)

gs = mpl.gridspec.GridSpec(20, 20, figure=fig)

ax = fig.add_subplot(gs[0:,:15])

ax.tick_params(
    axis='both',          
    which='both',      
    bottom=False,      
    left=False,       
    labelbottom=False,
    labelleft=False)

# Create a Rectangle patch
rect = patches.Rectangle((location_x, location_y),side_length,side_length,linewidth=0.5,edgecolor='r',facecolor='none')
ax.add_patch(rect)

def left(event):
	global rect, location_x
	location_x = location_x - 10
	rect.set_x(location_x)
	fig.canvas.draw()

def right(event):
	global rect, location_x
	location_x = location_x + 10
	rect.set_x(location_x)
	fig.canvas.draw()

def up(event):
	global rect, location_y
	location_y = location_y - 10
	rect.set_y(location_y)
	fig.canvas.draw()

def down(event):
	global rect, location_y
	location_y = location_y + 10
	rect.set_y(location_y)
	fig.canvas.draw()

def complete(event):
	global rect, location_x, location_y
	plt.close()
	return location_x, location_y

def rotate(event):
	global rect, ax, rotations
	rotations = rotations + 1
	t_start = ax.transData
	degrees = rotations * 1
	t = mpl.transforms.Affine2D().rotate_deg(degrees)
	t_end = t_start + t
	rect.set_transform(t_end)
	fig.canvas.draw()

def rotate_cc(event):
	global rect, ax, rotations
	rotations = rotations - 1
	t_start = ax.transData
	degrees = rotations * 5
	t = mpl.transforms.Affine2D().rotate_deg(degrees)
	t_end = t_start + t
	rect.set_transform(t_end)
	fig.canvas.draw()

def submit(text):
	global rect, mm_per_pixel, side_length
	side_length = mm_per_pixel * float(text)
	rect.set_width(side_length)
	rect.set_height(side_length)
	fig.canvas.draw()

axleft = fig.add_subplot(gs[6:8,16:18])
axright = fig.add_subplot(gs[6:8,18:20])
axup = fig.add_subplot(gs[4:6,17:19])
axdown = fig.add_subplot(gs[8:10,17:19])
axcomplete = fig.add_subplot(gs[18:19,17:19])
axrotate = fig.add_subplot(gs[12:13,16:20])
axrotate_cc = fig.add_subplot(gs[13:14,16:20])
axbox = fig.add_subplot(gs[16,16:20])

bleft = Button(axleft, 'Left')
bleft.on_clicked(left)
bright = Button(axright, 'Right')
bright.on_clicked(right)
bup = Button(axup, 'Up')
bup.on_clicked(up)
bdown = Button(axdown, 'Down')
bdown.on_clicked(down)
bcomplete = Button(axcomplete, 'Done')
bcomplete.on_clicked(complete)
brotate = Button(axrotate, 'Rotate C')
brotate.on_clicked(rotate)
brotate_cc = Button(axrotate_cc, 'Rotate CC')
brotate_cc.on_clicked(rotate_cc)
text_box = TextBox(axbox, 'Dimension of Square (mm)', initial="7.5")
text_box.on_submit(submit)

#blank config file used for testing
test = {"block":{"thickness":0,"width":0,"length":0,"origin_x":0,"origin_y":0,"physical_rotation":0},"desired_cut":{"cut_process":"","internal_a_rotation":0,"internal_c_rotation":0,"final_dimension_x":0,"final_dimension_y":0,"final_dimension_z":0,"wall_angle": 0,"top_style":"","top_angle": 0},"laser_cut_config":{"jump_speed":400,"mark_speed":100,"kerf_angle": 3,"xy_spacing":0.01,"z_spacing":0.1,"z_final_overshoot":0.25}}
test_str = json.dumps(test)

def lva(cut_configuration, image_path):
	global location_x, location_y, x_zero, y_zero, side_length, mm_per_pixel

	"""
	This function takes a cut_configuration and an image of the block on the MANTIS. Once the operator
	finishes changing the boundary of the coring in the GUI, this function should update the block offset values, 
	called origin_x and origin_y, as well as the dimensions of the cored stone. Origin_x and origin_y describe how 
	far off 0,0 the center of the block rests on the post. 
	"""

	#Check that this line reads json.loads(cut_configuration)

	input_json = json.loads(cut_configuration)

	#On closing, this function should update the configuration to be handed to the cutlist generator. This is unfinished
	def handle_close(event):
		input_json["block"]["origin_x"] = ((location_x - side_length/2) - x_zero) / mm_per_pixel
		input_json["block"]["origin_y"] = (-(location_y - side_length/2) + y_zero) / mm_per_pixel
		input_json["desired_cut"]["final_dimension_x"] = side_length / mm_per_pixel
		input_json["desired_cut"]["final_dimension_y"] = side_length / mm_per_pixel
		#input_json["block"]["origin_x"] = 5
		#input_json["block"]["origin_y"] = 4

	#Load image
	img = imageio.imread(image_path)
	#img = mpimg.imread("C:/Users/achen/Documents/DiamondFoundry/tool-pathing/test2.png")
	
	# Display the image	
	ax.imshow(img)
	fig.canvas.mpl_connect('close_event', handle_close)
	plt.show()

	output_json = json.dumps(input_json)
	#print(output_json)
	return output_json

#For testing on MANTIS, insert path to image as second parameter.
#lva(test_str, "C:\DFoundry\DF Laser\data\Vision Assistant\DF Laser Assistant 2020_08_19__17_17_32_84.jpg")
lva(test_str, "C:/Users/achen/Documents/DiamondFoundry/tool-pathing/test.jpg")