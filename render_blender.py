# A simple script that uses blender to render views of a single object by rotation the camera around it.
# Also produces depth map at the same time.
#
# Example:
# blender --background --python mytest.py -- --views 10 /path/to/my.obj
#

import argparse, sys, os
import numpy as np
import math
parser = argparse.ArgumentParser(description='Renders given obj file by rotation a camera around it.')
parser.add_argument('--views', type=int, default=24,
                    help='number of views to be rendered')
parser.add_argument('obj', type=str,
                    help='Path to the obj file to be rendered.')
parser.add_argument('--output_folder', type=str, default='H:/img',
                    help='The path the output will be dumped to.')
parser.add_argument('--scale', type=float, default=1,
                    help='Scaling factor applied to model. Depends on size of mesh.')
parser.add_argument('--remove_doubles', type=bool, default=True,
                    help='Remove double vertices to improve mesh quality.')
parser.add_argument('--edge_split', type=bool, default=True,
                    help='Adds edge split filter.')
parser.add_argument('--depth_scale', type=float, default=1.4,
                    help='Scaling that is applied to depth. Depends on size of mesh. Try out various values until you get a good result. Ignored if format is OPEN_EXR.')
parser.add_argument('--color_depth', type=str, default='8',
                    help='Number of bit per channel used for output. Either 8 or 16.')
parser.add_argument('--format', type=str, default='PNG',
                    help='Format of files generated. Either PNG or OPEN_EXR')

argv = sys.argv[sys.argv.index("--") + 1:]
args = parser.parse_args(argv)

import bpy

# Set up rendering of depth map.
bpy.context.scene.use_nodes = True
tree = bpy.context.scene.node_tree
links = tree.links

# Add passes for additionally dumping albedo and normals.
bpy.context.scene.render.layers["RenderLayer"].use_pass_normal = True
bpy.context.scene.render.layers["RenderLayer"].use_pass_color = True
bpy.context.scene.render.image_settings.file_format = args.format
bpy.context.scene.render.image_settings.color_depth = args.color_depth

# Clear default nodes
for n in tree.nodes:
    tree.nodes.remove(n)

# Create input render layer node.
render_layers = tree.nodes.new('CompositorNodeRLayers')

depth_file_output = tree.nodes.new(type="CompositorNodeOutputFile")
depth_file_output.label = 'Depth Output'
if args.format == 'OPEN_EXR':
  links.new(render_layers.outputs['Depth'], depth_file_output.inputs[0])
else:
  # Remap as other types can not represent the full range of depth.
  map = tree.nodes.new(type="CompositorNodeMapValue")
  # Size is chosen kind of arbitrarily, try out until you're satisfied with resulting depth map.
  map.offset = [-0.7]
  map.size = [args.depth_scale]
  map.use_min = True
  map.min = [0]
  links.new(render_layers.outputs['Depth'], map.inputs[0])

  links.new(map.outputs[0], depth_file_output.inputs[0])

scale_normal = tree.nodes.new(type="CompositorNodeMixRGB")
scale_normal.blend_type = 'MULTIPLY'
# scale_normal.use_alpha = True
scale_normal.inputs[2].default_value = (0.5, 0.5, 0.5, 1)
links.new(render_layers.outputs['Normal'], scale_normal.inputs[1])

bias_normal = tree.nodes.new(type="CompositorNodeMixRGB")
bias_normal.blend_type = 'ADD'
# bias_normal.use_alpha = True
bias_normal.inputs[2].default_value = (0.5, 0.5, 0.5, 0)
links.new(scale_normal.outputs[0], bias_normal.inputs[1])

normal_file_output = tree.nodes.new(type="CompositorNodeOutputFile")
normal_file_output.label = 'Normal Output'
links.new(bias_normal.outputs[0], normal_file_output.inputs[0])

albedo_file_output = tree.nodes.new(type="CompositorNodeOutputFile")
albedo_file_output.label = 'Albedo Output'
links.new(render_layers.outputs['Color'], albedo_file_output.inputs[0])

# Delete default cube
bpy.data.objects['Cube'].select = True
bpy.ops.object.delete()

bpy.ops.import_scene.obj(filepath=args.obj)
for object in bpy.context.scene.objects:
    if object.name in ['Camera', 'Lamp']:
        continue
    bpy.context.scene.objects.active = object
    if args.scale != 1:
        bpy.ops.transform.resize(value=(args.scale,args.scale,args.scale))
        bpy.ops.object.transform_apply(scale=True)
    if args.remove_doubles:
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.remove_doubles()
        bpy.ops.object.mode_set(mode='OBJECT')
    if args.edge_split:
        bpy.ops.object.modifier_add(type='EDGE_SPLIT')
        bpy.context.object.modifiers["EdgeSplit"].split_angle = 1.32645
        bpy.ops.object.modifier_apply(apply_as='DATA', modifier="EdgeSplit")

