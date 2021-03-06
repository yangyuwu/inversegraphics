__author__ = 'pol'
#From http://blender.stackexchange.com/a/9080

import bpy
import bmesh
from blender_utils import *
import blender_utils

def bmesh_copy_from_object(obj, objTransf, transform=True, triangulate=True, apply_modifiers=False):
    """
    Returns a transformed, triangulated copy of the mesh
    """

    assert(obj.type == 'MESH')

    if apply_modifiers and obj.modifiers:
        me = obj.to_mesh(bpy.context.scene, True, 'PREVIEW', calc_tessface=False)
        bm = bmesh.new()
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    else:
        if obj.mode == 'EDIT':
            bm_orig = bmesh.from_edit_mesh(me)
            bm = bm_orig.copy()
        else:
            bm = bmesh.new()
            bm.from_mesh(me)
        # Remove custom data layers to save memory
        for elem in (bm.faces, bm.edges, bm.verts, bm.loops):
            for layers_name in dir(elem.layers):
                if not layers_name.startswith("_"):
                    layers = getattr(elem.layers, layers_name)
                    layers.remove(layer)
                    for layer_name, layer in layers.items():
                        pass
        me = obj.data

    if transform:
        bm.transform(objTransf * obj.matrix_world)

    if triangulate:
        bmesh.ops.triangulate(bm, faces=bm.faces)

    return bm

def aabb_intersect(matrix_world1, instanceObjs1, matrix_world2, instanceObjs2):

    minX1, maxX1 = blender_utils.modelWidth(instanceObjs1, matrix_world1)
    minY1, maxY1 = blender_utils.modelDepth(instanceObjs1, matrix_world1)
    minZ1, maxZ1 = blender_utils.modelHeight(instanceObjs1, matrix_world1)

    minX2, maxX2 = blender_utils.modelWidth(instanceObjs2, matrix_world2)
    minY2, maxY2 = blender_utils.modelDepth(instanceObjs2, matrix_world2)
    minZ2, maxZ2 = blender_utils.modelHeight(instanceObjs2, matrix_world2)

    return ((maxX1 > minX2) and (minX1 < maxX2) and (maxY1 > minY2) and (minY1 < maxY2) and (maxZ1 > minZ2) and (minZ1 < maxZ2))


def bmesh_check_intersect_objects(obj, objTransf,  obj2, obj2Transf):
    """
    Check if any faces intersect with the other object

    returns a boolean
    """
    assert(obj != obj2)

    # Triangulate
    bm = bmesh_copy_from_object(obj, objTransf, transform=True, triangulate=True)
    bm2 = bmesh_copy_from_object(obj2, obj2Transf, transform=True, triangulate=True)

    # If bm has more edges, use bm2 instead for looping over its edges
    # (so we cast less rays from the simpler object to the more complex object)
    if len(bm.edges) > len(bm2.edges):
        bm2, bm = bm, bm2

    # Create a real mesh (lame!)
    scene = bpy.context.scene
    me_tmp = bpy.data.meshes.new(name="~temp~")
    bm2.to_mesh(me_tmp)
    bm2.free()
    obj_tmp = bpy.data.objects.new(name=me_tmp.name, object_data=me_tmp)
    scene.objects.link(obj_tmp)
    scene.update()
    ray_cast = obj_tmp.ray_cast

    intersect = False

    EPS_NORMAL = 0.000001
    EPS_CENTER = 0.01  # should always be bigger

    #for ed in me_tmp.edges:
    for ed in bm.edges:
        v1, v2 = ed.verts

        # setup the edge with an offset
        co_1 = v1.co.copy()
        co_2 = v2.co.copy()
        co_mid = (co_1 + co_2) * 0.5
        no_mid = (v1.normal + v2.normal).normalized() * EPS_NORMAL
        co_1 = co_1.lerp(co_mid, EPS_CENTER) + no_mid
        co_2 = co_2.lerp(co_mid, EPS_CENTER) + no_mid

        co, no, index = ray_cast(co_1, co_2)
        if index != -1:
            intersect = True
            break

    scene.objects.unlink(obj_tmp)
    bpy.data.objects.remove(obj_tmp)
    bpy.data.meshes.remove(me_tmp)

    scene.update()

    return intersect