# Make light just directional, disable shadows.
lamp = bpy.data.lamps['Lamp']
lamp.type = 'SUN'
lamp.shadow_method = 'NOSHADOW'
# Possibly disable specular shading:
lamp.use_specular = False
# Add another light source so stuff facing away from light is not completely dark
bpy.ops.object.lamp_add(type='SUN')
lamp2 = bpy.data.lamps['Sun']
lamp2.shadow_method = 'NOSHADOW'
lamp2.use_specular = False
lamp2.energy = 1.5
bpy.data.objects['Sun'].rotation_euler = bpy.data.objects['Lamp'].rotation_euler
# angle_rotation = 360/args.views
bpy.data.objects['Sun'].rotation_euler[0] += 180


def parent_obj_to_camera(b_camera):
    origin = (0, 0, 0)
    b_empty = bpy.data.objects.new("Empty", None)
    b_empty.location = origin
    b_camera.parent = b_empty  # setup parenting

    scn = bpy.context.scene
    scn.objects.link(b_empty)
    scn.objects.active = b_empty
    return b_empty
#????????????????????????
def camera_params():
    model_num = 24
    in_plane_rotation = 0
    fov = 25
    dets = np.zeros(shape=(24, 5))
    for i in range(model_num):
        az, el, depth_ratio = list(
            *([360, 5, 0.3] * np.random.rand(1, 3) + [0, 25, 0.65]))
        #print(az,el,in_plane_rotation,depth_ratio,fov)
        dets[i] = np.array([az,el,in_plane_rotation,depth_ratio,fov])
    np.savetxt("H:/rendering_metadata.txt", dets, fmt='%f', delimiter=' ')

scene = bpy.context.scene
scene.render.resolution_x = 274#?????????????????????
scene.render.resolution_y = 274
scene.render.resolution_percentage = 100
scene.render.alpha_mode = 'TRANSPARENT'
cam = scene.objects['Camera']
cam.location = (0, 1, 0.6)
cam_constraint = cam.constraints.new(type='TRACK_TO')
cam_constraint.track_axis = 'TRACK_NEGATIVE_Z'
cam_constraint.up_axis = 'UP_Y'
b_empty = parent_obj_to_camera(cam)
cam_constraint.target = b_empty#????????????
camera_loc = []
model_identifier = os.path.split(os.path.split(args.obj)[0])[1]
fp = os.path.join(args.output_folder, model_identifier, model_identifier)
scene.render.image_settings.file_format = 'PNG'  # set output format to .png

camera_params()#??????????????????
params = np.loadtxt('H:/rendering_metadata.txt', delimiter=' ')#????????????????????????
camera_num = params.shape[0]
camera_location = []
filePath = []
img_list = []
for i in range(0, camera_num):
    theta = -params[i][0] * math.pi / 180.0
    camz = params[i][3] * math.sin(params[i][1]*math.pi/180.0)/0.57
    lens = params[i][3] * math.cos(params[i][1]*math.pi/180.0)/0.57
    camx = lens * math.cos(theta)
    camy = lens * math.sin(theta)
    camera_location.append((camx,camy,camz))

for output_node in [depth_file_output, normal_file_output, albedo_file_output]:
    output_node.base_path = ''
for i in range(0, args.views):
    cam.location = camera_location[i]
    scene.render.filepath = fp.rstrip(model_identifier) + '{0:02d}'.format(int(i))
    # depth_file_output.file_slots[0].path = scene.render.filepath + "_depth.png"
    # normal_file_output.file_slots[0].path = scene.render.filepath + "_normal.png"
    #albedo_file_output.file_slots[0].path = scene.render.filepath + "_albedo.png"
    bpy.ops.render.render(write_still=True)  # render still
    img_list.append('{0:02d}'.format(int(i)) + ".png")
# print('fp:\n', fp)
# print('model_identifier:\n', model_identifier)
# print('scene.render.filepath:\n', scene.render.filepath)
print(albedo_file_output.file_slots)
img_txt = np.array(img_list)
filePath = fp.rstrip(model_identifier)+'rendering_metadata.txt'
imgPath = fp.rstrip(model_identifier)+'rendering.txt'
np.savetxt(filePath, params, fmt='%f', delimiter=' ')
np.savetxt(imgPath, img_txt, fmt='%s', delimiter=' ')
# from math import radians
#
# stepsize = 360.0 / args.views
# rotation_mode = 'XYZ'
#
# for output_node in [depth_file_output, normal_file_output, albedo_file_output]:
#     output_node.base_path = ''
#
# for i in range(0, args.views):
#     print("Rotation {}, {}".format((stepsize * i), radians(stepsize * i)))
#
#     scene.render.filepath = fp + '_r_{0:03d}'.format(int(i * stepsize))
#     #depth_file_output.file_slots[0].path = scene.render.filepath + "_depth.png"
#     #normal_file_output.file_slots[0].path = scene.render.filepath + "_normal.png"
#     albedo_file_output.file_slots[0].path = scene.render.filepath + "_albedo.png"
#
#     bpy.ops.render.render(write_still=True)  # render still
#
#     b_empty.rotation_euler[2] += radians(stepsize)