def instancesIntersect(matrix_world1, instanceObjs1, matrix_world2, instanceObjs2):

    if aabb_intersect(matrix_world1, instanceObjs1, matrix_world2, instanceObjs2):
        # print ("AABB intersection!")
        for mesh1 in instanceObjs1:
            for mesh2 in instanceObjs2:
                if bmesh_check_intersect_objects(mesh1, matrix_world1,  mesh2, matrix_world2):
                    # print ("There's a MESH intersection!")
                    return True
    # else:
    #     print ("There's NO intersection!")
    # print("There's NO intersection!")

    return False

def targetSceneCollision(target, scene, roomName, targetParentInstance):
    # bpy.ops.mesh.primitive_cube_add
    for sceneInstance in scene.objects:
        if sceneInstance.type == 'EMPTY' and sceneInstance != target and sceneInstance.name != roomName and sceneInstance != targetParentInstance:
            if instancesIntersect(target.matrix_world, target.dupli_group.objects, sceneInstance.matrix_world, sceneInstance.dupli_group.objects):
                return True

    return False


def targetCubeSceneCollision(target, scene, roomName, targetParentInstance):
    # bpy.ops.mesh.primitive_cube_add
    for sceneInstance in scene.objects:
        if sceneInstance.type == 'MESH' and sceneInstance != target and sceneInstance.name != roomName and sceneInstance != targetParentInstance:

            if instancesIntersect(mathutils.Matrix.Identity(4), [target], mathutils.Matrix.Identity(4), [sceneInstance]):
                return True

    return False

def parseSceneCollisions(gtDir, scene_i, target_i, target, scene, targetPosOffset, chObjDistGT, chObjRotationGT, targetParentInstance, roomObj,  distRange, rotationRange, distInterval, rotationInterval):

    scene.cycles.samples = 500


    original_matrix_world = target.matrix_world.copy()
    distBins = np.linspace(distInterval, distRange, distRange/distInterval)
    rotBins = np.linspace(0, rotationRange, rotationRange / rotationInterval)

    totalBins = np.meshgrid(distBins, rotBins)
    totalBins[0] = np.append([0], totalBins[0].ravel())
    totalBins[1] = np.append([0], totalBins[1].ravel())

    boolBins = np.zeros(len(totalBins[0].ravel())).astype(np.bool)

    scene.update()

    for bin_i in range(len(totalBins[0].ravel())):
        dist = totalBins[0].ravel()[bin_i]
        rot = totalBins[1].ravel()[bin_i]
        chObjDistGT[:]= dist
        chObjRotationGT[:]= rot

        ignore = False

        azimuthRot = mathutils.Matrix.Rotation(0, 4, 'Z')

        target.matrix_world = mathutils.Matrix.Translation(original_matrix_world.to_translation() + mathutils.Vector(targetPosOffset.r)) * azimuthRot * (mathutils.Matrix.Translation(-original_matrix_world.to_translation())) * original_matrix_world

        if targetCubeSceneCollision(target, scene, roomObj.name, targetParentInstance):
            # print("Teapot intersects with an object.")
            ignore = True
            # pass

        if not instancesIntersect(mathutils.Matrix.Translation(mathutils.Vector((0, 0, -0.01))), [target], mathutils.Matrix.Identity(4), [targetParentInstance]):
            # print("Teapot not on table.")
            ignore = True

        if instancesIntersect(mathutils.Matrix.Translation(mathutils.Vector((0, 0, +0.02))), [target], mathutils.Matrix.Identity(4), [targetParentInstance]):
            # print("Teapot interesects supporting object.")
            ignore = True

        # ipdb.set_trace()
        if instancesIntersect(mathutils.Matrix.Identity(4), [target], mathutils.Matrix.Identity(4), [roomObj]):
            # print("Teapot intersects room")
            ignore = True

        boolBins[bin_i] = not ignore

        # bpy.ops.render.render(write_still=True)
        #
        # import imageio
        #
        # image = np.array(imageio.imread(scene.render.filepath))[:, :, 0:3]
        #
        # from blender_utils import lin2srgb
        # blender_utils.lin2srgb(image)
        #
        # cv2.imwrite(gtDir + 'images/scene' + str(scene_i) + '_' + 'targetidx' + str(target_i) + 'bin' + str(bin_i) + '_ignore' + str(ignore) + '.jpeg', 255 * image[:, :, [2, 1, 0]], [int(cv2.IMWRITE_JPEG_QUALITY), 100])

    return boolBins, totalBins
